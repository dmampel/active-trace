# Design: C-03 auth-jwt-2fa

## Context

C-01 y C-02 provistos: FastAPI skeleton operativo, PostgreSQL async, `BaseRepository` con tenant scope, `AES256Cipher`, `MissingTenantScopeError`. Lo que falta es la capa que resuelve identidad y tenant en cada request — sin ella el backend no puede aplicar RBAC ni row-level security.

**Restricciones duras del proyecto:**
- Identidad SIEMPRE del JWT verificado, nunca de parámetros de la request.
- Passwords con Argon2id. Nada de MD5/SHA simple.
- Refresh tokens con rotación y detección de reuso (token theft).
- 2FA TOTP opcional por usuario, secreto cifrado AES-256 en reposo.
- Rate limiting 5/60s por IP+email en login.
- Tablas con `tenant_id` y soft delete — hereadas de `TenantMixin` + `TimestampMixin`.

---

## Goals / Non-Goals

**Goals:**
- Implementar los endpoints de auth (`/login`, `/refresh`, `/logout`, `/2fa/*`, `/forgot-password`, `/reset-password`).
- Proveer `get_current_user` como dependency inyectable en cualquier router.
- Crear el modelo `User` mínimo para auth (email, password_hash, totp). El perfil completo con PII va en C-07.
- Migración Alembic con las 3 tablas nuevas.

**Non-Goals:**
- RBAC / `require_permission` — eso es C-04.
- Campos PII del usuario (DNI, CUIL, CBU, teléfono, dirección) — eso es C-07.
- Envío real de emails — el servicio de auth genera el token, el envío lo hace el worker de comunicaciones (C-12) o un stub en tests.
- Frontend — eso es C-21.

---

## Decisions

### D-01: Refresh token — almacenamiento del token en DB
**Decisión**: Guardar en DB el hash SHA-256 del refresh token (el token opaco se entrega al cliente como Bearer). En cada uso se busca por hash, se valida vigencia, y se rota: se inserta el nuevo y se marca el anterior como `revoked_at = now()`.

**Alternativa descartada**: JWT como refresh token (stateless). No permite revocar sesiones individuales ni detectar reuso (token theft). La complejidad de una allowlist elimina la ventaja del stateless.

**Modelo `RefreshToken`:**
```
id: UUID (PK)
user_id: UUID (FK → user.id)
tenant_id: UUID
token_hash: str (SHA-256 del token opaco, único)
family_id: UUID (agrupa los tokens de la misma sesión para detectar reuso)
expires_at: datetime
revoked_at: datetime | None
created_at: datetime
```

Si se detecta reuso de un token ya rotado (token con `revoked_at` distinto de None), se revocan todos los `RefreshToken` con el mismo `family_id`.

---

### D-02: JWT — claims mínimos, sin permisos en el token
**Decisión**: El JWT lleva solo `sub` (user_id), `tenant_id`, `roles` (lista de strings) y `exp`. Los permisos se resuelven server-side en cada request a partir de la matriz de roles (C-04).

**Por qué no permisos en el token**: los permisos pueden cambiar sin que el usuario renueve su sesión (un admin cambia la matriz). Con roles en el token y permisos resueltos server-side, el access token de 15 min tiene ventana corta de staleness y el sistema mantiene control real.

**Algoritmo**: HS256 con `SECRET_KEY` del Settings. En producción se puede migrar a RS256 (asimétrico) sin cambiar la interfaz pública.

---

### D-03: Partial token para gate de 2FA
**Decisión**: Cuando el usuario tiene 2FA activo, el login responde con un `partial_token` JWT de vida muy corta (5 min) que contiene solo `sub`, `tenant_id` y `scope: "2fa_pending"`. El endpoint `/2fa/confirm` valida ese token y el código TOTP, y solo entonces emite la sesión completa.

**Alternativa descartada**: guardar estado de "login parcial" en Redis/DB. Añade infraestructura. El JWT corto es stateless y suficiente para el TTL de 5 min.

---

### D-04: Modelo User — mínimo viable para auth
**Decisión**: `User` hereda de `TenantMixin` + `TimestampMixin` + `SoftDeleteMixin`. Campos de auth:

