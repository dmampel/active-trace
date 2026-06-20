"""003_rbac_tables

Revision ID: a1b2c3d4e5f6
Revises: 2f9d509b868a
Create Date: 2024-06-02 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '2f9d509b868a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Crear tablas
    rol_table = op.create_table('rol',
        sa.Column('nombre', sa.String(length=50), nullable=False),
        sa.Column('descripcion', sa.String(length=255), nullable=True),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('nombre')
    )
    
    permiso_table = op.create_table('permiso',
        sa.Column('nombre', sa.String(length=100), nullable=False),
        sa.Column('descripcion', sa.String(length=255), nullable=True),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('nombre')
    )
    
    rol_permiso_table = op.create_table('rol_permiso',
        sa.Column('rol_id', sa.UUID(), nullable=False),
        sa.Column('permiso_id', sa.UUID(), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['permiso_id'], ['permiso.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['rol_id'], ['rol.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('rol_id', 'permiso_id', name='uq_rol_permiso')
    )
    op.create_index(op.f('ix_rol_permiso_permiso_id'), 'rol_permiso', ['permiso_id'], unique=False)
    op.create_index(op.f('ix_rol_permiso_rol_id'), 'rol_permiso', ['rol_id'], unique=False)
    
    user_rol_table = op.create_table('user_rol',
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('rol_id', sa.UUID(), nullable=False),
        sa.Column('desde', sa.Date(), nullable=False),
        sa.Column('hasta', sa.Date(), nullable=True),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(['rol_id'], ['rol.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_rol_rol_id'), 'user_rol', ['rol_id'], unique=False)
    op.create_index(op.f('ix_user_rol_tenant_id'), 'user_rol', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_user_rol_user_id'), 'user_rol', ['user_id'], unique=False)

    # 2. Seed de roles
    roles = ["ALUMNO", "TUTOR", "PROFESOR", "COORDINADOR", "NEXO", "ADMIN", "FINANZAS"]
    rol_data = []
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    for r in roles:
        rol_data.append({"id": uuid.uuid4(), "nombre": r, "descripcion": f"Rol de {r}", "created_at": now, "updated_at": now})
    
    op.bulk_insert(rol_table, rol_data)

    # Se removió el seed de permisos y rol_permiso para evitar duplicados.
    # Los permisos se insertan en cada migración correspondiente.


def downgrade() -> None:
    op.drop_index(op.f('ix_user_rol_user_id'), table_name='user_rol')
    op.drop_index(op.f('ix_user_rol_tenant_id'), table_name='user_rol')
    op.drop_index(op.f('ix_user_rol_rol_id'), table_name='user_rol')
    op.drop_table('user_rol')
    op.drop_index(op.f('ix_rol_permiso_rol_id'), table_name='rol_permiso')
    op.drop_index(op.f('ix_rol_permiso_permiso_id'), table_name='rol_permiso')
    op.drop_table('rol_permiso')
    op.drop_table('permiso')
    op.drop_table('rol')
