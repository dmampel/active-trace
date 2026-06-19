"""020_mensajeria_interna

Revision ID: d0e1f2a3b4c5
Revises: c3d4e5f6a7b8
Create Date: 2026-06-19 00:00:00.000000

Crea las tablas de mensajería interna (C-20):
- hilo_mensaje: conversación con asunto y participantes
- mensaje_interno: mensajes individuales dentro del hilo

También agrega permisos RBAC:
- perfil:editar  → todos los roles (autoservicio)
- inbox:usar     → todos los roles (autoservicio)
"""

from typing import Sequence, Union
import uuid
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision: str = "d0e1f2a3b4c5"
down_revision: Union[str, None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Tabla hilo_mensaje ────────────────────────────────────────────────────
    op.create_table(
        "hilo_mensaje",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False),
        sa.Column("asunto", sa.String(255), nullable=False),
        sa.Column("creado_por", UUID(as_uuid=True), sa.ForeignKey("user.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_hilo_mensaje_tenant_id", "hilo_mensaje", ["tenant_id"])
    op.create_index("ix_hilo_mensaje_creado_por", "hilo_mensaje", ["creado_por"])

    # ── Tabla mensaje_interno ─────────────────────────────────────────────────
    op.create_table(
        "mensaje_interno",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False),
        sa.Column("hilo_id", UUID(as_uuid=True), sa.ForeignKey("hilo_mensaje.id", ondelete="CASCADE"), nullable=False),
        sa.Column("autor_id", UUID(as_uuid=True), sa.ForeignKey("user.id", ondelete="CASCADE"), nullable=False),
        sa.Column("destinatario_id", UUID(as_uuid=True), sa.ForeignKey("user.id", ondelete="CASCADE"), nullable=False),
        sa.Column("cuerpo", sa.Text(), nullable=False),
        sa.Column("leido", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_mensaje_interno_tenant_id", "mensaje_interno", ["tenant_id"])
    op.create_index("ix_mensaje_interno_hilo_id", "mensaje_interno", ["hilo_id"])
    op.create_index("ix_mensaje_interno_destinatario_id", "mensaje_interno", ["destinatario_id"])
    op.create_index("ix_mensaje_interno_autor_id", "mensaje_interno", ["autor_id"])

    # ── Permisos RBAC: perfil:editar e inbox:usar ─────────────────────────────
    connection = op.get_bind()
    now = datetime.now(timezone.utc)

    nuevos_permisos = [
        ("perfil:editar", "Leer y editar el propio perfil (autoservicio del usuario)"),
        ("inbox:usar", "Usar el inbox interno: leer, enviar y responder mensajes entre usuarios"),
    ]

    # Roles que reciben ambos permisos (todos los roles activos)
    roles_con_permiso = ["ADMIN", "COORDINADOR", "TUTOR", "PROFESOR", "NEXO", "FINANZAS", "ALUMNO"]

    for nombre_permiso, descripcion in nuevos_permisos:
        permiso_id = uuid.uuid4()
        connection.execute(
            sa.text(
                "INSERT INTO permiso (id, nombre, descripcion, created_at, updated_at) "
                "VALUES (:id, :nombre, :descripcion, :created_at, :updated_at)"
            ),
            {
                "id": permiso_id,
                "nombre": nombre_permiso,
                "descripcion": descripcion,
                "created_at": now,
                "updated_at": now,
            },
        )

        for rol_nombre in roles_con_permiso:
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
                    "permiso_id": permiso_id,
                    "created_at": now,
                    "updated_at": now,
                },
            )


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        sa.text("DELETE FROM permiso WHERE nombre IN (:p1, :p2)"),
        {"p1": "perfil:editar", "p2": "inbox:usar"},
    )
    op.drop_table("mensaje_interno")
    op.drop_table("hilo_mensaje")
