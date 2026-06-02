from cryptography.fernet import Fernet

class AES256Cipher:
    """
    AES-256 (Fernet) Encryption helper for PII data.
    Requires a valid 32-byte url-safe base64-encoded key.
    """
    def __init__(self, key: bytes):
        # Fernet validates the key length and format on initialization
        # If the key is invalid, it raises ValueError
        self.fernet = Fernet(key)

    def encrypt(self, plaintext: str) -> str:
        """Encrypts a string and returns the url-safe base64-encoded ciphertext."""
        return self.fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        """Decrypts a url-safe base64-encoded ciphertext and returns the plaintext string."""
        return self.fernet.decrypt(ciphertext.encode()).decode()
