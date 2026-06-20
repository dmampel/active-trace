"""009_calificaciones_tables

Revision ID: b1c2d3e4f5a6
Revises: a8b9c0d1e2f3
Create Date: 2026-06-17 00:00:00.000000

Agrega tablas del módulo calificaciones (C-10):
- calificacion: nota de un alumno en una actividad evaluable
- umbral_materia: umbral de aprobación por asignación docente

Decisiones de diseño:
- `aprobado` NO es columna — se deriva con `derivar_aprobado()` (función pura).
- `materia_id` es UUID indexado sin FK dura (D1, sigue patrón C-09).
- `umbral_materia` tiene unique constraint por (tenant, asignacion, materia).

Permisos nuevos:
- calificaciones:importar → PROFESOR, COORDINADOR
- calificaciones:leer     → PROFESOR, TUTOR, COORDINADOR, ADMIN
"""

from typing import Sequence, Union
import uuid
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, None] = "a8b9c0d1e2f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── calificacion ──────────────────────────────────────────────────────────
    op.create_table(
        "calificacion",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenant.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "entrada_padron_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("entrada_padron.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("materia_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actividad", sa.String(500), nullable=False),
        sa.Column("nota_numerica", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("nota_textual", sa.String(500), nullable=True),
        sa.Column(
            "origen",
            sa.Enum("Importado", "Manual", name="origencalificacion"),
            nullable=False,
        ),
        sa.Column("importado_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_calificacion_tenant_id", "calificacion", ["tenant_id"])
    op.create_index("ix_calificacion_entrada_padron_id", "calificacion", ["entrada_padron_id"])
    op.create_index("ix_calificacion_materia_id", "calificacion", ["materia_id"])
    op.create_index(
        "ix_calificacion_tenant_materia",
        "calificacion",
        ["tenant_id", "materia_id"],
    )

    # ── umbral_materia ────────────────────────────────────────────────────────
    op.create_table(
        "umbral_materia",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenant.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "asignacion_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("asignacion.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("materia_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("umbral_pct", sa.Integer, nullable=False, server_default="60"),
        sa.Column("valores_aprobatorios", postgresql.JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_umbral_materia_tenant_id", "umbral_materia", ["tenant_id"])
    op.create_index("ix_umbral_materia_asignacion_id", "umbral_materia", ["asignacion_id"])
    op.create_index("ix_umbral_materia_materia_id", "umbral_materia", ["materia_id"])
    op.create_index(
        "ix_umbral_materia_tenant_asignacion_materia",
        "umbral_materia",
        ["tenant_id", "asignacion_id", "materia_id"],
        unique=True,
    )

    # ── Permisos nuevos ───────────────────────────────────────────────────────
    now = datetime.now(timezone.utc)
    connection = op.get_bind()

    nuevos_permisos = [
        ("calificaciones:leer", "Consultar calificaciones y reportes de aprobación"),
    ]

    permiso_ids: dict[str, uuid.UUID] = {}
    for nombre, descripcion in nuevos_permisos:
        pid = uuid.uuid4()
        permiso_ids[nombre] = pid
        connection.execute(
            sa.text(
                "INSERT INTO permiso (id, nombre, descripcion, created_at, updated_at) "
                "VALUES (:id, :nombre, :descripcion, :created_at, :updated_at)"
            ),
            {
                "id": pid,
                "nombre": nombre,
                "descripcion": descripcion,
                "created_at": now,
                "updated_at": now,
            },
        )

    # Asignar permisos a roles
    rol_permisos = [
        # calificaciones:leer → PROFESOR, TUTOR, COORDINADOR, ADMIN
        ("PROFESOR", "calificaciones:leer"),
        ("TUTOR", "calificaciones:leer"),
        ("COORDINADOR", "calificaciones:leer"),
        ("ADMIN", "calificaciones:leer"),
    ]

    for rol_nombre, permiso_nombre in rol_permisos:
        rol_row = connection.execute(
            sa.text("SELECT id FROM rol WHERE nombre = :nombre"),
            {"nombre": rol_nombre},
        ).fetchone()
        if rol_row is None:
            continue
        rp_id = uuid.uuid4()
        connection.execute(
            sa.text(
                "INSERT INTO rol_permiso (id, rol_id, permiso_id, created_at, updated_at) "
                "VALUES (:id, :rol_id, :permiso_id, :created_at, :updated_at)"
            ),
            {
                "id": rp_id,
                "rol_id": rol_row[0],
                "permiso_id": permiso_ids[permiso_nombre],
                "created_at": now,
                "updated_at": now,
            },
        )


def downgrade() -> None:
    # Eliminar permisos y sus rol_permiso (cascade via FK en rol_permiso → permiso)
    connection = op.get_bind()
    for nombre in ("calificaciones:leer",):
        connection.execute(
            sa.text("DELETE FROM permiso WHERE nombre = :nombre"),
            {"nombre": nombre},
        )

    op.drop_index("ix_umbral_materia_tenant_asignacion_materia", table_name="umbral_materia")
    op.drop_index("ix_umbral_materia_materia_id", table_name="umbral_materia")
    op.drop_index("ix_umbral_materia_asignacion_id", table_name="umbral_materia")
    op.drop_index("ix_umbral_materia_tenant_id", table_name="umbral_materia")
    op.drop_table("umbral_materia")

    op.drop_index("ix_calificacion_tenant_materia", table_name="calificacion")
    op.drop_index("ix_calificacion_materia_id", table_name="calificacion")
    op.drop_index("ix_calificacion_entrada_padron_id", table_name="calificacion")
    op.drop_index("ix_calificacion_tenant_id", table_name="calificacion")
    op.drop_table("calificacion")

    op.execute("DROP TYPE IF EXISTS origencalificacion")
