"""Tests de cifrado PII en UsuarioService.

Strict TDD:
  2.1 - helper cifrado/descifrado round-trip
  2.3 - valor persistido en *_enc NO coincide con texto plano
  2.4 - PII no aparece en texto plano en logs
"""
import logging
import os
import uuid

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5433/activia_trace_test")
os.environ.setdefault("TEST_DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5433/activia_trace_test")
os.environ.setdefault("SECRET_KEY", "a" * 64)
os.environ.setdefault("ENCRYPTION_KEY", "b" * 64)


# ── 2.1 Round-trip PII con AES256GCMCipher ────────────────────────────────────

def test_pii_cipher_roundtrip_dni():
    """El helper cifra y descifra DNI correctamente."""
    from app.services.usuario_service import _cipher
    plain = "20123456"
    ciphertext = _cipher.encrypt(plain)
    assert _cipher.decrypt(ciphertext) == plain


def test_pii_cipher_roundtrip_cuil():
    from app.services.usuario_service import _cipher
    plain = "20201234567"
    assert _cipher.decrypt(_cipher.encrypt(plain)) == plain


def test_pii_cipher_roundtrip_cbu():
    from app.services.usuario_service import _cipher
    plain = "0000003100012345678900"
    assert _cipher.decrypt(_cipher.encrypt(plain)) == plain


def test_pii_cipher_roundtrip_alias_cbu():
    from app.services.usuario_service import _cipher
    plain = "mi.alias.cbu"
    assert _cipher.decrypt(_cipher.encrypt(plain)) == plain


def test_pii_cipher_each_encryption_is_different():
    """Dos cifrados del mismo texto producen resultados distintos (nonce aleatorio)."""
    from app.services.usuario_service import _cipher
    plain = "20123456"
    enc1 = _cipher.encrypt(plain)
    enc2 = _cipher.encrypt(plain)
    assert enc1 != enc2
    assert _cipher.decrypt(enc1) == plain
    assert _cipher.decrypt(enc2) == plain


# ── 2.3 Valor persistido en *_enc no coincide con texto plano ─────────────────

def test_encrypt_dni_is_not_plaintext():
    from app.services.usuario_service import encrypt_pii
    plain = "20123456"
    encrypted = encrypt_pii(plain)
    assert encrypted != plain
    assert len(encrypted) > len(plain)


def test_encrypt_returns_none_for_none():
    from app.services.usuario_service import encrypt_pii
    assert encrypt_pii(None) is None


def test_decrypt_returns_none_for_none():
    from app.services.usuario_service import decrypt_pii
    assert decrypt_pii(None) is None


# ── 2.4 PII no aparece en texto plano en logs ─────────────────────────────────

def test_pii_not_in_logs_on_encrypt(caplog):
    """El valor plano de la PII no debe aparecer en los logs durante cifrado."""
    from app.services.usuario_service import encrypt_pii
    with caplog.at_level(logging.DEBUG):
        result = encrypt_pii("20123456")
    # Ningún record de log contiene el DNI en texto plano
    for record in caplog.records:
        assert "20123456" not in record.getMessage()


def test_pii_not_in_logs_on_decrypt(caplog):
    """El valor descifrado de la PII no debe aparecer en los logs durante descifrado."""
    from app.services.usuario_service import _cipher, decrypt_pii
    ciphertext = _cipher.encrypt("20123456")
    with caplog.at_level(logging.DEBUG):
        result = decrypt_pii(ciphertext)
    assert result == "20123456"
    for record in caplog.records:
        assert "20123456" not in record.getMessage()
