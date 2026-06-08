## 1. Security: AES-256-GCM cipher

- [x] 1.1 Reemplazar `FernetCipher` en `security.py` con `AES256GCMCipher` usando `cryptography.hazmat.primitives.ciphers.aead.AESGCM`. Mantener interfaz pública `encrypt(str) → str` / `decrypt(str) → str`. Formato de ciphertext: `base64url(nonce[12] + tag[16] + ciphertext)`.
- [x] 1.2 Eliminar `@lru_cache` de `_get_cipher()` en `auth_service.py`. Instanciar `AES256GCMCipher` como singleton a nivel de módulo.
- [x] 1.3 Escribir tests RED→GREEN para `AES256GCMCipher`: encrypt/decrypt roundtrip, tamper detection (tag modificado → error), clave incorrecta → error.
- [x] 1.4 Script de re-encrypt en dev: NULL-ear `totp_secret_enc` y `totp_pending_secret_enc` en la tabla `user` de la DB de desarrollo (los datos de prod no existen aún).

## 2. Config: nuevas variables

- [x] 2.1 Agregar `impersonation_token_expire_minutes: int = 60` a `core/config.py`.
- [x] 2.2 Usar `settings.impersonation_token_expire_minutes` en `auth_service.py` en lugar del literal `timedelta(minutes=60)`.

## 3. Security: rate limiting en endpoints faltantes

- [x] 3.1 Agregar `@limiter.limit("5/minute")` + `request: Request` a `POST /auth/forgot-password` en `auth.py`.
- [x] 3.2 Agregar `@limiter.limit("5/minute")` + `request: Request` a `POST /auth/2fa/enroll` en `auth.py`.
- [x] 3.3 Agregar `@limiter.limit("5/minute")` a `POST /auth/impersonate` en `auth.py` (ya tiene `request: Request`).
- [x] 3.4 Escribir tests que verifiquen 429 al superar el rate limit en cada uno de los 3 endpoints.

## 4. Security: email case-insensitive y tenant scope en token queries

- [x] 4.1 Normalizar `email.lower()` al momento de guardar el usuario (en el service de creación — cuando se implemente en C-07). Para el login: normalizar `email.lower()` en `AuthService.login()` antes de llamar al repo.
- [x] 4.2 En `UserRepository.get_by_email()`: comparar `func.lower(User.email) == email.lower()` en lugar de `User.email == email`. Agregar test RED→GREEN: login con email en mayúsculas autentica correctamente.
- [x] 4.3 En `UserRepository.get_refresh_token_by_hash()`: agregar filtro `RefreshToken.tenant_id == tenant_id` al query. Actualizar firma para recibir `tenant_id: uuid.UUID`.
- [x] 4.4 En `UserRepository.get_reset_token_by_hash()`: agregar filtro `PasswordResetToken.tenant_id == tenant_id` al query. Actualizar firma para recibir `tenant_id: uuid.UUID`.
- [x] 4.5 Actualizar los callers en `AuthService.refresh()`, `AuthService.reset_password()` para pasar `tenant_id` a los nuevos métodos del repo.
- [x] 4.6 Escribir test: refresh token de tenant B no es retornado cuando se busca con tenant A.

## 5. Migración async — repositories

- [x] 5.1 `repositories/user_repository.py`: convertir todos los métodos a `async def` con `AsyncSession`. Reemplazar `session.execute(stmt)` por `await session.execute(stmt)`. Reemplazar `session.add()` y mutaciones directas por el equivalente async.
- [x] 5.2 `repositories/rbac_repository.py`: ídem — convertir a async.
- [x] 5.3 `repositories/estructura_repository.py`: ídem — convertir a async.
- [x] 5.4 `repositories/audit_log_repository.py`: ya es async — verificar que no use `Session` sync en ningún método. Alinear con el patrón de los otros.
- [x] 5.5 `repositories/base.py`: eliminar `commit()` interno de `delete()`. El caller es responsable del commit.
- [x] 5.6 Ejecutar tests de repositories para confirmar que no hay regresiones.

## 6. Migración async — services

- [x] 6.1 `services/auth_service.py`: convertir todos los métodos de `AuthService` a `async def`. Agregar `await` a todas las llamadas a `UserRepository` y `RbacRepository`.
- [x] 6.2 `services/estructura_service.py`: convertir a async completo.
- [x] 6.3 Ejecutar tests de services para confirmar que no hay regresiones.

## 7. Migración async — core (permissions y dependencies)

- [x] 7.1 `core/permissions.py`: convertir `require_permission` a dependency async. `RbacRepository.get_effective_permissions()` pasa a ser `async def`. Usar `AsyncSession` via `Depends(get_db)`.
- [x] 7.2 `core/dependencies.py`: eliminar `get_sync_db()`, `_get_sync_session_factory()`, `_sync_engine`, `_sync_session_factory`. Eliminar el import de `create_engine` y `sessionmaker` sync. Eliminar comentarios con referencias a task IDs (C-03, C-04).
- [x] 7.3 Verificar que `alembic/env.py` sigue usando su propio engine sync (no importa de `dependencies.py`).

## 8. Migración async — routers

- [x] 8.1 `api/v1/routers/auth.py`: convertir todos los handlers a `async def`. Reemplazar `Depends(get_sync_db)` por `Depends(get_db)`. Agregar `await` a todas las llamadas a `AuthService`.
- [x] 8.2 `api/v1/routers/estructura.py`: convertir a async, reemplazar `get_sync_db` por `get_db`.
- [x] 8.3 `api/v1/routers/me.py`: convertir a async, reemplazar `get_sync_db` por `get_db` (si aplica).
- [x] 8.4 Eliminar el helper `_svc()` sync en `estructura.py` si queda obsoleto con el patrón async.

## 9. Tests: actualización y cobertura

- [x] 9.1 Actualizar `tests/services/test_auth_service.py`: reescritura completa async (PG real, AES256GCMCipher, pytest_asyncio fixtures, `await` en todos los llamados de servicio).
- [x] 9.2 Actualizar `tests/api/v1/routers/test_auth.py`, `test_estructura.py`, `test_me.py`, `test_impersonation.py`: eliminar `get_sync_db`, usar `get_db` + `async def _fake_db()`, AsyncMock para permisos.
- [x] 9.3 Ejecutar suite completa: `pytest --tb=short -q`. Los 117 tests existentes deben pasar. Cero regresiones.
- [x] 9.4 Verificar cobertura: `pytest --cov=app --cov-report=term-missing`. Mantener ≥80% líneas.

## 10. Limpieza final

- [x] 10.1 Verificar que `from app.core.dependencies import get_sync_db` no aparece en ningún archivo de la app (solo en Alembic si aplica).
- [x] 10.2 Verificar que `FernetCipher` no es importado desde ningún archivo (reemplazado por `AES256GCMCipher`).
- [x] 10.3 Verificar que `psycopg2` no aparece en imports del directorio `app/` (solo en `alembic/`).
- [x] 10.4 Ejecutar suite completa una última vez y confirmar cero fallos.
