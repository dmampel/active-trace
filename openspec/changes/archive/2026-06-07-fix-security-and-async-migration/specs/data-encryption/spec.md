## MODIFIED Requirements

### Requirement: Encrypt Sensitive Attributes
The system MUST encrypt designated PII attributes (DNI, CBU, TOTP secrets) before persisting them to the database using AES-256-GCM. The stored format SHALL be `base64url(nonce[12] || tag[16] || ciphertext)`. The encryption key SHALL be exactly 32 bytes, derived from `ENCRYPTION_KEY` environment variable.

#### Scenario: Saving a new record with PII
- **WHEN** the system persists an entity with a PII attribute (e.g., DNI, TOTP secret)
- **THEN** the value MUST be transformed into an AES-256-GCM cipher string before saving
- **AND** the raw value MUST NOT be visible in database dumps or logs

#### Scenario: Encryption key wrong length
- **WHEN** `ENCRYPTION_KEY` produces a key that is not 32 bytes after derivation
- **THEN** the system MUST raise a configuration error at startup, before accepting requests

---

### Requirement: Decrypt Sensitive Attributes
The system MUST decrypt AES-256-GCM encrypted PII attributes transparently when retrieving them for authorized operations.

#### Scenario: Reading an existing record with PII
- **WHEN** the system retrieves an entity with an AES-256-GCM encrypted attribute
- **THEN** the attribute MUST be decrypted into its original plaintext value

#### Scenario: Invalid or missing encryption key
- **WHEN** the system attempts to decrypt an AES-256-GCM ciphertext but the `ENCRYPTION_KEY` is invalid or missing
- **THEN** the system MUST raise a critical decryption error
- **AND** the operation MUST fail securely without exposing partial data

#### Scenario: Tampered ciphertext rejected
- **WHEN** the system attempts to decrypt a ciphertext whose GCM authentication tag does not match
- **THEN** the system MUST raise a decryption error (AES-GCM provides authenticated encryption — tampered data is detected)

## REMOVED Requirements

### Requirement: Fernet-based encryption (AES-128)
**Reason**: Fernet uses AES-128-CBC internally, which violates the AES-256 requirement from `docs/ARQUITECTURA.md §2` (RNF-08). Replaced by AES-256-GCM via `cryptography.hazmat.primitives.ciphers.aead.AESGCM`.
**Migration**: Existing ciphertexts encrypted with Fernet are incompatible with AES-256-GCM. Execute the re-encrypt script (documented in `design.md`) before deploying. For development environments, NULL-ify TOTP secret columns and re-enroll 2FA.
