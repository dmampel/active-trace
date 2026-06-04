import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from cryptography.fernet import Fernet
from jose import JWTError, ExpiredSignatureError, jwt
from passlib.context import CryptContext

from app.core.config import Settings


class InvalidTokenError(Exception):
    pass


_pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

_SETTINGS = None


def _settings() -> Settings:
    global _SETTINGS
    if _SETTINGS is None:
        _SETTINGS = Settings()
    return _SETTINGS


# ── Password hashing (Argon2id via passlib) ───────────────────────────────────

def hash_password(plain: str) -> str:
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain, hashed)


# ── JWT (HS256) ───────────────────────────────────────────────────────────────

def create_access_token(data: dict, expires_delta: timedelta) -> str:
    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + expires_delta
    return jwt.encode(payload, _settings().secret_key, algorithm="HS256")


def create_partial_token(user_id: str, tenant_id: str) -> str:
    payload = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "scope": "2fa_pending",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
    }
    return jwt.encode(payload, _settings().secret_key, algorithm="HS256")


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, _settings().secret_key, algorithms=["HS256"])
    except ExpiredSignatureError as exc:
        raise InvalidTokenError("Token expired") from exc
    except JWTError as exc:
        raise InvalidTokenError("Invalid token") from exc


# ── Opaque token hashing (SHA-256) ───────────────────────────────────────────

def hash_opaque_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def generate_opaque_token() -> str:
    return secrets.token_urlsafe(32)


# ── Cifrado simétrico (Fernet / AES-128-CBC + HMAC-SHA256) ───────────────────
# Fernet usa AES-128, no AES-256. La arquitectura aspira a AES-256-GCM — pendiente de migración.

class FernetCipher:
    def __init__(self, key: bytes):
        self.fernet = Fernet(key)

    def encrypt(self, plaintext: str) -> str:
        return self.fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        return self.fernet.decrypt(ciphertext.encode()).decode()
