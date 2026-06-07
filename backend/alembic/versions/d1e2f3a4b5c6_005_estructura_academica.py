"""005_estructura_academica

Revision ID: d1e2f3a4b5c6
Revises: c4d5e6f7a8b9
Create Date: 2026-06-07 00:00:00.000000

"""
from typing import Sequence, Union
import uuid
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

revision: str = "d1e2f3a4b5c6"
down_revision: Union[str, None] = "c4d5e6f7a8b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Tablas ────────────────────────────────────────────────────────────────
    op.create_table(
        "carrera",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("codigo", sa.String(50), nullable=False),
        sa.Column("nombre", sa.String(255), nullable=False),
        sa.Column("estado", sa.String(20), nullable=False, server_default="Activa"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "codigo", name="uq_carrera_tenant_codigo"),
    )
    op.create_index("ix_carrera_tenant", "carrera", ["tenant_id"])

    op.create_table(
        "cohorte",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("carrera_id", sa.UUID(), nullable=False),
        sa.Column("nombre", sa.String(100), nullable=False),
        sa.Column("anio", sa.Integer(), nullable=False),
        sa.Column("vig_desde", sa.Date(), nullable=False),
        sa.Column("vig_hasta", sa.Date(), nullable=True),
        sa.Column("estado", sa.String(20), nullable=False, server_default="Activa"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["carrera_id"], ["carrera.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "carrera_id", "nombre", name="uq_cohorte_tenant_carrera_nombre"),
    )
    op.create_index("ix_cohorte_tenant", "cohorte", ["tenant_id"])
    op.create_index("ix_cohorte_carrera", "cohorte", ["carrera_id"])

    op.create_table(
        "materia",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("codigo", sa.String(50), nullable=False),
        sa.Column("nombre", sa.String(255), nullable=False),
        sa.Column("estado", sa.String(20), nullable=False, server_default="Activa"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "codigo", name="uq_materia_tenant_codigo"),
    )
    op.create_index("ix_materia_tenant", "materia", ["tenant_id"])

    op.create_table(
        "instancia_dictado",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("materia_id", sa.UUID(), nullable=False),
        sa.Column("cohorte_id", sa.UUID(), nullable=False),
        sa.Column("nombre", sa.String(255), nullable=False),
        sa.Column("periodo", sa.String(20), nullable=False),
        sa.Column("estado", sa.String(20), nullable=False, server_default="Activa"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["materia_id"], ["materia.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["cohorte_id"], ["cohorte.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id", "materia_id", "cohorte_id", "periodo",
            name="uq_instancia_tenant_materia_cohorte_periodo",
        ),
    )
    op.create_index("ix_instancia_tenant", "instancia_dictado", ["tenant_id"])
    op.create_index("ix_instancia_cohorte", "instancia_dictado", ["cohorte_id"])
    op.create_index("ix_instancia_materia", "instancia_dictado", ["materia_id"])

    # ── Permisos granulares de estructura ─────────────────────────────────────
    now = datetime.now(timezone.utc)
    nuevos_permisos = [
        "estructura:leer",
        "estructura:crear",
        "estructura:editar",
        "estructura:eliminar",
    ]
    permiso_data = [
        {"id": uuid.uuid4(), "nombre": p, "descripcion": f"Permiso {p}", "created_at": now, "updated_at": now}
        for p in nuevos_permisos
    ]
    connection = op.get_bind()
    for pd in permiso_data:
        connection.execute(
            sa.text(
                "INSERT INTO permiso (id, nombre, descripcion, created_at, updated_at) "
                "VALUES (:id, :nombre, :descripcion, :created_at, :updated_at) "
                "ON CONFLICT (nombre) DO NOTHING"
            ),
            pd,
        )

    # ── Asignar permisos a roles ───────────────────────────────────────────────
    matriz = {
        "ADMIN":        ["estructura:leer", "estructura:crear", "estructura:editar", "estructura:eliminar"],
        "COORDINADOR":  ["estructura:leer", "estructura:crear", "estructura:editar"],
        "PROFESOR":     ["estructura:leer"],
        "TUTOR":        ["estructura:leer"],
    }
    rol_rows = connection.execute(sa.text("SELECT id, nombre FROM rol")).fetchall()
    permiso_rows = connection.execute(sa.text("SELECT id, nombre FROM permiso WHERE nombre LIKE 'estructura:%'")).fetchall()
    rol_map = {r[1]: r[0] for r in rol_rows}
    permiso_map = {r[1]: r[0] for r in permiso_rows}

    for rol_nombre, perms in matriz.items():
        rol_id = rol_map.get(rol_nombre)
        if not rol_id:
            continue
        for p in perms:
            p_id = permiso_map.get(p)
            if not p_id:
                continue
            connection.execute(
                sa.text(
                    "INSERT INTO rol_permiso (id, rol_id, permiso_id, created_at, updated_at) "
                    "VALUES (:id, :rol_id, :permiso_id, :created_at, :updated_at) "
                    "ON CONFLICT (rol_id, permiso_id) DO NOTHING"
                ),
                {"id": uuid.uuid4(), "rol_id": rol_id, "permiso_id": p_id, "created_at": now, "updated_at": now},
            )


def downgrade() -> None:
    op.drop_index("ix_instancia_materia", table_name="instancia_dictado")
    op.drop_index("ix_instancia_cohorte", table_name="instancia_dictado")
    op.drop_index("ix_instancia_tenant", table_name="instancia_dictado")
    op.drop_table("instancia_dictado")

    op.drop_index("ix_materia_tenant", table_name="materia")
    op.drop_table("materia")

    op.drop_index("ix_cohorte_carrera", table_name="cohorte")
    op.drop_index("ix_cohorte_tenant", table_name="cohorte")
    op.drop_table("cohorte")

    op.drop_index("ix_carrera_tenant", table_name="carrera")
    op.drop_table("carrera")

    connection = op.get_bind()
    for p in ["estructura:leer", "estructura:crear", "estructura:editar", "estructura:eliminar"]:
        connection.execute(sa.text("DELETE FROM permiso WHERE nombre = :nombre"), {"nombre": p})
