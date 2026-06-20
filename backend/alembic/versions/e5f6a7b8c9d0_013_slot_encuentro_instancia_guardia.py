"""013_slot_encuentro_instancia_guardia

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-06-17 00:00:00.000000

Crea las tablas del módulo de encuentros y guardias (C-13):
- Enums: `diasemana`, `estadoinstanciaencuentro`, `estadoguardia`
- Tabla `slot_encuentro`: serie recurrente o encuentro único vinculado a una asignación
- Tabla `instancia_encuentro`: ocurrencia individual de un slot (editable por instancia)
- Tabla `guardia`: registro de atención de guardia por TUTOR
- Permisos: encuentros:gestionar, encuentros:ver_admin, guardias:registrar, guardias:consultar, guardias:exportar
- Asignación de permisos a roles según D5

Notas:
- `slot_encuentro.cant_semanas > 0` XOR `fecha_unica` se valida en la capa Pydantic (RN-13).
- `instancia_encuentro` tiene soft delete (deleted_at) por regla dura #13.
- `guardia.asignacion_id` es FK a `asignacion` — nunca proviene del body HTTP.
"""

from typing import Sequence, Union
import uuid
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 2. Tabla slot_encuentro ───────────────────────────────────────────────
    op.create_table(
        "slot_encuentro",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tenant.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "asignacion_id",
            UUID(as_uuid=True),
            sa.ForeignKey("asignacion.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("titulo", sa.String(255), nullable=False),
        # Recurrente: cant_semanas > 0 y fecha_unica IS NULL
        sa.Column("cant_semanas", sa.Integer, nullable=True),
        sa.Column("fecha_inicio", sa.Date, nullable=True),
        sa.Column(
            "dia_semana",
            sa.Enum(
                "Lunes", "Martes", "Miercoles", "Jueves", "Viernes", "Sabado", "Domingo",
                name="diasemana",
            ),
            nullable=True,
        ),
        # Único: fecha_unica IS NOT NULL y cant_semanas IS NULL
        sa.Column("fecha_unica", sa.Date, nullable=True),
        sa.Column("hora", sa.Time, nullable=False),
        sa.Column("meet_url", sa.String(500), nullable=True),
        sa.Column("descripcion", sa.Text, nullable=True),
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
    op.create_index("ix_slot_encuentro_tenant_id", "slot_encuentro", ["tenant_id"])
    op.create_index("ix_slot_encuentro_asignacion_id", "slot_encuentro", ["asignacion_id"])

    # ── 3. Tabla instancia_encuentro ──────────────────────────────────────────
    op.create_table(
        "instancia_encuentro",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tenant.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # FK nullable: si el slot se elimina, las instancias pueden quedar huérfanas
        # (soft delete del slot, la instancia mantiene su historial)
        sa.Column(
            "slot_id",
            UUID(as_uuid=True),
            sa.ForeignKey("slot_encuentro.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("fecha", sa.Date, nullable=False),
        sa.Column("hora", sa.Time, nullable=False),
        sa.Column(
            "estado",
            sa.Enum(
                "Programado", "Realizado", "Cancelado",
                name="estadoinstanciaencuentro",
            ),
            nullable=False,
            server_default="Programado",
        ),
        sa.Column("meet_url", sa.String(500), nullable=True),
        sa.Column("video_url", sa.String(500), nullable=True),
        sa.Column("comentario", sa.Text, nullable=True),
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
    op.create_index("ix_instancia_encuentro_tenant_id", "instancia_encuentro", ["tenant_id"])
    op.create_index("ix_instancia_encuentro_slot_id", "instancia_encuentro", ["slot_id"])
    op.create_index("ix_instancia_encuentro_fecha", "instancia_encuentro", ["fecha"])

    # ── 4. Tabla guardia ──────────────────────────────────────────────────────
    op.create_table(
        "guardia",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tenant.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "asignacion_id",
            UUID(as_uuid=True),
            sa.ForeignKey("asignacion.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("materia_id", UUID(as_uuid=True), nullable=False),
        sa.Column("carrera_id", UUID(as_uuid=True), nullable=True),
        sa.Column("cohorte_id", UUID(as_uuid=True), nullable=True),
        sa.Column("dia", sa.Date, nullable=False),
        # Texto libre: "14:00–14:45" (KB dice texto libre)
        sa.Column("horario", sa.String(100), nullable=False),
        sa.Column(
            "estado",
            sa.Enum(
                "Pendiente", "Cubierta", "Ausente",
                name="estadoguardia",
            ),
            nullable=False,
            server_default="Pendiente",
        ),
        sa.Column("comentarios", sa.Text, nullable=True),
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
    op.create_index("ix_guardia_tenant_id", "guardia", ["tenant_id"])
    op.create_index("ix_guardia_asignacion_id", "guardia", ["asignacion_id"])
    op.create_index("ix_guardia_materia_id", "guardia", ["materia_id"])
    op.create_index("ix_guardia_dia", "guardia", ["dia"])
    op.create_index("ix_guardia_tenant_estado", "guardia", ["tenant_id", "estado"])

    # ── 5. Permisos e asignaciones a roles ────────────────────────────────────
    connection = op.get_bind()
    now = datetime.now(timezone.utc)

    permisos = [
        ("encuentros:gestionar", "Crear y editar slots e instancias de encuentros"),
        ("encuentros:ver_admin", "Ver todos los encuentros del tenant"),
        ("guardias:registrar", "Registrar guardias propias (TUTOR)"),
        ("guardias:consultar", "Consultar guardias del tenant"),
        ("guardias:exportar", "Exportar guardias a CSV"),
    ]
    permiso_ids: dict[str, uuid.UUID] = {}
    for nombre, descripcion in permisos:
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

    # D5: asignación de permisos a roles
    # encuentros:gestionar   → PROFESOR, COORDINADOR, ADMIN
    # encuentros:ver_admin   → COORDINADOR, ADMIN
    # guardias:registrar     → TUTOR
    # guardias:consultar     → TUTOR (propias), COORDINADOR, ADMIN (todas)
    # guardias:exportar      → COORDINADOR, ADMIN
    asignaciones = [
        ("encuentros:gestionar", ["PROFESOR", "COORDINADOR", "ADMIN"]),
        ("encuentros:ver_admin", ["COORDINADOR", "ADMIN"]),
        ("guardias:registrar", ["TUTOR"]),
        ("guardias:consultar", ["TUTOR", "COORDINADOR", "ADMIN"]),
        ("guardias:exportar", ["COORDINADOR", "ADMIN"]),
    ]
    for perm_nombre, roles in asignaciones:
        pid = permiso_ids[perm_nombre]
        for rol_nombre in roles:
            rol_row = connection.execute(
                sa.text("SELECT id FROM rol WHERE nombre = :nombre"),
                {"nombre": rol_nombre},
            ).fetchone()
            if rol_row is None:
                continue
            connection.execute(
                sa.text(
                    "INSERT INTO rol_permiso (id, rol_id, permiso_id, created_at, updated_at) "
                    "VALUES (:id, :rol_id, :permiso_id, :created_at, :updated_at)"
                ),
                {
                    "id": uuid.uuid4(),
                    "rol_id": rol_row[0],
                    "permiso_id": pid,
                    "created_at": now,
                    "updated_at": now,
                },
            )


def downgrade() -> None:
    connection = op.get_bind()

    # Eliminar permisos encuentros:* y guardias:*
    connection.execute(
        sa.text(
            "DELETE FROM permiso WHERE nombre LIKE 'encuentros:%' "
            "OR nombre LIKE 'guardias:%'"
        )
    )

    # Eliminar tablas (orden inverso: dependencias primero)
    op.drop_index("ix_guardia_tenant_estado", table_name="guardia")
    op.drop_index("ix_guardia_dia", table_name="guardia")
    op.drop_index("ix_guardia_materia_id", table_name="guardia")
    op.drop_index("ix_guardia_asignacion_id", table_name="guardia")
    op.drop_index("ix_guardia_tenant_id", table_name="guardia")
    op.drop_table("guardia")

    op.drop_index("ix_instancia_encuentro_fecha", table_name="instancia_encuentro")
    op.drop_index("ix_instancia_encuentro_slot_id", table_name="instancia_encuentro")
    op.drop_index("ix_instancia_encuentro_tenant_id", table_name="instancia_encuentro")
    op.drop_table("instancia_encuentro")

    op.drop_index("ix_slot_encuentro_asignacion_id", table_name="slot_encuentro")
    op.drop_index("ix_slot_encuentro_tenant_id", table_name="slot_encuentro")
    op.drop_table("slot_encuentro")

    # Eliminar enums
    op.execute("DROP TYPE IF EXISTS estadoguardia")
    op.execute("DROP TYPE IF EXISTS estadoinstanciaencuentro")
    op.execute("DROP TYPE IF EXISTS diasemana")
