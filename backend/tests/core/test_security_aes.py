import pytest
from cryptography.fernet import InvalidToken
from app.core.security import FernetCipher

def test_aes_cipher_encrypt_decrypt():
    # Valid 32-byte url-safe base64 encoded key
    key = b"V6wT1Z_mPZ6BqN0hR5wzZ1xR_j5K6_W7mPZ6BqN0hR4="
    cipher = FernetCipher(key)
    
    plaintext = "this is a secret DNI"
    encrypted = cipher.encrypt(plaintext)
    
    assert encrypted != plaintext
    assert isinstance(encrypted, str)
    
    decrypted = cipher.decrypt(encrypted)
    assert decrypted == plaintext

def test_aes_cipher_invalid_key_raises_error():
    # Invalid key
    with pytest.raises(ValueError):
        FernetCipher(b"invalid_key_length")

def test_aes_cipher_decrypt_invalid_token():
    key = b"V6wT1Z_mPZ6BqN0hR5wzZ1xR_j5K6_W7mPZ6BqN0hR4="
    cipher = FernetCipher(key)
    
    with pytest.raises(InvalidToken):
        cipher.decrypt("invalid-encrypted-string")