```
id: UUID (PK, generado)
tenant_id: UUID (NOT NULL, index)
email: str (único dentro del tenant, NOT NULL)
password_hash: str (Argon2id, NOT NULL)
totp_secret_enc: str | None (AES-256, NULL hasta enrolamiento)
totp_pending_secret_enc: str | None (AES-256, durante enrolamiento, antes de confirmar)
totp_enabled: bool (default False)
is_active: bool (default True)
```

Email en texto plano para login. No es PII que necesite cifrado en reposo en este contexto (es el identificador de login). DNI, CUIL, CBU sí van cifrados en C-07.

---

### D-05: PasswordResetToken — tabla dedicada

```
id: UUID (PK)
user_id: UUID (FK → user.id)
tenant_id: UUID
token_hash: str (SHA-256 del token opaco, único)
expires_at: datetime (30 min desde creación)
used_at: datetime | None
created_at: datetime
```

El token se genera con `secrets.token_urlsafe(32)`, se entrega al cliente una sola vez, y se almacena su hash. El endpoint de reset valida hash + vigencia + `used_at is None`.

---

### D-06: Rate limiting con slowapi
**Decisión**: `slowapi` (wrapper de `limits` para FastAPI/Starlette). Límite 5/60s por clave `f"{ip}:{email}"` en el endpoint `/login`. Storage en memoria (suficiente para una instancia). En multi-instancia se configura Redis como backend de `slowapi`.

**Alternativa descartada**: implementar rate limiting propio. Más código, misma funcionalidad.

---

## Estructura de archivos

```
backend/app/
├── models/
│   └── user.py                    # User, RefreshToken, PasswordResetToken
├── schemas/
│   └── auth.py                    # LoginRequest, TokenResponse, PartialTokenResponse,
│                                  # RefreshRequest, LogoutRequest, ForgotPasswordRequest,
│                                  # ResetPasswordRequest, TOTPEnrollResponse, TOTPConfirmRequest
├── repositories/
│   └── user_repository.py         # get_by_email, get_by_id, get_refresh_token_by_hash,
│                                  # create_refresh_token, revoke_refresh_family,
│                                  # get_reset_token_by_hash, create_reset_token, mark_reset_used
├── services/
│   └── auth_service.py            # login, refresh, logout, totp_enroll, totp_confirm,
│                                  # totp_verify_gate, forgot_password, reset_password
├── api/v1/routers/
│   └── auth.py                    # todos los endpoints de auth
├── core/
│   ├── security.py                # (extender) jwt_encode, jwt_decode, hash_password,
│                                  # verify_password, hash_token (SHA-256)
│   └── dependencies.py            # (extender) get_current_user, get_partial_token_user
└── alembic/versions/
    └── 002_auth_tables.py         # user, refresh_token, password_reset_token
```

---

## Risks / Trade-offs

- **[Risk] Secreto JWT comprometido** → Mitigation: rotar `SECRET_KEY` en Settings fuerza re-login de todos los usuarios (refresh tokens siguen siendo válidos hasta expirar). Documentar en runbook.
- **[Risk] Rate limiting en memoria con múltiples réplicas** → Mitigation: aceptable para MVP (instancia única). En escala agregar Redis como backend de slowapi — cambio de config, no de código.
- **[Risk] 30 min de ventana para token de reset** → Mitigation: es la ventana estándar de la industria. Tokens de menor duración aumentan el abandono. Si una institución lo requiere, es un setting por tenant (futura iteración).
- **[Risk] 2FA sin backup codes** → Mitigation: fuera de scope de C-03. Si el usuario pierde el dispositivo, el ADMIN del tenant puede deshabilitar 2FA vía el panel de admin (C-07+).

---

## Migration Plan

1. Ejecutar `alembic upgrade head` — crea tablas `user`, `refresh_token`, `password_reset_token`.
2. Registrar el router `/api/v1/auth` en `main.py`.
3. Para tests: fixture que crea un `Tenant` (C-02) + `User` activo. Usar DB de test (aiosqlite / postgres efímero).
4. No hay datos existentes que migrar — es una tabla nueva.
