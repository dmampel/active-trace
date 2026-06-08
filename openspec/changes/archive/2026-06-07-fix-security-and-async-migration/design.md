## Context

El stack especificado en `docs/ARQUITECTURA.md §2` es FastAPI async + SQLAlchemy 2.0 async + asyncpg. La implementación de C-01→C-06 derivó hacia SQLAlchemy sync (psycopg2) en routers y services, mientras `BaseRepository` (en `repositories/base.py`) fue construido correctamente como async. El resultado es un split incoherente: `BaseRepository` async no es utilizado por ningún service, y todos los routers usan `get_sync_db()` bloqueando el event loop de asyncio.

Adicionalmente, el cifrado de PII usa `cryptography.fernet.Fernet` (AES-128-CBC) cuando el spec exige AES-256. Tres endpoints de auth carecen de rate limiting. El login es case-sensitive para email. Los queries de refresh/reset tokens no aplican `tenant_id` a nivel DB.

**Estado actual de la sesión de ejecución**: 117 tests pasando, 6 changes archivados. Todos los services y repositories relevantes están en `backend/app/`.

## Goals / Non-Goals

**Goals:**
- Unificar toda la stack en async (AsyncSession, asyncpg) — eliminar psycopg2 del path de runtime
- Reemplazar Fernet por AES-256-GCM real usando `cryptography.hazmat.primitives`
- Agregar `@limiter.limit()` a los 3 endpoints faltantes
- Hacer `get_by_email` y login case-insensitive (normalize to lowercase)
- Agregar `tenant_id` scope a `get_refresh_token_by_hash` y `get_reset_token_by_hash`
- Eliminar `commit()` interno de `BaseRepository.delete()`
- Hacer configurable la expiración del token de impersonación
- Mantener 100% de los 117 tests pasando

**Non-Goals:**
- Migrar datos PII cifrados en producción (fuera de scope — procedimiento documentado, no automatizado)
- Agregar nuevas features de auth (CSRF, sesiones, etc.) — eso va en C-08
- Cambiar el schema de DB (no hay migración Alembic en este change)
- Frontend (no existe aún)

## Decisions

### D-01: AES-256-GCM con `cryptography.hazmat` directamente

**Decisión**: Reemplazar `FernetCipher` con `AES256GCMCipher` usando `cryptography.hazmat.primitives.ciphers.aead.AESGCM`.

**Alternativas consideradas**:
- *Fernet con clave de 32 bytes*: No es posible — Fernet solo acepta claves de 32 bytes base64 y siempre usa AES-128 internamente. El nombre del key no cambia el algoritmo.
- *PyNaCl SecretBox*: XSalsa20-Poly1305. Excelente, pero cambia el algoritmo por completo; no cumple el req explícito de AES-256.
- *AES-256-CBC con PKCS7*: No tiene autenticación integrada (AEAD). GCM es superior: cifra + autentica en una operación.

**Implementación**:
```python
# Formato del ciphertext almacenado: base64url( nonce[12] + tag[16] + ciphertext )
# AESGCM requiere clave de exactamente 32 bytes
```
La interfaz pública (`encrypt(str) → str`, `decrypt(str) → str`) no cambia. El cambio es interno a `security.py`. Los sitios de uso en `auth_service.py` no se tocan.

**Re-encrypt en dev**: los datos cifrados con Fernet son incompatibles con AES-256-GCM. En la DB de desarrollo, los campos `totp_secret_enc`, `totp_pending_secret_enc` se NULL-ean con un script de migración de datos (no Alembic — no cambia el schema). En producción no hay datos reales aún.

### D-02: Migración async — strategy "lift and shift" completa en un solo change

**Decisión**: Convertir todos los repositories, services y routers en un solo paso. No hacer migración incremental (async nuevos, sync viejos).

**Alternativas consideradas**:
- *Migración incremental por módulo*: Mantener `get_sync_db` temporalmente para los módulos no migrados. El problema es que `require_permission` (RBAC) se usa en TODOS los routers — si queda sync, bloquea el event loop en cada request autenticado. No hay forma de migrar "solo un módulo" sin migrar el RBAC también.
- *Dejar sync*: Viola el spec. Bloquea el event loop. No escala. Descartado.

**Patrón de migración**:
1. Repositories: `Session` → `AsyncSession`, todos los métodos con `await`
2. Services: `def` → `async def`, `await repo.method()`
3. Routers: `def` → `async def`, `await svc.method()`; `Depends(get_sync_db)` → `Depends(get_db)`
4. `require_permission`: convertir a dependency async con `AsyncSession`
5. `get_sync_db` y `_sync_engine`: eliminar de `dependencies.py`

**El `get_sync_db` para Alembic** se mantiene en `alembic/env.py` únicamente (Alembic necesita sync para migraciones). No en el path de la app.

### D-03: `require_permission` pasa a usar `AsyncSession`

**Decisión**: `require_permission` en `permissions.py` debe usar `AsyncSession` como todos los demás.

