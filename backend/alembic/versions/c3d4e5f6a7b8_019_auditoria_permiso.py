"""019_auditoria_permiso

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-06-19 00:00:00.000000

Agrega permisos para el panel de auditoría y métricas (C-19):
- auditoria:ver → ADMIN, COORDINADOR, FINANZAS

Sin migraciones de tablas — C-19 solo lee datos existentes (AuditLog y Comunicacion).
"""

from typing import Sequence, Union
import uuid
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    connection = op.get_bind()
    now = datetime.now(timezone.utc)

    # Insertar permiso auditoria:ver
    permiso_id = uuid.uuid4()
    connection.execute(
        sa.text(
            "INSERT INTO permiso (id, nombre, descripcion, created_at, updated_at) "
            "VALUES (:id, :nombre, :descripcion, :created_at, :updated_at)"
        ),
        {
            "id": permiso_id,
            "nombre": "auditoria:ver",
            "descripcion": "Ver panel de auditoría: log completo, acciones por día, "
            "estado de comunicaciones por docente e interacciones por materia",
            "created_at": now,
            "updated_at": now,
        },
    )

    # Asignar a roles: ADMIN, COORDINADOR, FINANZAS
    roles_con_permiso = ["ADMIN", "COORDINADOR", "FINANZAS"]
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
        {"nombre": "auditoria:ver"},
    )
