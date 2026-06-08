import uuid
from datetime import date, timedelta

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rbac import Permiso, Rol, RolPermiso, UserRol
from app.models.tenant import Tenant
from app.models.user import User
from app.repositories.rbac_repository import RbacRepository


@pytest_asyncio.fixture
async def tenant(db_session: AsyncSession):
    t = Tenant(name=f"RBAC-Tenant-{uuid.uuid4().hex[:6]}")
    db_session.add(t)
    await db_session.commit()
    await db_session.refresh(t)
    return t


@pytest_asyncio.fixture
async def user(db_session: AsyncSession, tenant):
    u = User(tenant_id=tenant.id, email=f"u-{uuid.uuid4().hex[:6]}@example.com", password_hash="hash")
    db_session.add(u)
    await db_session.commit()
    await db_session.refresh(u)
    return u


async def test_user_with_no_roles_has_no_permissions(db_session: AsyncSession, user, tenant):
    perms = await RbacRepository.get_effective_permissions(db_session, user.id, tenant.id)
    assert perms == set()
    roles = await RbacRepository.get_user_roles(db_session, user.id, tenant.id)
    assert roles == []


async def test_admin_role_has_estructura_gestionar(db_session: AsyncSession, user, tenant):
    rol = Rol(nombre=f"ADMIN-{uuid.uuid4().hex[:4]}")
    perm = Permiso(nombre=f"estructura:gestionar-{uuid.uuid4().hex[:4]}")
    db_session.add(rol)
    db_session.add(perm)
    await db_session.flush()

    db_session.add(RolPermiso(rol_id=rol.id, permiso_id=perm.id))
    db_session.add(UserRol(
        user_id=user.id,
        rol_id=rol.id,
        tenant_id=tenant.id,
        desde=date.today() - timedelta(days=1),
    ))
    await db_session.commit()

    perms = await RbacRepository.get_effective_permissions(db_session, user.id, tenant.id)
    assert perm.nombre in perms


async def test_role_union_merges_permissions(db_session: AsyncSession, user, tenant):
    suffix = uuid.uuid4().hex[:4]
    r1 = Rol(nombre=f"R1-{suffix}")
    r2 = Rol(nombre=f"R2-{suffix}")
    p1 = Permiso(nombre=f"p1-{suffix}")
    p2 = Permiso(nombre=f"p2-{suffix}")
    db_session.add_all([r1, r2, p1, p2])
    await db_session.flush()

    db_session.add(RolPermiso(rol_id=r1.id, permiso_id=p1.id))
    db_session.add(RolPermiso(rol_id=r2.id, permiso_id=p2.id))
    db_session.add(UserRol(user_id=user.id, rol_id=r1.id, tenant_id=tenant.id, desde=date.today()))
    db_session.add(UserRol(user_id=user.id, rol_id=r2.id, tenant_id=tenant.id, desde=date.today()))
    await db_session.commit()

    perms = await RbacRepository.get_effective_permissions(db_session, user.id, tenant.id)
    assert p1.nombre in perms
    assert p2.nombre in perms

    roles = await RbacRepository.get_user_roles(db_session, user.id, tenant.id)
    assert set(roles) >= {r1.nombre, r2.nombre}


async def test_expired_role_not_included(db_session: AsyncSession, user, tenant):
    suffix = uuid.uuid4().hex[:4]
    r = Rol(nombre=f"R-exp-{suffix}")
    p = Permiso(nombre=f"p-exp-{suffix}")
    db_session.add_all([r, p])
    await db_session.flush()
    db_session.add(RolPermiso(rol_id=r.id, permiso_id=p.id))

    hasta = date.today() - timedelta(days=2)
    db_session.add(UserRol(user_id=user.id, rol_id=r.id, tenant_id=tenant.id, desde=date(2020, 1, 1), hasta=hasta))
    await db_session.commit()

    perms = await RbacRepository.get_effective_permissions(db_session, user.id, tenant.id)
    assert p.nombre not in perms
    roles = await RbacRepository.get_user_roles(db_session, user.id, tenant.id)
    assert r.nombre not in roles


async def test_future_role_not_included(db_session: AsyncSession, user, tenant):
    suffix = uuid.uuid4().hex[:4]
    r = Rol(nombre=f"R-fut-{suffix}")
    p = Permiso(nombre=f"p-fut-{suffix}")
    db_session.add_all([r, p])
    await db_session.flush()
    db_session.add(RolPermiso(rol_id=r.id, permiso_id=p.id))

    desde = date.today() + timedelta(days=2)
    db_session.add(UserRol(user_id=user.id, rol_id=r.id, tenant_id=tenant.id, desde=desde))
    await db_session.commit()

    perms = await RbacRepository.get_effective_permissions(db_session, user.id, tenant.id)
    assert p.nombre not in perms


async def test_wrong_tenant_not_included(db_session: AsyncSession, user, tenant):
    other_tenant = Tenant(name=f"Other-{uuid.uuid4().hex[:6]}")
    db_session.add(other_tenant)
    suffix = uuid.uuid4().hex[:4]
    r = Rol(nombre=f"R-ot-{suffix}")
    p = Permiso(nombre=f"p-ot-{suffix}")
    db_session.add_all([r, p])
    await db_session.flush()
    db_session.add(RolPermiso(rol_id=r.id, permiso_id=p.id))

    db_session.add(UserRol(user_id=user.id, rol_id=r.id, tenant_id=other_tenant.id, desde=date.today()))
    await db_session.commit()

    perms = await RbacRepository.get_effective_permissions(db_session, user.id, tenant.id)
    assert p.nombre not in perms
