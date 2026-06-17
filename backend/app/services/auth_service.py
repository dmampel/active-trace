import base64
import io
import uuid
from datetime import datetime, timedelta, timezone

import pyotp
import qrcode
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import IMPERSONACION_FINALIZAR, IMPERSONACION_INICIAR, record_audit
from app.core.config import get_settings
from app.core.security import (
    AES256GCMCipher,
    InvalidTokenError,
    create_access_token,
    create_impersonation_token,
    create_partial_token,
    decode_token,
    derive_encryption_key,
    generate_opaque_token,
    hash_opaque_token,
    hash_password,
    verify_password,
)
from app.repositories.user_repository import UserRepository
from app.repositories.rbac_repository import RbacRepository
from app.schemas.auth import PartialTokenResponse, TokenResponse


class AuthError(Exception):
    pass


ROLE_HIERARCHY: dict[str, int] = {
    "TUTOR": 1,
    "PROFESOR": 2,
    "NEXO": 3,
    "FINANZAS": 4,
    "COORDINADOR": 5,
    "ADMIN": 6,
}


def _max_role_level(roles: list[str]) -> int:
    return max((ROLE_HIERARCHY.get(r, 0) for r in roles), default=0)


def _build_cipher() -> AES256GCMCipher:
    return AES256GCMCipher(derive_encryption_key(get_settings().encryption_key))


_cipher = _build_cipher()


async def _build_token_response(session: AsyncSession, user, roles: list[str]) -> TokenResponse:
    access = create_access_token(
        {"sub": str(user.id), "tenant_id": str(user.tenant_id), "roles": roles},
        timedelta(minutes=get_settings().access_token_expire_minutes),
    )
    raw_refresh = generate_opaque_token()
    family_id = uuid.uuid4()
    expires_at = datetime.now(timezone.utc) + timedelta(days=get_settings().refresh_token_expire_days)
    await UserRepository.create_refresh_token(
        session, user.id, user.tenant_id, hash_opaque_token(raw_refresh), family_id, expires_at
    )
    return TokenResponse(access_token=access, refresh_token=raw_refresh)


