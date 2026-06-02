# Data Encryption Specification

## Purpose
Define the mechanisms for encrypting and decrypting Personally Identifiable Information (PII) at rest using AES-256 (via Fernet).

## Requirements

### Requirement: Encrypt Sensitive Attributes

The system MUST encrypt designated PII attributes (like DNI, CBU) before persisting them to the database.

#### Scenario: Saving a new record with PII
- GIVEN a valid `ENCRYPTION_KEY` environment variable
- WHEN the system persists an entity with a PII attribute (e.g., DNI)
- THEN the value MUST be transformed into an AES-256 cipher string before saving
- AND the raw value MUST NOT be visible in database dumps or logs

### Requirement: Decrypt Sensitive Attributes

The system MUST decrypt PII attributes transparently when retrieving them for authorized operations.

#### Scenario: Reading an existing record with PII
- GIVEN an entity with an encrypted DNI in the database
- WHEN the system retrieves the entity via `BaseRepository.get()`
- THEN the DNI MUST be decrypted into its original plaintext value

#### Scenario: Invalid or missing encryption key
- GIVEN an encrypted value in the database
- WHEN the system attempts to decrypt it but the `ENCRYPTION_KEY` is invalid or missing
- THEN the system MUST raise a critical decryption error
- AND the operation MUST fail securely without exposing partial data
