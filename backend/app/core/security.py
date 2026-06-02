"""RESERVADO para C-03 (auth-jwt-2fa).

Este módulo implementará:
- Hashing de passwords con Argon2id
- Firma y verificación de JWT (access + refresh tokens)
- Cifrado/descifrado AES-256 para PII en reposo (CBU, DNI, email cifrado)
- Rate limiting de intentos de login

NO agregar lógica en este archivo hasta C-03. Su existencia es un contrato
de extensión que guía a los agentes de changes futuros.
"""

# Implementar en C-03: hash_password, verify_password
# Implementar en C-03: create_access_token, create_refresh_token, decode_token
# Implementar en C-03/C-02: encrypt_pii, decrypt_pii (AES-256)
