"""015_avisos_acknowledgment

Revision ID: a0b1c2d3e4f5
Revises: f6a7b8c9d0e1
Create Date: 2026-06-18 00:00:00.000000

Crea las tablas del módulo de avisos y acknowledgment (C-15):
- Enums: `alcanceaviso`, `severidadaviso`
- Tabla `aviso`: aviso institucional segmentado por audiencia con ventana de vigencia
- Tabla `acknowledgment_aviso`: confirmación de lectura por usuario (idempotente)
- Índices compuestos para el query de feed
- Permiso: avisos:publicar → COORDINADOR, ADMIN
"""

from typing import Sequence, Union
import uuid
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "a0b1c2d3e4f5"
down_revision: Union[str, None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 2. Tabla aviso ────────────────────────────────────────────────────────
    op.create_table(
        "aviso",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tenant.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "alcance",
            sa.Enum(
                "Global", "PorMateria", "PorCohorte", "PorRol",
                name="alcanceaviso",
            ),
            nullable=False,
        ),
        sa.Column(
            "materia_id",
            UUID(as_uuid=True),
            sa.ForeignKey("materia.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column(
            "cohorte_id",
            UUID(as_uuid=True),
            sa.ForeignKey("cohorte.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("rol_destino", sa.String(50), nullable=True),
        sa.Column(
            "severidad",
            sa.Enum(
                "Info", "Advertencia", "Critico",
                name="severidadaviso",
            ),
            nullable=False,
            server_default="Info",
        ),
        sa.Column("titulo", sa.String(255), nullable=False),
        sa.Column("cuerpo", sa.Text, nullable=False),
        sa.Column("inicio_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fin_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("orden", sa.Integer, nullable=False, server_default="0"),
        sa.Column("activo", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("requiere_ack", sa.Boolean, nullable=False, server_default="false"),
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
    op.create_index("ix_aviso_alcance", "aviso", ["alcance"])
    op.create_index(
        "ix_aviso_feed",
        "aviso",
        ["tenant_id", "alcance", "activo", "inicio_en"],
    )

    # ── 3. Tabla acknowledgment_aviso ─────────────────────────────────────────
    op.create_table(
        "acknowledgment_aviso",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "aviso_id",
            UUID(as_uuid=True),
            sa.ForeignKey("aviso.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "usuario_id",
            UUID(as_uuid=True),
            sa.ForeignKey("user.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("confirmado_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "aviso_id", "usuario_id", name="uix_ack_aviso_usuario"
        ),
    )
    op.create_index("ix_ack_aviso_aviso_id", "acknowledgment_aviso", ["aviso_id"])
    op.create_index("ix_ack_aviso_usuario_id", "acknowledgment_aviso", ["usuario_id"])

    # ── 4. Permiso avisos:publicar ─────────────────────────────────────────────
    connection = op.get_bind()
    now = datetime.now(timezone.utc)

    permiso_id = uuid.uuid4()
    connection.execute(
        sa.text(
            "INSERT INTO permiso (id, nombre, descripcion, created_at, updated_at) "
            "VALUES (:id, :nombre, :descripcion, :created_at, :updated_at)"
        ),
        {
            "id": permiso_id,
            "nombre": "avisos:publicar",
            "descripcion": "Crear, editar y eliminar avisos institucionales",
            "created_at": now,
            "updated_at": now,
        },
    )

    for rol_nombre in ["COORDINADOR", "ADMIN"]:
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

    # Eliminar permiso avisos:publicar (cascade elimina rol_permiso)
    connection.execute(
        sa.text("DELETE FROM permiso WHERE nombre = 'avisos:publicar'")
    )

    # Eliminar tablas en orden inverso
    op.drop_index("ix_ack_aviso_usuario_id", table_name="acknowledgment_aviso")
    op.drop_index("ix_ack_aviso_aviso_id", table_name="acknowledgment_aviso")
    op.drop_table("acknowledgment_aviso")

    op.drop_index("ix_aviso_feed", table_name="aviso")
    op.drop_index("ix_aviso_alcance", table_name="aviso")
    op.drop_table("aviso")

    # Eliminar enums
    op.execute("DROP TYPE IF EXISTS severidadaviso")
    op.execute("DROP TYPE IF EXISTS alcanceaviso")
