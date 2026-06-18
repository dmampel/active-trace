"""014_comunicacion

Revision ID: d4e5f6a7b8c9
Revises: c2d3e4f5a6b7
Create Date: 2026-06-17 00:00:00.000000

Crea la tabla `comunicacion` para el módulo de mensajería saliente (C-12):
- Tabla comunicacion con máquina de estados Pendiente→Enviando→Enviado/Error/Cancelado
- Enum `estadocomunicacion` en PostgreSQL
- Columna `requiere_aprobacion` en tabla `tenant`
- Permisos: comunicacion:enviar, comunicacion:aprobar, comunicacion:ver
- Asignación de permisos a roles

`destinatario` es TEXT — el cifrado AES-256 es responsabilidad de la capa app.
"""

from typing import Sequence, Union
import uuid
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c2d3e4f5a6b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Crear enum estadocomunicacion
    op.execute(
        "CREATE TYPE estadocomunicacion AS ENUM "
        "('Pendiente', 'Enviando', 'Enviado', 'Error', 'Cancelado')"
    )

    # 2. Agregar columna requiere_aprobacion a tenant
    op.add_column(
        "tenant",
        sa.Column(
            "requiere_aprobacion",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    # 3. Crear tabla comunicacion
    op.create_table(
        "comunicacion",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tenant.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("enviado_por", UUID(as_uuid=True), nullable=False),
        sa.Column("materia_id", UUID(as_uuid=True), nullable=False),
        # TEXT — cifrado AES-256 en app-level
        sa.Column("destinatario", sa.Text, nullable=False),
        sa.Column("asunto", sa.String(500), nullable=False),
        sa.Column("cuerpo", sa.Text, nullable=False),
        sa.Column(
            "estado",
            sa.Enum(
                "Pendiente", "Enviando", "Enviado", "Error", "Cancelado",
                name="estadocomunicacion",
                create_type=False,  # ya creado arriba
            ),
            nullable=False,
            server_default="Pendiente",
        ),
        sa.Column("lote_id", UUID(as_uuid=True), nullable=True),
        sa.Column("enviado_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("aprobado_at", sa.DateTime(timezone=True), nullable=True),
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

    # 4. Índices
    op.create_index("ix_comunicacion_tenant_id", "comunicacion", ["tenant_id"])
    op.create_index("ix_comunicacion_estado", "comunicacion", ["estado"])
    op.create_index("ix_comunicacion_lote_id", "comunicacion", ["lote_id"])
    op.create_index("ix_comunicacion_enviado_por", "comunicacion", ["enviado_por"])
    op.create_index("ix_comunicacion_materia_id", "comunicacion", ["materia_id"])
    op.create_index(
        "ix_comunicacion_tenant_estado", "comunicacion", ["tenant_id", "estado"]
    )
    op.create_index(
        "ix_comunicacion_tenant_lote", "comunicacion", ["tenant_id", "lote_id"]
    )

    # 5. Insertar permisos comunicacion:*
    connection = op.get_bind()
    now = datetime.now(timezone.utc)

    permisos = [
        ("comunicacion:enviar", "Encolar y previsualizar mensajes salientes"),
        ("comunicacion:aprobar", "Aprobar o cancelar lotes de mensajes"),
        ("comunicacion:ver", "Ver historial de comunicaciones"),
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

    # 6. Asignar permisos a roles
    # comunicacion:enviar → PROFESOR, COORDINADOR, ADMIN
    # comunicacion:aprobar → COORDINADOR, ADMIN
    # comunicacion:ver → PROFESOR, COORDINADOR, ADMIN
    asignaciones = [
        ("comunicacion:enviar", ["PROFESOR", "COORDINADOR", "ADMIN"]),
        ("comunicacion:aprobar", ["COORDINADOR", "ADMIN"]),
        ("comunicacion:ver", ["PROFESOR", "COORDINADOR", "ADMIN"]),
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

    # Eliminar permisos comunicacion:*
    connection.execute(
        sa.text("DELETE FROM permiso WHERE nombre LIKE 'comunicacion:%'")
    )

    # Eliminar tabla e índices
    op.drop_index("ix_comunicacion_tenant_lote", table_name="comunicacion")
    op.drop_index("ix_comunicacion_tenant_estado", table_name="comunicacion")
    op.drop_index("ix_comunicacion_materia_id", table_name="comunicacion")
    op.drop_index("ix_comunicacion_enviado_por", table_name="comunicacion")
    op.drop_index("ix_comunicacion_lote_id", table_name="comunicacion")
    op.drop_index("ix_comunicacion_estado", table_name="comunicacion")
    op.drop_index("ix_comunicacion_tenant_id", table_name="comunicacion")
    op.drop_table("comunicacion")

    # Eliminar columna del tenant
    op.drop_column("tenant", "requiere_aprobacion")

    # Eliminar enum
    op.execute("DROP TYPE IF EXISTS estadocomunicacion")
