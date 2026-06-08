## Why

El audit de C-01→C-06 identificó violaciones directas al spec documentado en `docs/ARQUITECTURA.md` y `CLAUDE.md`: la implementación usa Fernet (AES-128) en lugar de AES-256 exigido por RNF-08, tres endpoints de auth críticos carecen de rate limiting (RNF-11), y toda la capa de services/repositories opera en modo síncrono a pesar de que el stack especifica explícitamente SQLAlchemy 2.0 async. Estos no son detalles de estilo — son contratos rotos que afectan seguridad, escalabilidad y la coherencia de todos los changes futuros.

## What Changes

- **BREAKING** — Migración sync → async: todos los routers, services y repositories pasan a `AsyncSession`. Se elimina `get_sync_db()` y el engine psycopg2 de `dependencies.py`.
- **BREAKING** — `BaseRepository.delete()` deja de hacer `commit()` interno. El commit es responsabilidad del caller.
- `security.py`: reemplazar `FernetCipher` con implementación AES-256-GCM usando `cryptography.hazmat` directamente. La interfaz `encrypt(str) → str` / `decrypt(str) → str` se mantiene para no romper los sitios de uso.
- `auth.py`: agregar `@limiter.limit()` a `/forgot-password`, `/2fa/enroll` e `/impersonate`.
- `user_repository.py`: `get_refresh_token_by_hash` y `get_reset_token_by_hash` agregan filtro por `tenant_id` en el query (actualmente solo lo validan en el service después del fetch).
- `auth_service.py`: `_get_cipher()` reemplaza `lru_cache` por inicialización explícita que soporta key rotation; expiración de token de impersonación pasa a `settings.impersonation_token_expire_minutes`.
- `user_repository.py` / `auth_service.py`: login normaliza email a lowercase; `get_by_email` compara `func.lower(User.email) == email.lower()`.
- `dependencies.py`: eliminar comentarios con referencias a task IDs (C-03, C-04).
- `config.py`: agregar `IMPERSONATION_TOKEN_EXPIRE_MINUTES` (default: 60).

## Capabilities

### New Capabilities

_(ninguna — este change es de corrección, no de feature)_

### Modified Capabilities

- `user-auth`: rate limiting completo en todos los endpoints de auth; login case-insensitive; token queries con scope de tenant en DB; expiración de impersonación configurable.
- `data-encryption`: AES-256-GCM real en reemplazo de Fernet (AES-128). Misma interfaz pública, implementación interna reemplazada.
- `multi-tenancy`: `BaseRepository.delete()` deja de commitear internamente; todos los repositories son async con `AsyncSession`.

## Impact

**Archivos afectados:**
- `backend/app/core/security.py` — reescritura de `FernetCipher` → `AES256GCMCipher`
- `backend/app/core/dependencies.py` — eliminar sync engine, exponer solo `get_db` async
- `backend/app/core/permissions.py` — migrar `require_permission` a async
- `backend/app/core/config.py` — agregar `impersonation_token_expire_minutes`
- `backend/app/services/auth_service.py` — async completo, cipher sin lru_cache, email lowercase
- `backend/app/services/estructura_service.py` — async completo
- `backend/app/repositories/base.py` — eliminar commit interno de `delete()`
- `backend/app/repositories/user_repository.py` — async, tenant scope en token queries, email lowercase
- `backend/app/repositories/rbac_repository.py` — async
- `backend/app/repositories/audit_log_repository.py` — ya async, verificar consistencia
- `backend/app/repositories/estructura_repository.py` — async
- `backend/app/api/v1/routers/auth.py` — rate limiting en 3 endpoints, async
- `backend/app/api/v1/routers/estructura.py` — async
- `backend/app/api/v1/routers/me.py` — async

**Dependencias:** `cryptography` ya instalada (usada por Fernet). No se agregan dependencias nuevas; se elimina `psycopg2` del path de ejecución (sigue en dev/test para Alembic sync).

**Tests:** todos los tests existentes deben seguir pasando. Los fixtures de `conftest.py` que usan `AsyncSession` no cambian. Los tests de `AuthService` y `EstructuraService` necesitan actualización para `await`.

**Sin migración de datos:** el cifrado AES-256-GCM produce ciphertexts distintos a Fernet. Los datos PII cifrados existentes en la DB de desarrollo deben re-cifrarse. Para producción, se documentará el procedimiento de re-encrypt en el design.
