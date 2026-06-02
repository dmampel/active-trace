import uuid
from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models.base import Base
# These imports will fail initially because the modules don't exist yet!
from app.models.rbac import Rol, Permiso, RolPermiso, UserRol
from app.models.tenant import Tenant
from app.models.user import User

@pytest.fixture
def memory_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

def test_rbac_models_instantiation(memory_session):
    # Setup dependencies
    tenant = Tenant(name="Test Tenant")
    memory_session.add(tenant)
    memory_session.flush()

    user = User(tenant_id=tenant.id, email="u@example.com", password_hash="hash")
    memory_session.add(user)
    
    rol = Rol(nombre="ADMIN", descripcion="Administrator")
    memory_session.add(rol)

    permiso = Permiso(nombre="modulo:accion", descripcion="Test permission")
    memory_session.add(permiso)
    memory_session.flush()

    rol_permiso = RolPermiso(rol_id=rol.id, permiso_id=permiso.id)
    memory_session.add(rol_permiso)
    
    # UserRol requires desde DATE NOT NULL, hasta DATE NULLABLE
    user_rol = UserRol(
        user_id=user.id, 
        tenant_id=tenant.id, 
        rol_id=rol.id, 
        desde=date(2024, 1, 1),
        hasta=None
    )
    memory_session.add(user_rol)
    memory_session.commit()

    # Verification
    assert user_rol.id is not None
    assert user_rol.desde == date(2024, 1, 1)
    assert user_rol.hasta is None