class AuthService:

    @staticmethod
    async def login(session: AsyncSession, tenant_id: uuid.UUID, email: str, password: str):
        user = await UserRepository.get_by_email(session, tenant_id, email.lower())
        if not user or not user.is_active:
            raise AuthError("Invalid credentials")
        if not verify_password(password, user.password_hash):
            raise AuthError("Invalid credentials")

        if user.totp_enabled:
            return PartialTokenResponse(
                partial_token=create_partial_token(str(user.id), str(user.tenant_id))
            )

        roles = await RbacRepository.get_user_roles(session, user.id, user.tenant_id)
        return await _build_token_response(session, user, roles)

    @staticmethod
    async def refresh(session: AsyncSession, tenant_id: uuid.UUID, refresh_token_str: str) -> TokenResponse:
        token_hash = hash_opaque_token(refresh_token_str)
        rt = await UserRepository.get_refresh_token_by_hash(session, token_hash, tenant_id)

        if rt is None:
            raise AuthError("Invalid refresh token")

        if rt.revoked_at is not None:
            await UserRepository.revoke_refresh_family(session, rt.family_id)
            raise AuthError("Token reuse detected")

        expires_at = rt.expires_at if rt.expires_at.tzinfo else rt.expires_at.replace(tzinfo=timezone.utc)
        if expires_at < datetime.now(timezone.utc):
            raise AuthError("Refresh token expired")

        if str(rt.tenant_id) != str(tenant_id):
            raise AuthError("Invalid refresh token")

        rt.revoked_at = datetime.now(timezone.utc)

        user = await UserRepository.get_by_id(session, tenant_id, rt.user_id)
        if not user or not user.is_active:
            raise AuthError("User not found or inactive")

        roles = await RbacRepository.get_user_roles(session, user.id, user.tenant_id)
        access = create_access_token(
            {"sub": str(user.id), "tenant_id": str(user.tenant_id), "roles": roles},
            timedelta(minutes=get_settings().access_token_expire_minutes),
        )
        raw_refresh = generate_opaque_token()
        new_expires = datetime.now(timezone.utc) + timedelta(days=get_settings().refresh_token_expire_days)
        await UserRepository.create_refresh_token(
            session, user.id, user.tenant_id, hash_opaque_token(raw_refresh), rt.family_id, new_expires
        )
        return TokenResponse(access_token=access, refresh_token=raw_refresh)

    @staticmethod
    async def logout(session: AsyncSession, tenant_id: uuid.UUID, refresh_token_str: str) -> None:
        token_hash = hash_opaque_token(refresh_token_str)
        rt = await UserRepository.get_refresh_token_by_hash(session, token_hash, tenant_id)
        if rt and rt.revoked_at is None and rt.tenant_id == tenant_id:
            rt.revoked_at = datetime.now(timezone.utc)

    @staticmethod
    async def totp_enroll(session: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID) -> dict:
        user = await UserRepository.get_by_id(session, tenant_id, user_id)
        if not user:
            raise AuthError("User not found")

        secret = pyotp.random_base32()
        user.totp_pending_secret_enc = _cipher.encrypt(secret)

        uri = pyotp.totp.TOTP(secret).provisioning_uri(name=user.email, issuer_name="activia-trace")
        qr = qrcode.make(uri)
        buf = io.BytesIO()
        qr.save(buf)
        buf.seek(0)
        qr_b64 = base64.b64encode(buf.getvalue()).decode()
        return {"otpauth_uri": uri, "qr_base64": qr_b64}

    @staticmethod
    async def totp_confirm_enroll(session: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID, code: str) -> bool:
        user = await UserRepository.get_by_id(session, tenant_id, user_id)
        if not user or not user.totp_pending_secret_enc:
            raise AuthError("No pending TOTP enrollment")

        secret = _cipher.decrypt(user.totp_pending_secret_enc)
        totp = pyotp.TOTP(secret)
        if not totp.verify(code):
            raise AuthError("Invalid TOTP code")

        user.totp_secret_enc = user.totp_pending_secret_enc
        user.totp_pending_secret_enc = None
        user.totp_enabled = True
        return True

    @staticmethod
    async def totp_verify_gate(session: AsyncSession, tenant_id: uuid.UUID, partial_token_str: str, code: str) -> TokenResponse:
        try:
            claims = decode_token(partial_token_str)
        except InvalidTokenError as exc:
            raise AuthError("Invalid partial token") from exc

        if claims.get("scope") != "2fa_pending":
            raise AuthError("Invalid token scope")

        if str(claims.get("tenant_id")) != str(tenant_id):
            raise AuthError("Tenant mismatch")

        user_id = uuid.UUID(claims["sub"])
        user = await UserRepository.get_by_id(session, tenant_id, user_id)
        if not user or not user.totp_enabled or not user.totp_secret_enc:
            raise AuthError("2FA not configured")

        secret = _cipher.decrypt(user.totp_secret_enc)
        if not pyotp.TOTP(secret).verify(code):
            raise AuthError("Invalid TOTP code")

        roles = await RbacRepository.get_user_roles(session, user.id, user.tenant_id)
        return await _build_token_response(session, user, roles)

    @staticmethod
    async def forgot_password(session: AsyncSession, tenant_id: uuid.UUID, email: str) -> str | None:
        user = await UserRepository.get_by_email(session, tenant_id, email.lower())
        if not user:
            return None

        raw = generate_opaque_token()
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)
        await UserRepository.create_reset_token(session, user.id, tenant_id, hash_opaque_token(raw), expires_at)
        return raw

    @staticmethod
    async def impersonate(
        session: AsyncSession,
        current_user,
        target_user_id: uuid.UUID,
        request=None,
    ) -> str:
        if current_user.impersonado_id is not None:
            raise AuthError("No se puede impersonar desde una sesión de impersonación activa")

        target = await UserRepository.get_by_id(session, current_user.tenant_id, target_user_id)
        if not target or not target.is_active:
            raise AuthError("Target user not found")

        target_roles = await RbacRepository.get_user_roles(session, target.id, current_user.tenant_id)
        if _max_role_level(target_roles) > _max_role_level(current_user.roles):
            raise AuthError("No se puede impersonar a un usuario con mayor nivel de privilegio")

        token, _jti = create_impersonation_token(
            {
                "sub": str(current_user.id),
                "tenant_id": str(current_user.tenant_id),
                "roles": current_user.roles,
                "impersonado_id": str(target.id),
            },
            timedelta(minutes=get_settings().impersonation_token_expire_minutes),
        )

        await record_audit(
            session,
            current_user,
            IMPERSONACION_INICIAR,
            request=request,
            detail={"target_user_id": str(target.id)},
        )
        return token

    @staticmethod
    async def end_impersonation(session: AsyncSession, current_user, request=None) -> None:
        if current_user.impersonado_id is None:
            raise AuthError("No hay sesión de impersonación activa")

        if current_user.jti:
            from app.core.redis_client import revoke_jti
            ttl = get_settings().impersonation_token_expire_minutes * 60
            await revoke_jti(current_user.jti, ttl_seconds=ttl)

        await record_audit(
            session,
            current_user,
            IMPERSONACION_FINALIZAR,
            request=request,
            detail={"target_user_id": str(current_user.impersonado_id)},
        )

    @staticmethod
    async def reset_password(session: AsyncSession, tenant_id: uuid.UUID, token_str: str, new_password: str) -> None:
        token_hash = hash_opaque_token(token_str)
        prt = await UserRepository.get_reset_token_by_hash(session, token_hash, tenant_id)

        if prt is None or prt.used_at is not None:
            raise AuthError("Invalid or already used reset token")

        prt_expires_at = prt.expires_at if prt.expires_at.tzinfo else prt.expires_at.replace(tzinfo=timezone.utc)
        if prt_expires_at < datetime.now(timezone.utc):
            raise AuthError("Reset token expired")

        if str(prt.tenant_id) != str(tenant_id):
            raise AuthError("Invalid reset token")

        user = await UserRepository.get_by_id(session, tenant_id, prt.user_id)
        if not user:
            raise AuthError("User not found")

        user.password_hash = hash_password(new_password)
        await UserRepository.mark_reset_token_used(session, prt.id)
