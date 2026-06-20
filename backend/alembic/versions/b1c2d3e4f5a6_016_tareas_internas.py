"""016_tareas_internas

Revision ID: c16d3e4f5a6b
Revises: a0b1c2d3e4f5
Create Date: 2026-06-18 00:00:00.000000

Crea las tablas del módulo de tareas internas (C-16):
- Enum: `estadotarea`
- Tabla `tarea`: tarea interna con ciclo de vida multi-tenant
- Tabla `comentario_tarea`: hilo de comentarios append-only
- Índices compuestos para queries frecuentes de mis-tareas y admin
- Permiso: tareas:gestionar → COORDINADOR, ADMIN, TUTOR, PROFESOR
"""

from typing import Sequence, Union
import uuid
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "c16d3e4f5a6b"
down_revision: Union[str, None] = "a0b1c2d3e4f5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 2. Tabla tarea ────────────────────────────────────────────────────────
    op.create_table(
        "tarea",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tenant.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "asignado_a",
            UUID(as_uuid=True),
            sa.ForeignKey("user.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "asignado_por",
            UUID(as_uuid=True),
            sa.ForeignKey("user.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "materia_id",
            UUID(as_uuid=True),
            sa.ForeignKey("materia.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column(
            "estado",
            sa.Enum(
                "pendiente", "en_progreso", "resuelta", "cancelada",
                name="estadotarea",
            ),
            nullable=False,
            server_default="pendiente",
        ),
        sa.Column("descripcion", sa.Text, nullable=False),
        sa.Column("contexto_id", UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_tarea_tenant_id", "tarea", ["tenant_id"])
    op.create_index("ix_tarea_asignado_a", "tarea", ["asignado_a"])
    op.create_index("ix_tarea_asignado_por", "tarea", ["asignado_por"])
    op.create_index("ix_tarea_materia_id", "tarea", ["materia_id"])
    op.create_index(
        "ix_tarea_tenant_asignado_a_estado",
        "tarea",
        ["tenant_id", "asignado_a", "estado"],
    )
    op.create_index(
        "ix_tarea_tenant_asignado_por_estado",
        "tarea",
        ["tenant_id", "asignado_por", "estado"],
    )

    # ── 3. Tabla comentario_tarea ─────────────────────────────────────────────
    op.create_table(
        "comentario_tarea",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tenant.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "tarea_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tarea.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "autor_id",
            UUID(as_uuid=True),
            sa.ForeignKey("user.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("texto", sa.Text, nullable=False),
        sa.Column("creado_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_comentario_tarea_tenant_id", "comentario_tarea", ["tenant_id"])
    op.create_index("ix_comentario_tarea_tarea_id", "comentario_tarea", ["tarea_id"])
    op.create_index("ix_comentario_tarea_autor_id", "comentario_tarea", ["autor_id"])

    # ── 4. Permiso tareas:gestionar (idempotente) ─────────────────────────────
    connection = op.get_bind()
    now = datetime.now(timezone.utc)

    # Insertar permiso de forma idempotente
    existing = connection.execute(
        sa.text("SELECT id FROM permiso WHERE nombre = 'tareas:gestionar'")
    ).fetchone()

    if existing is None:
        permiso_id = uuid.uuid4()
        connection.execute(
            sa.text(
                "INSERT INTO permiso (id, nombre, descripcion, created_at, updated_at) "
                "VALUES (:id, :nombre, :descripcion, :created_at, :updated_at)"
            ),
            {
                "id": permiso_id,
                "nombre": "tareas:gestionar",
                "descripcion": "Crear, ver y gestionar tareas internas del tenant",
                "created_at": now,
                "updated_at": now,
            },
        )
    else:
        permiso_id = existing[0]

    # Asignar permiso a roles relevantes
    for rol_nombre in ["COORDINADOR", "ADMIN", "TUTOR", "PROFESOR"]:
        rol_row = connection.execute(
            sa.text("SELECT id FROM rol WHERE nombre = :nombre"),
            {"nombre": rol_nombre},
        ).fetchone()
        if rol_row is None:
            continue
        # Idempotente: solo insertar si no existe el par rol_id+permiso_id
        existing_rp = connection.execute(
            sa.text(
                "SELECT id FROM rol_permiso WHERE rol_id = :rol_id AND permiso_id = :permiso_id"
            ),
            {"rol_id": rol_row[0], "permiso_id": permiso_id},
        ).fetchone()
        if existing_rp is None:
            connection.execute(
                sa.text(
                    "INSERT INTO rol_permiso (id, rol_id, permiso_id, created_at, updated_at) "
                    "VALUES (:id, :rol_id, :permiso_id, :created_at, :updated_at)"
                ),
                {
                    "id": uuid.uuid4(),
                    "rol_id": rol_row[0],
                    "permiso_id": permiso_id,
                    "created_at": now,
                    "updated_at": now,
                },
            )


def downgrade() -> None:
    connection = op.get_bind()

    # Eliminar permiso tareas:gestionar (cascade elimina rol_permiso)
    connection.execute(
        sa.text("DELETE FROM permiso WHERE nombre = 'tareas:gestionar'")
    )

    # Eliminar índices y tabla comentario_tarea
    op.drop_index("ix_comentario_tarea_autor_id", table_name="comentario_tarea")
    op.drop_index("ix_comentario_tarea_tarea_id", table_name="comentario_tarea")
    op.drop_index("ix_comentario_tarea_tenant_id", table_name="comentario_tarea")
    op.drop_table("comentario_tarea")

    # Eliminar índices y tabla tarea
    op.drop_index("ix_tarea_tenant_asignado_por_estado", table_name="tarea")
    op.drop_index("ix_tarea_tenant_asignado_a_estado", table_name="tarea")
    op.drop_index("ix_tarea_materia_id", table_name="tarea")
    op.drop_index("ix_tarea_asignado_por", table_name="tarea")
    op.drop_index("ix_tarea_asignado_a", table_name="tarea")
    op.drop_index("ix_tarea_tenant_id", table_name="tarea")
    op.drop_table("tarea")

    # Eliminar enum
    op.execute("DROP TYPE IF EXISTS estadotarea")
