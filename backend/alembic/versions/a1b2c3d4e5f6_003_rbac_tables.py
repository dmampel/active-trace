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

    # 3. Seed de permisos
    permisos = [
        "estado_academico:ver_propio",
        "evaluacion:reservar",
        "avisos:confirmar",
        "calificaciones:importar",
        "calificaciones:importar_propio",
        "atrasados:ver",
        "atrasados:ver_propio",
        "entregas:detectar",
        "entregas:detectar_propio",
        "comunicacion:enviar",
        "comunicacion:enviar_propio",
        "comunicacion:aprobar",
        "encuentros:gestionar",
        "encuentros:gestionar_propio",
        "guardias:registrar",
        "guardias:registrar_propio",
        "tareas:gestionar",
        "tareas:gestionar_propio",
        "avisos:publicar",
        "equipos:gestionar",
        "estructura:gestionar",
        "usuarios:gestionar",
        "auditoria:ver",
        "auditoria:ver_propio",
        "grilla_salarial:operar",
        "liquidaciones:gestionar",
        "facturas:gestionar",
        "tenant:configurar"
    ]
    permiso_data = []
    for p in permisos:
        permiso_data.append({"id": uuid.uuid4(), "nombre": p, "descripcion": f"Permiso {p}", "created_at": now, "updated_at": now})
    op.bulk_insert(permiso_table, permiso_data)

    # 4. Asociaciones rol_permiso (mapeo)
    matriz = {
        "ALUMNO": ["estado_academico:ver_propio", "evaluacion:reservar", "avisos:confirmar"],
        "TUTOR": ["avisos:confirmar", "atrasados:ver", "entregas:detectar", "encuentros:gestionar", "guardias:registrar_propio"],
        "PROFESOR": ["avisos:confirmar", "calificaciones:importar_propio", "atrasados:ver_propio", "entregas:detectar_propio", "comunicacion:enviar_propio", "encuentros:gestionar_propio", "guardias:registrar_propio", "tareas:gestionar_propio"],
        "COORDINADOR": ["avisos:confirmar", "calificaciones:importar", "atrasados:ver", "entregas:detectar", "comunicacion:enviar", "comunicacion:aprobar", "encuentros:gestionar", "guardias:registrar", "tareas:gestionar", "avisos:publicar", "equipos:gestionar", "auditoria:ver_propio"],
        "NEXO": [],
        "ADMIN": ["avisos:confirmar", "calificaciones:importar", "atrasados:ver", "entregas:detectar", "comunicacion:enviar", "comunicacion:aprobar", "encuentros:gestionar", "guardias:registrar", "tareas:gestionar", "avisos:publicar", "equipos:gestionar", "estructura:gestionar", "usuarios:gestionar", "auditoria:ver", "tenant:configurar"],
        "FINANZAS": ["avisos:confirmar", "auditoria:ver", "grilla_salarial:operar", "liquidaciones:gestionar", "facturas:gestionar"]
    }
    
    # Needs a db connection to get generated UUIDs
    connection = op.get_bind()
    rol_rows = connection.execute(sa.text("SELECT id, nombre FROM rol")).fetchall()
    permiso_rows = connection.execute(sa.text("SELECT id, nombre FROM permiso")).fetchall()
    
    rol_map = {row[1]: row[0] for row in rol_rows}
    permiso_map = {row[1]: row[0] for row in permiso_rows}
    
    rol_permiso_data = []
    for r, p_list in matriz.items():
        r_id = rol_map.get(r)
        if not r_id: continue
        for p in p_list:
            p_id = permiso_map.get(p)
            if p_id:
                rol_permiso_data.append({"id": uuid.uuid4(), "rol_id": r_id, "permiso_id": p_id, "created_at": now, "updated_at": now})
                
    if rol_permiso_data:
        op.bulk_insert(rol_permiso_table, rol_permiso_data)


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
