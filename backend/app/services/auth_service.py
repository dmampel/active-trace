import base64
import io
import uuid
from datetime import datetime, timedelta, timezone

import pyotp
import qrcode

from app.core.config import Settings
from app.core.security import (
    AES256Cipher,
    InvalidTokenError,
    create_access_token,
    create_partial_token,
    decode_token,
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


_cached_settings = None


def _get_settings() -> Settings:
    global _cached_settings  # noqa: PLW0603
    if _cached_settings is None:
        _cached_settings = Settings()
    return _cached_settings


def _get_cipher() -> AES256Cipher:
    key = base64.urlsafe_b64encode(_get_settings().encryption_key[:32].encode())
    return AES256Cipher(key)


def _build_token_response(session, user, roles: list[str]) -> TokenResponse:
    access = create_access_token(
        {"sub": str(user.id), "tenant_id": str(user.tenant_id), "roles": roles},
        timedelta(minutes=_get_settings().access_token_expire_minutes),
    )
    raw_refresh = generate_opaque_token()
    family_id = uuid.uuid4()
    expires_at = datetime.now(timezone.utc) + timedelta(days=_get_settings().refresh_token_expire_days)
    UserRepository.create_refresh_token(
        session, user.id, user.tenant_id, hash_opaque_token(raw_refresh), family_id, expires_at
    )
    return TokenResponse(access_token=access, refresh_token=raw_refresh)


class AuthService:

    @staticmethod
    def login(session, tenant_id: uuid.UUID, email: str, password: str):
        user = UserRepository.get_by_email(session, tenant_id, email)
        if not user or not user.is_active:
            raise AuthError("Invalid credentials")
        if not verify_password(password, user.password_hash):
            raise AuthError("Invalid credentials")

        if user.totp_enabled:
            return PartialTokenResponse(
                partial_token=create_partial_token(str(user.id), str(user.tenant_id))
            )

        roles = RbacRepository.get_user_roles(session, user.id, user.tenant_id)
        return _build_token_response(session, user, roles)

    @staticmethod
    def refresh(session, tenant_id: uuid.UUID, refresh_token_str: str) -> TokenResponse:
        token_hash = hash_opaque_token(refresh_token_str)
        rt = UserRepository.get_refresh_token_by_hash(session, token_hash)

        if rt is None:
            raise AuthError("Invalid refresh token")

        if rt.revoked_at is not None:
            # Token reuse detected — revoke entire family
            UserRepository.revoke_refresh_family(session, rt.family_id)
            raise AuthError("Token reuse detected")

        if rt.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            raise AuthError("Refresh token expired")

        if str(rt.tenant_id) != str(tenant_id):
            raise AuthError("Invalid refresh token")

        # Rotate: revoke current, issue new pair
        rt.revoked_at = datetime.now(timezone.utc)

        user = UserRepository.get_by_id(session, tenant_id, rt.user_id)
        if not user or not user.is_active:
            raise AuthError("User not found or inactive")

        access = create_access_token(
            {"sub": str(user.id), "tenant_id": str(user.tenant_id), "roles": RbacRepository.get_user_roles(session, user.id, user.tenant_id)},
            timedelta(minutes=_get_settings().access_token_expire_minutes),
        )
        raw_refresh = generate_opaque_token()
        expires_at = datetime.now(timezone.utc) + timedelta(days=_get_settings().refresh_token_expire_days)
        UserRepository.create_refresh_token(
            session, user.id, user.tenant_id, hash_opaque_token(raw_refresh), rt.family_id, expires_at
        )
        return TokenResponse(access_token=access, refresh_token=raw_refresh)

    @staticmethod
    def logout(session, tenant_id: uuid.UUID, refresh_token_str: str) -> None:
        token_hash = hash_opaque_token(refresh_token_str)
        rt = UserRepository.get_refresh_token_by_hash(session, token_hash)
        if rt and rt.revoked_at is None and rt.tenant_id == tenant_id:
            rt.revoked_at = datetime.now(timezone.utc)

    @staticmethod
    def totp_enroll(session, tenant_id: uuid.UUID, user_id: uuid.UUID) -> dict:
        user = UserRepository.get_by_id(session, tenant_id, user_id)
        if not user:
            raise AuthError("User not found")

        secret = pyotp.random_base32()
        cipher = _get_cipher()
        user.totp_pending_secret_enc = cipher.encrypt(secret)

        uri = pyotp.totp.TOTP(secret).provisioning_uri(name=user.email, issuer_name="activia-trace")
        qr = qrcode.make(uri)
        buf = io.BytesIO()
        qr.save(buf)
        buf.seek(0)
        qr_b64 = base64.b64encode(buf.getvalue()).decode()
        return {"otpauth_uri": uri, "qr_base64": qr_b64}

    @staticmethod
    def totp_confirm_enroll(session, tenant_id: uuid.UUID, user_id: uuid.UUID, code: str) -> bool:
        user = UserRepository.get_by_id(session, tenant_id, user_id)
        if not user or not user.totp_pending_secret_enc:
            raise AuthError("No pending TOTP enrollment")

        cipher = _get_cipher()
        secret = cipher.decrypt(user.totp_pending_secret_enc)
        totp = pyotp.TOTP(secret)
        if not totp.verify(code):
            return False

        user.totp_secret_enc = user.totp_pending_secret_enc
        user.totp_pending_secret_enc = None
        user.totp_enabled = True
        return True

    @staticmethod
    def totp_verify_gate(session, tenant_id: uuid.UUID, partial_token_str: str, code: str) -> TokenResponse:
        try:
            claims = decode_token(partial_token_str)
        except InvalidTokenError as exc:
            raise AuthError("Invalid partial token") from exc

        if claims.get("scope") != "2fa_pending":
            raise AuthError("Invalid token scope")

        if str(claims.get("tenant_id")) != str(tenant_id):
            raise AuthError("Tenant mismatch")

        user_id = uuid.UUID(claims["sub"])
        user = UserRepository.get_by_id(session, tenant_id, user_id)
        if not user or not user.totp_enabled or not user.totp_secret_enc:
            raise AuthError("2FA not configured")

        cipher = _get_cipher()
        secret = cipher.decrypt(user.totp_secret_enc)
        if not pyotp.TOTP(secret).verify(code):
            raise AuthError("Invalid TOTP code")

        roles = RbacRepository.get_user_roles(session, user.id, user.tenant_id)
        return _build_token_response(session, user, roles)

    @staticmethod
    def forgot_password(session, tenant_id: uuid.UUID, email: str) -> str | None:
        user = UserRepository.get_by_email(session, tenant_id, email)
        if not user:
            return None  # silent — no enumeration

        raw = generate_opaque_token()
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)
        UserRepository.create_reset_token(session, user.id, tenant_id, hash_opaque_token(raw), expires_at)
        return raw

    @staticmethod
    def reset_password(session, tenant_id: uuid.UUID, token_str: str, new_password: str) -> None:
        token_hash = hash_opaque_token(token_str)
        prt = UserRepository.get_reset_token_by_hash(session, token_hash)

        if prt is None or prt.used_at is not None:
            raise AuthError("Invalid or already used reset token")

        if prt.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            raise AuthError("Reset token expired")

        if str(prt.tenant_id) != str(tenant_id):
            raise AuthError("Invalid reset token")

        user = UserRepository.get_by_id(session, tenant_id, prt.user_id)
        if not user:
            raise AuthError("User not found")

        user.password_hash = hash_password(new_password)
        UserRepository.mark_reset_token_used(session, prt.id)
