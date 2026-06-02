import uuid
from datetime import date, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models.base import Base
from app.models.rbac import Permiso, Rol, RolPermiso, UserRol
from app.models.tenant import Tenant
from app.models.user import User
from app.repositories.rbac_repository import RbacRepository

@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

@pytest.fixture
def tenant(session):
    t = Tenant(name="Test Tenant")
    session.add(t)
    session.commit()
    return t

@pytest.fixture
def user(session, tenant):
    u = User(tenant_id=tenant.id, email="u@example.com", password_hash="hash")
    session.add(u)
    session.commit()
    return u

def test_user_with_no_roles_has_no_permissions(session, user, tenant):
    perms = RbacRepository.get_effective_permissions(session, user.id, tenant.id)
    assert perms == set()
    roles = RbacRepository.get_user_roles(session, user.id, tenant.id)
    assert roles == []

def test_admin_role_has_estructura_gestionar(session, user, tenant):
    rol = Rol(nombre="ADMIN")
    perm = Permiso(nombre="estructura:gestionar")
    session.add(rol)
    session.add(perm)
    session.flush()

    session.add(RolPermiso(rol_id=rol.id, permiso_id=perm.id))
    session.add(UserRol(
        user_id=user.id, 
        rol_id=rol.id, 
        tenant_id=tenant.id, 
        desde=date.today() - timedelta(days=1)
    ))
    session.commit()

    perms = RbacRepository.get_effective_permissions(session, user.id, tenant.id)
    assert "estructura:gestionar" in perms

def test_role_union_merges_permissions(session, user, tenant):
    r1 = Rol(nombre="R1")
    r2 = Rol(nombre="R2")
    p1 = Permiso(nombre="p1")
    p2 = Permiso(nombre="p2")
    session.add_all([r1, r2, p1, p2])
    session.flush()

    session.add(RolPermiso(rol_id=r1.id, permiso_id=p1.id))
    session.add(RolPermiso(rol_id=r2.id, permiso_id=p2.id))
    session.add(UserRol(user_id=user.id, rol_id=r1.id, tenant_id=tenant.id, desde=date.today()))
    session.add(UserRol(user_id=user.id, rol_id=r2.id, tenant_id=tenant.id, desde=date.today()))
    session.commit()

    perms = RbacRepository.get_effective_permissions(session, user.id, tenant.id)
    assert perms == {"p1", "p2"}
    
    roles = RbacRepository.get_user_roles(session, user.id, tenant.id)
    assert set(roles) == {"R1", "R2"}

def test_expired_role_not_included(session, user, tenant):
    r = Rol(nombre="R1")
    p = Permiso(nombre="p1")
    session.add_all([r, p])
    session.flush()
    session.add(RolPermiso(rol_id=r.id, permiso_id=p.id))
    
    # Expired 2 days ago
    hasta = date.today() - timedelta(days=2)
    session.add(UserRol(user_id=user.id, rol_id=r.id, tenant_id=tenant.id, desde=date(2020,1,1), hasta=hasta))
    session.commit()

    perms = RbacRepository.get_effective_permissions(session, user.id, tenant.id)
    assert perms == set()
    roles = RbacRepository.get_user_roles(session, user.id, tenant.id)
    assert roles == []

def test_future_role_not_included(session, user, tenant):
    r = Rol(nombre="R1")
    p = Permiso(nombre="p1")
    session.add_all([r, p])
    session.flush()
    session.add(RolPermiso(rol_id=r.id, permiso_id=p.id))
    
    # Starts in 2 days
    desde = date.today() + timedelta(days=2)
    session.add(UserRol(user_id=user.id, rol_id=r.id, tenant_id=tenant.id, desde=desde))
    session.commit()

    perms = RbacRepository.get_effective_permissions(session, user.id, tenant.id)
    assert perms == set()

def test_wrong_tenant_not_included(session, user, tenant):
    other_tenant = Tenant(name="Other")
    session.add(other_tenant)
    r = Rol(nombre="R1")
    p = Permiso(nombre="p1")
    session.add_all([r, p])
    session.flush()
    session.add(RolPermiso(rol_id=r.id, permiso_id=p.id))
    
    # User is in this tenant but the role assignment is linked to other tenant
    # Wait, the UserRol has tenant_id. We'll set it to other_tenant.id.
    session.add(UserRol(user_id=user.id, rol_id=r.id, tenant_id=other_tenant.id, desde=date.today()))
    session.commit()

    perms = RbacRepository.get_effective_permissions(session, user.id, tenant.id)
    assert perms == set()
