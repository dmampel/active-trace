import pytest
from app.core.security import AES256GCMCipher


def test_aes256gcm_roundtrip():
    key = b"b" * 32
    cipher = AES256GCMCipher(key)
    plaintext = "super-secret DNI: 12345678"
    assert cipher.decrypt(cipher.encrypt(plaintext)) == plaintext


def test_aes256gcm_ciphertext_differs_from_plaintext():
    key = b"b" * 32
    cipher = AES256GCMCipher(key)
    encrypted = cipher.encrypt("some value")
    assert encrypted != "some value"
    assert isinstance(encrypted, str)


def test_aes256gcm_nonce_randomness():
    key = b"b" * 32
    cipher = AES256GCMCipher(key)
    ct1 = cipher.encrypt("same plaintext")
    ct2 = cipher.encrypt("same plaintext")
    assert ct1 != ct2  # nonces differ


def test_aes256gcm_tamper_detection():
    key = b"b" * 32
    cipher = AES256GCMCipher(key)
    encrypted = cipher.encrypt("secret")
    # Tamper with the ciphertext
    import base64
    raw = base64.urlsafe_b64decode(encrypted + "==")
    tampered = raw[:-1] + bytes([raw[-1] ^ 0xFF])
    bad = base64.urlsafe_b64encode(tampered).rstrip(b"=").decode()
    with pytest.raises(Exception):
        cipher.decrypt(bad)


def test_aes256gcm_wrong_key_raises():
    key_a = b"a" * 32
    key_b = b"b" * 32
    cipher_a = AES256GCMCipher(key_a)
    cipher_b = AES256GCMCipher(key_b)
    encrypted = cipher_a.encrypt("secret value")
    with pytest.raises(Exception):
        cipher_b.decrypt(encrypted)