**Problema actual**: `RbacRepository.get_effective_permissions` es un método estático sync. Al migrar, se convierte en `async def` y `require_permission` pasa a ser una async dependency.

**Impacto**: Todos los endpoints que usan `Depends(require_permission(...))` automáticamente benefician de non-blocking RBAC checks.

### D-04: Cipher sin `lru_cache` — inicialización en `__init__` del service

**Decisión**: Eliminar `@lru_cache(maxsize=1)` en `_get_cipher()`. Instanciar `AES256GCMCipher` una vez en el módulo al importar (module-level singleton), no en una función cacheada.

**Alternativas consideradas**:
- *Mantener lru_cache*: El problema es que `lru_cache` no expone invalidación. Si `ENCRYPTION_KEY` cambia (key rotation), el proceso sigue usando la clave vieja.
- *Instanciar en cada llamada*: Deroche de CPU. `AESGCM(key)` construye el objeto en cada encrypt/decrypt.
- *Module-level singleton*: Se inicializa una vez al importar el módulo, usando la key de settings. Para key rotation, se reinicia el proceso (aceptable para el MVP).

### D-05: Email normalizado a lowercase en el write path

**Decisión**: `email` se guarda siempre en lowercase en la DB. La normalización ocurre en el service al crear/actualizar un usuario, no en el repository. `get_by_email` compara directamente (ya es lowercase en la DB).

**Alternativas consideradas**:
- *`ilike` o `func.lower()` en cada query*: Funciona sin tocar datos existentes, pero no es indexable eficientemente. El índice `ix_user_tenant_email` en `(tenant_id, email)` no se puede usar con `lower()` a menos que sea un índice funcional.
- *Normalizar al escribir (elegida)*: El índice existente funciona sin cambios. El único riesgo es que datos ya en la DB tengan email mixto — en dev se limpian; en prod no hay datos reales.

## Risks / Trade-offs

**[Riesgo] Re-cifrado de datos PII en producción** → El cambio de AES-128 a AES-256-GCM hace incompatibles los ciphertexts existentes. Los campos `totp_secret_enc` y `totp_pending_secret_enc` en la DB quedarán corruptos si se deployea sin re-cifrar. **Mitigación**: Script de re-encrypt (decrypt con Fernet viejo, encrypt con AESGCM nuevo) a ejecutar en la ventana de deploy. Para el MVP con una sola instancia de desarrollo, se trunca la tabla `user` o se NULL-ean los campos TOTP.

**[Riesgo] Scope de la migración async** → Cambiar sync→async en services y routers implica que cada `def` que accede a la DB debe tener `await`. Un `await` faltante no falla en import time — falla en runtime con un error críptico de coroutine no awaited. **Mitigación**: Los 117 tests existentes cubren los paths críticos. El CI detectará los `await` faltantes en la primera ejecución.

**[Trade-off] Alembic sigue siendo sync** → Alembic no tiene soporte async nativo completo. `alembic/env.py` mantiene `create_engine` sync con psycopg2. Esto es conocido y aceptado — las migraciones corren fuera del ciclo de request.

**[Trade-off] `lru_cache` eliminado** → La key del cipher se recarga en cada restart del proceso. Para key rotation en producción se necesita restart. Aceptable para MVP; una futura implementación podría usar un KMS.

## Migration Plan

1. **Actualizar `security.py`** — `AES256GCMCipher` reemplaza `FernetCipher`. Mantener el alias `FernetCipher = AES256GCMCipher` temporalmente para no romper imports, luego eliminar.
2. **Actualizar `config.py`** — agregar `impersonation_token_expire_minutes: int = 60`.
3. **Migrar repositories** — `base.py`, `user_repository.py`, `rbac_repository.py`, `estructura_repository.py` a async. `audit_log_repository.py` ya es async — verificar consistencia.
4. **Migrar services** — `auth_service.py`, `estructura_service.py`.
5. **Migrar `permissions.py`** — `require_permission` a async dependency.
6. **Migrar routers** — `auth.py`, `estructura.py`, `me.py`. Agregar rate limiting faltante.
7. **Limpiar `dependencies.py`** — eliminar `get_sync_db`, `_sync_engine`, comentarios con task refs.
8. **Actualizar tests** — los fixtures y tests que usen services/repos deben usar `await`.
9. **Script de re-encrypt** — NULL-ear campos TOTP en DB de dev (no hay datos de prod).
10. **Ejecutar suite completa** — `pytest --tb=short -q` debe pasar al 100%.

**Rollback**: git revert del commit. No hay cambios de schema que requieran migración inversa.

## Open Questions

- **¿El email debe ser PII cifrada?** La propuesta actual lo deja en plaintext (necesario para el índice de login). Si el req de negocio exige cifrar el email, se necesita HMAC para búsquedas — eso es un change separado de mayor complejidad. Por ahora: email plaintext + lowercase, documentado como decisión explícita.
- **¿`impersonation_token_expire_minutes` debe ser menor que `access_token_expire_minutes`?** Por seguridad, sería razonable. La implementación actual iguala ambos por defecto (60 min). Si se decide acortar, es un cambio de config, no de código.
