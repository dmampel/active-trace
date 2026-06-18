"""010_analisis_permiso

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
Create Date: 2026-06-17 00:00:00.000000

Agrega permisos para el módulo de análisis de atrasados (C-11):
- atrasados:ver → TUTOR, PROFESOR, COORDINADOR, ADMIN

Sin migraciones de tablas — C-11 solo lee datos existentes.
"""

from typing import Sequence, Union
import uuid
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

revision: str = "c2d3e4f5a6b7"
down_revision: Union[str, None] = "b1c2d3e4f5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    connection = op.get_bind()
    now = datetime.now(timezone.utc)

    # Insertar permiso atrasados:ver
    permiso_id = uuid.uuid4()
    connection.execute(
        sa.text(
            "INSERT INTO permiso (id, nombre, descripcion, created_at, updated_at) "
            "VALUES (:id, :nombre, :descripcion, :created_at, :updated_at)"
        ),
        {
            "id": permiso_id,
            "nombre": "atrasados:ver",
            "descripcion": "Ver análisis de alumnos atrasados, ranking, reportes y monitor",
            "created_at": now,
            "updated_at": now,
        },
    )

    # Asignar a roles: TUTOR, PROFESOR, COORDINADOR, ADMIN
    roles_con_permiso = ["TUTOR", "PROFESOR", "COORDINADOR", "ADMIN"]
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
        sa.text("DELETE FROM permiso WHERE nombre = :nombre"),
        {"nombre": "atrasados:ver"},
    )
