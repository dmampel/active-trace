import base64
import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from jose import JWTError, ExpiredSignatureError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings


class InvalidTokenError(Exception):
    pass


_pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


# ── Password hashing (Argon2id via passlib) ───────────────────────────────────

def hash_password(plain: str) -> str:
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain, hashed)


# ── JWT (HS256) ───────────────────────────────────────────────────────────────

def create_access_token(data: dict, expires_delta: timedelta) -> str:
    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + expires_delta
    return jwt.encode(payload, get_settings().secret_key, algorithm="HS256")


def create_partial_token(user_id: str, tenant_id: str) -> str:
    payload = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "scope": "2fa_pending",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
    }
    return jwt.encode(payload, get_settings().secret_key, algorithm="HS256")


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, get_settings().secret_key, algorithms=["HS256"])
    except ExpiredSignatureError as exc:
        raise InvalidTokenError("Token expired") from exc
    except JWTError as exc:
        raise InvalidTokenError("Invalid token") from exc


# ── Opaque token hashing (SHA-256) ───────────────────────────────────────────

def hash_opaque_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def generate_opaque_token() -> str:
    return secrets.token_urlsafe(32)


# ── Cifrado simétrico AES-256-GCM ─────────────────────────────────────────────
# Formato almacenado: base64url( nonce[12] + ciphertext+tag )
# AESGCM requiere clave de exactamente 32 bytes.

class AES256GCMCipher:
    def __init__(self, key: bytes):
        if len(key) != 32:
            raise ValueError("AES-256 key must be exactly 32 bytes")
        self._aesgcm = AESGCM(key)

    def encrypt(self, plaintext: str) -> str:
        nonce = os.urandom(12)
        ct = self._aesgcm.encrypt(nonce, plaintext.encode(), None)
        return base64.urlsafe_b64encode(nonce + ct).rstrip(b"=").decode()

    def decrypt(self, ciphertext: str) -> str:
        padding = "=" * (-len(ciphertext) % 4)
        raw = base64.urlsafe_b64decode(ciphertext + padding)
        nonce, ct = raw[:12], raw[12:]
        return self._aesgcm.decrypt(nonce, ct, None).decode()
