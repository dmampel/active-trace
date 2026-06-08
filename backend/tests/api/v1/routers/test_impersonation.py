"""Tests para endpoints de impersonación."""
import uuid
from datetime import timedelta, date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.models.rbac import Permiso, Rol, RolPermiso, UserRol
from app.models.tenant import Tenant
from app.models.user import User
from app.core.dependencies import CurrentUser
from app.core.security import create_access_token, hash_password, decode_token


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _create_tenant(db: AsyncSession, name: str = None) -> Tenant:
    t = Tenant(name=name or f"T-{uuid.uuid4().hex[:6]}")
    db.add(t)
    await db.commit()
    await db.refresh(t)
    return t


async def _create_user(db: AsyncSession, tenant_id: uuid.UUID, email: str = None) -> User:
    u = User(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        email=email or f"u-{uuid.uuid4().hex[:6]}@test.com",
        password_hash=hash_password("secret123"),
        is_active=True,
    )
    db.add(u)
    await db.commit()
    await db.refresh(u)
    return u


async def _grant_permission(db: AsyncSession, user_id: uuid.UUID, tenant_id: uuid.UUID, perm_name: str = "impersonacion:usar"):
    from sqlalchemy import select as sa_select
    result = await db.execute(sa_select(Permiso).where(Permiso.nombre == perm_name))
    perm = result.scalar_one_or_none()
    if perm is None:
        perm = Permiso(id=uuid.uuid4(), nombre=perm_name)
        db.add(perm)
        await db.flush()

    rol = Rol(id=uuid.uuid4(), nombre=f"rol-{uuid.uuid4().hex[:4]}")
    db.add(rol)
    await db.flush()

    db.add_all([RolPermiso(rol_id=rol.id, permiso_id=perm.id), UserRol(user_id=user_id, rol_id=rol.id, tenant_id=tenant_id, desde=date.today())])
    await db.commit()


def _token_for(user: User, extra_claims: dict = None) -> str:
    claims = {"sub": str(user.id), "tenant_id": str(user.tenant_id), "roles": []}
    if extra_claims:
        claims.update(extra_claims)
    return create_access_token(claims, timedelta(minutes=15))


# ── get_current_user — impersonado_id (no DB needed) ─────────────────────────

def test_get_current_user_with_impersonado_id():
    target_id = uuid.uuid4()
    user_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    token = create_access_token(
        {"sub": str(user_id), "tenant_id": str(tenant_id), "roles": [], "impersonado_id": str(target_id)},
        timedelta(minutes=15),
    )
    claims = decode_token(token)
    impersonado = uuid.UUID(claims["impersonado_id"])
    cu = CurrentUser(id=uuid.UUID(claims["sub"]), tenant_id=uuid.UUID(claims["tenant_id"]), roles=[], impersonado_id=impersonado)
    assert cu.impersonado_id == target_id


def test_get_current_user_without_impersonado_id():
    user_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    token = create_access_token({"sub": str(user_id), "tenant_id": str(tenant_id), "roles": []}, timedelta(minutes=15))
    claims = decode_token(token)
    cu = CurrentUser(id=uuid.UUID(claims["sub"]), tenant_id=uuid.UUID(claims["tenant_id"]), roles=[], impersonado_id=None)
    assert cu.impersonado_id is None


# ── POST /impersonate ─────────────────────────────────────────────────────────

async def test_impersonate_without_permission_returns_403(app_client, db_session: AsyncSession):
    tenant = await _create_tenant(db_session)
    actor = await _create_user(db_session, tenant.id)
    target = await _create_user(db_session, tenant.id)
    token = _token_for(actor)

    resp = await app_client.post(
        "/api/v1/auth/impersonate",
        json={"target_user_id": str(target.id)},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


async def test_impersonate_cross_tenant_returns_404(app_client, db_session: AsyncSession):
    tenant_a = await _create_tenant(db_session)
    tenant_b = await _create_tenant(db_session)
    actor = await _create_user(db_session, tenant_a.id)
    await _grant_permission(db_session, actor.id, tenant_a.id)
    cross_target = await _create_user(db_session, tenant_b.id)
    token = _token_for(actor)

    resp = await app_client.post(
        "/api/v1/auth/impersonate",
        json={"target_user_id": str(cross_target.id)},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


async def test_impersonate_success(app_client, db_session: AsyncSession):
    tenant = await _create_tenant(db_session)
    actor = await _create_user(db_session, tenant.id)
    await _grant_permission(db_session, actor.id, tenant.id)
    target = await _create_user(db_session, tenant.id)
    token = _token_for(actor)

    resp = await app_client.post(
        "/api/v1/auth/impersonate",
        json={"target_user_id": str(target.id)},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "impersonate_token" in data
    assert data["token_type"] == "bearer"

    result = await db_session.execute(select(AuditLog).where(AuditLog.actor_id == actor.id))
    entry = result.scalar_one_or_none()
    assert entry is not None
    assert entry.accion == "IMPERSONACION_INICIAR"


async def test_impersonate_token_has_impersonado_id(app_client, db_session: AsyncSession):
    tenant = await _create_tenant(db_session)
    actor = await _create_user(db_session, tenant.id)
    await _grant_permission(db_session, actor.id, tenant.id)
    target = await _create_user(db_session, tenant.id)
    token = _token_for(actor)

    resp = await app_client.post(
        "/api/v1/auth/impersonate",
        json={"target_user_id": str(target.id)},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    imp_token = resp.json()["impersonate_token"]
    claims = decode_token(imp_token)
    assert claims["impersonado_id"] == str(target.id)
    assert claims["sub"] == str(actor.id)


async def test_impersonate_nested_rejected(app_client, db_session: AsyncSession):
    tenant = await _create_tenant(db_session)
    actor = await _create_user(db_session, tenant.id)
    await _grant_permission(db_session, actor.id, tenant.id)
    target = await _create_user(db_session, tenant.id)
    target2 = await _create_user(db_session, tenant.id)

    imp_token = _token_for(actor, {"impersonado_id": str(target.id)})

    resp = await app_client.post(
        "/api/v1/auth/impersonate",
        json={"target_user_id": str(target2.id)},
        headers={"Authorization": f"Bearer {imp_token}"},
    )
    assert resp.status_code == 400
    assert "impersonación activa" in resp.json()["detail"]


# ── POST /impersonate/end ─────────────────────────────────────────────────────

async def test_end_impersonation_without_active_session(app_client, db_session: AsyncSession):
    tenant = await _create_tenant(db_session)
    actor = await _create_user(db_session, tenant.id)
    token = _token_for(actor)

    resp = await app_client.post(
        "/api/v1/auth/impersonate/end",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400
    assert "impersonación activa" in resp.json()["detail"]


async def test_end_impersonation_success(app_client, db_session: AsyncSession):
    tenant = await _create_tenant(db_session)
    actor = await _create_user(db_session, tenant.id)
    target = await _create_user(db_session, tenant.id)
    imp_token = _token_for(actor, {"impersonado_id": str(target.id)})

    resp = await app_client.post(
        "/api/v1/auth/impersonate/end",
        headers={"Authorization": f"Bearer {imp_token}"},
    )
    assert resp.status_code == 200

    result = await db_session.execute(
        select(AuditLog).where(AuditLog.actor_id == actor.id, AuditLog.accion == "IMPERSONACION_FINALIZAR")
    )
    entry = result.scalar_one_or_none()
    assert entry is not None
    assert entry.impersonado_id == target.id
