"""008_padron_tables

Revision ID: a8b9c0d1e2f3
Revises: f1a2b3c4d5e6
Create Date: 2026-06-16 00:00:00.000000

Agrega tablas del módulo padrón (C-09):
- version_padron: contenedor versionado de padrón por (tenant, materia, cohorte)
- entrada_padron: una fila del padrón (alumno), con email cifrado
- tenant_moodle_config: configuración Moodle WS por tenant (url y token cifrados)

Permisos nuevos:
- padron:importar → PROFESOR, COORDINADOR
- padron:leer     → PROFESOR, TUTOR, COORDINADOR, ADMIN
"""
from typing import Sequence, Union
import uuid
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "a8b9c0d1e2f3"
down_revision: Union[str, None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── version_padron ────────────────────────────────────────────────────────
    op.create_table(
        "version_padron",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False),
        sa.Column("materia_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cohorte_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cargado_por", postgresql.UUID(as_uuid=True), sa.ForeignKey("user.id", ondelete="SET NULL"), nullable=True),
        sa.Column("cargado_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("activa", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_version_padron_tenant_id", "version_padron", ["tenant_id"])
    op.create_index("ix_version_padron_materia_id", "version_padron", ["materia_id"])
    op.create_index("ix_version_padron_cohorte_id", "version_padron", ["cohorte_id"])
    op.create_index(
        "ix_version_padron_tenant_materia_cohorte_activa",
        "version_padron",
        ["tenant_id", "materia_id", "cohorte_id", "activa"],
    )

    # ── entrada_padron ────────────────────────────────────────────────────────
    op.create_table(
        "entrada_padron",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("version_padron.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False),
        sa.Column("usuario_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("user.id", ondelete="SET NULL"), nullable=True),
        sa.Column("nombre", sa.String(255), nullable=False),
        sa.Column("apellidos", sa.String(255), nullable=False),
        sa.Column("email_enc", sa.String(512), nullable=False),
        sa.Column("comision", sa.String(100), nullable=True),
        sa.Column("regional", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_entrada_padron_version_id", "entrada_padron", ["version_id"])
    op.create_index("ix_entrada_padron_tenant_id", "entrada_padron", ["tenant_id"])

    # ── tenant_moodle_config ──────────────────────────────────────────────────
    op.create_table(
        "tenant_moodle_config",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False),
        sa.Column("moodle_url_enc", sa.String(512), nullable=False),
        sa.Column("moodle_token_enc", sa.String(512), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("tenant_id", name="uq_tenant_moodle_config_tenant"),
    )
    op.create_index("ix_tenant_moodle_config_tenant_id", "tenant_moodle_config", ["tenant_id"])

    # ── Permisos nuevos ───────────────────────────────────────────────────────
    now = datetime.now(timezone.utc)
    connection = op.get_bind()

    nuevos_permisos = [
        ("padron:importar", "Importar padrón de alumnos desde archivo o Moodle"),
        ("padron:leer", "Consultar padrón de alumnos y versiones"),
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
            {"id": pid, "nombre": nombre, "descripcion": descripcion, "created_at": now, "updated_at": now},
        )

    # Asignar permisos a roles
    rol_permisos = [
        # padron:importar → PROFESOR, COORDINADOR
        ("PROFESOR", "padron:importar"),
        ("COORDINADOR", "padron:importar"),
        # padron:leer → PROFESOR, TUTOR, COORDINADOR, ADMIN
        ("PROFESOR", "padron:leer"),
        ("TUTOR", "padron:leer"),
        ("COORDINADOR", "padron:leer"),
        ("ADMIN", "padron:leer"),
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
    # Eliminar permisos
    connection = op.get_bind()
    for nombre in ("padron:importar", "padron:leer"):
        connection.execute(
            sa.text("DELETE FROM permiso WHERE nombre = :nombre"),
            {"nombre": nombre},
        )

    op.drop_index("ix_tenant_moodle_config_tenant_id", table_name="tenant_moodle_config")
    op.drop_table("tenant_moodle_config")

    op.drop_index("ix_entrada_padron_tenant_id", table_name="entrada_padron")
    op.drop_index("ix_entrada_padron_version_id", table_name="entrada_padron")
    op.drop_table("entrada_padron")

    op.drop_index("ix_version_padron_tenant_materia_cohorte_activa", table_name="version_padron")
    op.drop_index("ix_version_padron_cohorte_id", table_name="version_padron")
    op.drop_index("ix_version_padron_materia_id", table_name="version_padron")
    op.drop_index("ix_version_padron_tenant_id", table_name="version_padron")
    op.drop_table("version_padron")
