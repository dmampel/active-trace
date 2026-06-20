"""006_usuarios_y_asignaciones

Revision ID: e1f2a3b4c5d6
Revises: d1e2f3a4b5c6
Create Date: 2026-06-09 00:00:00.000000

Agrega:
- enum `roldominio`
- columnas de perfil PII en tabla `user` (nullables/default seguro)
- tabla `asignacion` con índices y FKs RESTRICT
- permisos: usuarios:gestionar, equipos:asignar (ADMIN/COORDINADOR)
            atrasados:ver, calificaciones:ver (NEXO)
"""
from typing import Sequence, Union
import uuid
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

revision: str = "e1f2a3b4c5d6"
down_revision: Union[str, None] = "d1e2f3a4b5c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. Extender tabla user con columnas de perfil PII ────────────────────
    op.add_column("user", sa.Column("nombre", sa.String(255), nullable=True))
    op.add_column("user", sa.Column("apellidos", sa.String(255), nullable=True))
    op.add_column("user", sa.Column("dni_enc", sa.String(512), nullable=True))
    op.add_column("user", sa.Column("cuil_enc", sa.String(512), nullable=True))
    op.add_column("user", sa.Column("cbu_enc", sa.String(512), nullable=True))
    op.add_column("user", sa.Column("alias_cbu_enc", sa.String(512), nullable=True))
    op.add_column("user", sa.Column("banco", sa.String(255), nullable=True))
    op.add_column("user", sa.Column("regional", sa.String(100), nullable=True))
    op.add_column("user", sa.Column("legajo", sa.String(50), nullable=True))
    op.add_column("user", sa.Column("legajo_profesional", sa.String(50), nullable=True))
    op.add_column("user", sa.Column("facturador", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column(
        "user",
        sa.Column("estado", sa.String(20), nullable=False, server_default="activa"),
    )

    # ── 3. Crear tabla asignacion ─────────────────────────────────────────────
    op.create_table(
        "asignacion",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("usuario_id", sa.UUID(), nullable=False),
        sa.Column("rol", sa.String(20), nullable=False),
        sa.Column("materia_id", sa.UUID(), nullable=True),
        sa.Column("carrera_id", sa.UUID(), nullable=True),
        sa.Column("cohorte_id", sa.UUID(), nullable=True),
        sa.Column("comisiones", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("responsable_id", sa.UUID(), nullable=True),
        sa.Column("desde", sa.Date(), nullable=False),
        sa.Column("hasta", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["usuario_id"], ["user.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["materia_id"], ["materia.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["carrera_id"], ["carrera.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["cohorte_id"], ["cohorte.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["responsable_id"], ["user.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_asignacion_tenant", "asignacion", ["tenant_id"])
    op.create_index("ix_asignacion_usuario", "asignacion", ["usuario_id"])

    # ── 4. Seed de permisos ───────────────────────────────────────────────────
    now = datetime.now(timezone.utc)
    connection = op.get_bind()

    nuevos_permisos = [
        ("usuarios:gestionar", "Gestión completa de usuarios del tenant"),
        ("equipos:asignar", "Crear y gestionar asignaciones de roles contextuales"),
        ("atrasados:ver", "Ver alumnos atrasados en la población asignada"),
        ("calificaciones:ver", "Ver calificaciones en la población asignada"),
    ]
    for nombre, descripcion in nuevos_permisos:
        connection.execute(
            sa.text(
                "INSERT INTO permiso (id, nombre, descripcion, created_at, updated_at) "
                "VALUES (:id, :nombre, :descripcion, :created_at, :updated_at) "
                "ON CONFLICT (nombre) DO NOTHING"
            ),
            {"id": uuid.uuid4(), "nombre": nombre, "descripcion": descripcion,
             "created_at": now, "updated_at": now},
        )

    # Asignar permisos a roles
    matriz = {
        "ADMIN":       ["usuarios:gestionar", "equipos:asignar"],
        "COORDINADOR": ["equipos:asignar"],
        "NEXO":        ["atrasados:ver", "calificaciones:ver"],
    }
    rol_rows = connection.execute(sa.text("SELECT id, nombre FROM rol")).fetchall()
    permiso_rows = connection.execute(
        sa.text("SELECT id, nombre FROM permiso WHERE nombre IN "
                "('usuarios:gestionar','equipos:asignar','atrasados:ver','calificaciones:ver')")
    ).fetchall()
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
                {"id": uuid.uuid4(), "rol_id": rol_id, "permiso_id": p_id,
                 "created_at": now, "updated_at": now},
            )


def downgrade() -> None:
    # Eliminar permisos semilla
    connection = op.get_bind()
    for nombre in ["usuarios:gestionar", "equipos:asignar", "atrasados:ver", "calificaciones:ver"]:
        connection.execute(sa.text("DELETE FROM permiso WHERE nombre = :nombre"), {"nombre": nombre})

    # Eliminar tabla asignacion
    op.drop_index("ix_asignacion_usuario", table_name="asignacion")
    op.drop_index("ix_asignacion_tenant", table_name="asignacion")
    op.drop_table("asignacion")

    # Eliminar columnas PII de user
    for col in [
        "estado", "facturador", "legajo_profesional", "legajo",
        "regional", "banco", "alias_cbu_enc", "cbu_enc", "cuil_enc",
        "dni_enc", "apellidos", "nombre",
    ]:
        op.drop_column("user", col)
