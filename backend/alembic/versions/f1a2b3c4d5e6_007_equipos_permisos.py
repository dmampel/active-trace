"""007_equipos_permisos

Revision ID: f1a2b3c4d5e6
Revises: e1f2a3b4c5d6
Create Date: 2026-06-11 00:00:00.000000

Agrega permisos del módulo equipos-docentes (C-08):
- equipos:read_own  → PROFESOR, TUTOR, NEXO, COORDINADOR
- equipos:manage    → COORDINADOR, ADMIN
- equipos:export    → COORDINADOR, ADMIN
"""
from typing import Sequence, Union
import uuid
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, None] = "e1f2a3b4c5d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    now = datetime.now(timezone.utc)
    connection = op.get_bind()

    nuevos_permisos = [
        ("equipos:read_own", "Ver las propias asignaciones docentes del usuario autenticado"),
        ("equipos:manage", "Asignación masiva, clonar equipos y modificar vigencias"),
        ("equipos:export", "Exportar el plantel docente completo del tenant en CSV"),
    ]
    for nombre, descripcion in nuevos_permisos:
        connection.execute(
            sa.text(
                "INSERT INTO permiso (id, nombre, descripcion, created_at, updated_at) "
                "VALUES (:id, :nombre, :descripcion, :created_at, :updated_at) "
                "ON CONFLICT (nombre) DO NOTHING"
            ),
            {
                "id": uuid.uuid4(),
                "nombre": nombre,
                "descripcion": descripcion,
                "created_at": now,
                "updated_at": now,
            },
        )

    # Asignar permisos a roles
    matriz = {
        "PROFESOR":    ["equipos:read_own"],
        "TUTOR":       ["equipos:read_own"],
        "NEXO":        ["equipos:read_own"],
        "COORDINADOR": ["equipos:read_own", "equipos:manage", "equipos:export"],
        "ADMIN":       ["equipos:manage", "equipos:export"],
    }
    rol_rows = connection.execute(sa.text("SELECT id, nombre FROM rol")).fetchall()
    permiso_rows = connection.execute(
        sa.text(
            "SELECT id, nombre FROM permiso WHERE nombre IN "
            "('equipos:read_own','equipos:manage','equipos:export')"
        )
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
                {
                    "id": uuid.uuid4(),
                    "rol_id": rol_id,
                    "permiso_id": p_id,
                    "created_at": now,
                    "updated_at": now,
                },
            )


def downgrade() -> None:
    connection = op.get_bind()
    for nombre in ["equipos:read_own", "equipos:manage", "equipos:export"]:
        connection.execute(
            sa.text("DELETE FROM permiso WHERE nombre = :nombre"), {"nombre": nombre}
        )
