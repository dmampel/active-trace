"""018_liquidaciones_honorarios

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f7
Create Date: 2026-06-19 00:00:00.000000

Crea el módulo de liquidaciones y honorarios (C-18):
- Columna `plus_key TEXT NULL` en `instancia_dictado`
- Tabla `salario_base`: grilla salarial base por rol con vigencia temporal
- Tabla `salario_plus`: grilla de plus por (grupo/clave × rol) con vigencia temporal
- Tabla `liquidacion`: liquidación de honorarios por (cohorte × período × docente)
- Tabla `factura`: facturas de docentes monotributistas (facturantes)
- Permisos: liquidaciones:ver, liquidaciones:calcular, liquidaciones:cerrar,
            liquidaciones:configurar-salarios, liquidaciones:exportar → rol FINANZAS
"""

from typing import Sequence, Union
import uuid
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. plus_key en instancia_dictado (ALTER TABLE nullable — no destructivo) ──
    op.add_column(
        "instancia_dictado",
        sa.Column("plus_key", sa.Text, nullable=True),
    )
    op.create_index("ix_instancia_dictado_plus_key", "instancia_dictado", ["plus_key"])

    # ── 2. Tabla salario_base ─────────────────────────────────────────────────
    op.create_table(
        "salario_base",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tenant.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("rol", sa.String(50), nullable=False),
        sa.Column("monto", sa.Numeric(12, 2), nullable=False),
        sa.Column("desde", sa.Date, nullable=False),
        sa.Column("hasta", sa.Date, nullable=True),
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
    op.create_index("ix_salario_base_tenant", "salario_base", ["tenant_id"])
    op.create_index("ix_salario_base_rol", "salario_base", ["tenant_id", "rol"])

    # ── 3. Tabla salario_plus ─────────────────────────────────────────────────
    op.create_table(
        "salario_plus",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tenant.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("grupo", sa.Text, nullable=False),   # clave Plus libre (e.g. "PROG")
        sa.Column("rol", sa.String(50), nullable=False),
        sa.Column("descripcion", sa.Text, nullable=True),
        sa.Column("monto", sa.Numeric(12, 2), nullable=False),
        sa.Column("desde", sa.Date, nullable=False),
        sa.Column("hasta", sa.Date, nullable=True),
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
    op.create_index("ix_salario_plus_tenant", "salario_plus", ["tenant_id"])
    op.create_index("ix_salario_plus_grupo_rol", "salario_plus", ["tenant_id", "grupo", "rol"])

    # ── 4. Tabla liquidacion ──────────────────────────────────────────────────
    op.create_table(
        "liquidacion",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tenant.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "cohorte_id",
            UUID(as_uuid=True),
            sa.ForeignKey("cohorte.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("periodo", sa.String(20), nullable=False),
        sa.Column(
            "usuario_id",
            UUID(as_uuid=True),
            sa.ForeignKey("user.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("rol", sa.String(50), nullable=False),
        sa.Column("comisiones", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("monto_base", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("monto_plus", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("total", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("es_nexo", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("excluido_por_factura", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("estado", sa.String(20), nullable=False, server_default="Abierta"),
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
        sa.UniqueConstraint(
            "tenant_id", "cohorte_id", "periodo", "usuario_id",
            name="uq_liquidacion_tenant_cohorte_periodo_usuario",
        ),
    )
    op.create_index("ix_liquidacion_tenant", "liquidacion", ["tenant_id"])
    op.create_index("ix_liquidacion_cohorte_periodo", "liquidacion", ["cohorte_id", "periodo"])
    op.create_index("ix_liquidacion_usuario", "liquidacion", ["usuario_id"])

    # ── 5. Tabla factura ──────────────────────────────────────────────────────
    op.create_table(
        "factura",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tenant.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "usuario_id",
            UUID(as_uuid=True),
            sa.ForeignKey("user.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("periodo", sa.String(20), nullable=False),
        sa.Column("detalle", sa.Text, nullable=True),
        sa.Column("referencia_archivo", sa.Text, nullable=True),
        sa.Column("tamano_kb", sa.Integer, nullable=True),
        sa.Column("estado", sa.String(20), nullable=False, server_default="Pendiente"),
        sa.Column("cargada_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("abonada_at", sa.DateTime(timezone=True), nullable=True),
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
    op.create_index("ix_factura_tenant", "factura", ["tenant_id"])
    op.create_index("ix_factura_usuario", "factura", ["usuario_id"])
    op.create_index("ix_factura_periodo", "factura", ["tenant_id", "periodo"])

    # ── 6. Permisos liquidaciones:* → rol FINANZAS ────────────────────────────
    connection = op.get_bind()
    now = datetime.now(timezone.utc)

    permisos = [
        ("liquidaciones:ver", "Ver liquidaciones y facturas del tenant"),
        ("liquidaciones:calcular", "Calcular liquidaciones y gestionar facturas"),
        ("liquidaciones:cerrar", "Cerrar liquidaciones de un período"),
        ("liquidaciones:configurar-salarios", "Crear y editar grilla salarial"),
        ("liquidaciones:exportar", "Exportar liquidaciones a planilla"),
    ]

    permiso_ids: dict[str, uuid.UUID] = {}
    for nombre, descripcion in permisos:
        existing = connection.execute(
            sa.text("SELECT id FROM permiso WHERE nombre = :nombre"),
            {"nombre": nombre},
        ).fetchone()
        if existing is None:
            pid = uuid.uuid4()
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
            permiso_ids[nombre] = pid
        else:
            permiso_ids[nombre] = existing[0]

    # Todos los permisos de liquidaciones → FINANZAS
    for perm_nombre in [p[0] for p in permisos]:
        pid = permiso_ids[perm_nombre]
        rol_row = connection.execute(
            sa.text("SELECT id FROM rol WHERE nombre = :nombre"),
            {"nombre": "FINANZAS"},
        ).fetchone()
        if rol_row is None:
            continue
        existing_rp = connection.execute(
            sa.text(
                "SELECT id FROM rol_permiso WHERE rol_id = :rol_id AND permiso_id = :permiso_id"
            ),
            {"rol_id": rol_row[0], "permiso_id": pid},
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
                    "permiso_id": pid,
                    "created_at": now,
                    "updated_at": now,
                },
            )


def downgrade() -> None:
    connection = op.get_bind()

    # Eliminar permisos liquidaciones:* (cascade elimina rol_permiso)
    connection.execute(
        sa.text(
            "DELETE FROM permiso WHERE nombre IN ("
            "'liquidaciones:ver', 'liquidaciones:calcular', 'liquidaciones:cerrar',"
            "'liquidaciones:configurar-salarios', 'liquidaciones:exportar'"
            ")"
        )
    )

    # Eliminar tablas en orden inverso (respeta FKs)
    op.drop_index("ix_factura_periodo", table_name="factura")
    op.drop_index("ix_factura_usuario", table_name="factura")
    op.drop_index("ix_factura_tenant", table_name="factura")
    op.drop_table("factura")

    op.drop_index("ix_liquidacion_usuario", table_name="liquidacion")
    op.drop_index("ix_liquidacion_cohorte_periodo", table_name="liquidacion")
    op.drop_index("ix_liquidacion_tenant", table_name="liquidacion")
    op.drop_table("liquidacion")

    op.drop_index("ix_salario_plus_grupo_rol", table_name="salario_plus")
    op.drop_index("ix_salario_plus_tenant", table_name="salario_plus")
    op.drop_table("salario_plus")

    op.drop_index("ix_salario_base_rol", table_name="salario_base")
    op.drop_index("ix_salario_base_tenant", table_name="salario_base")
    op.drop_table("salario_base")

    op.drop_index("ix_instancia_dictado_plus_key", table_name="instancia_dictado")
    op.drop_column("instancia_dictado", "plus_key")
