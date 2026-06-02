# Tasks: C-03 auth-jwt-2fa

## Execution Plan

### 1. Dependencias y security helpers

- [x] Agregar al `pyproject.toml`: `python-jose[cryptography]`, `passlib[argon2]`, `pyotp`, `slowapi`.
- [x] Extender `backend/app/core/security.py` con:
  - `hash_password(plain: str) -> str` (Argon2id via passlib)
  - `verify_password(plain: str, hashed: str) -> bool`
  - `create_access_token(data: dict, expires_delta: timedelta) -> str` (HS256)
  - `create_partial_token(user_id, tenant_id) -> str` (scope `2fa_pending`, TTL 5 min)
  - `decode_token(token: str) -> dict` (raises `InvalidTokenError` si expirado/inválido)
  - `hash_opaque_token(token: str) -> str` (SHA-256 hex, para refresh y reset tokens)
- [x] Escribir `backend/tests/core/test_security_jwt.py`:
  - encode → decode round-trip
  - token expirado lanza excepción
  - hash_password / verify_password round-trip
  - contraseña incorrecta retorna False

### 2. Modelos ORM

- [x] Crear `backend/app/models/user.py` con `User`, `RefreshToken`, `PasswordResetToken` (ver design §D-01, §D-04, §D-05).
- [x] Actualizar `backend/app/models/__init__.py` para exportar los tres modelos.
- [x] Escribir `backend/tests/models/test_user_model.py`:
  - `User` hereda mixins correctamente (uuid, tenant_id, timestamps, soft delete)
  - `RefreshToken` tiene `family_id` y `revoked_at`

### 3. Migración Alembic

- [x] Generar migración: `alembic revision --autogenerate -m "002 auth tables"`.
- [x] Revisar el script generado: verificar índices en `user.email + tenant_id`, `refresh_token.token_hash`, `refresh_token.family_id`.
- [x] Aplicar: `alembic upgrade head` y confirmar que la DB levanta limpia.

### 4. Repositorio de usuario y tokens

- [x] Crear `backend/app/repositories/user_repository.py` con:
  - `get_by_email(session, tenant_id, email) -> User | None`
  - `get_by_id(session, tenant_id, user_id) -> User | None`
  - `create_refresh_token(session, user_id, tenant_id, token_hash, family_id, expires_at) -> RefreshToken`
  - `get_refresh_token_by_hash(session, token_hash) -> RefreshToken | None`
  - `revoke_refresh_family(session, family_id)` — sets `revoked_at = now()` en toda la familia
  - `create_reset_token(session, user_id, tenant_id, token_hash, expires_at) -> PasswordResetToken`
  - `get_reset_token_by_hash(session, token_hash) -> PasswordResetToken | None`
  - `mark_reset_token_used(session, token_id)`
- [x] Escribir `backend/tests/repositories/test_user_repository.py`:
  - `get_by_email` retorna None para email de otro tenant
  - `revoke_refresh_family` revoca todos los tokens de la familia y solo esos
  - `get_reset_token_by_hash` retorna None para token ya usado

### 5. Schemas Pydantic

- [x] Crear `backend/app/schemas/auth.py` con (todos `extra='forbid'`):
  - `LoginRequest(email, password)`
  - `TokenResponse(access_token, refresh_token, token_type="bearer")`
  - `PartialTokenResponse(partial_token, requires_2fa=True)`
  - `RefreshRequest(refresh_token)`
  - `LogoutRequest(refresh_token)`
  - `ForgotPasswordRequest(email)`
  - `ResetPasswordRequest(token, new_password)`
  - `TOTPEnrollResponse(otpauth_uri, qr_base64)`
  - `TOTPConfirmRequest(partial_token, code)`
  - `TOTPVerifyEnrollRequest(code)`

### 6. Servicio de autenticación

- [x] Crear `backend/app/services/auth_service.py` con:
  - `login(session, tenant_id, email, password) -> TokenResponse | PartialTokenResponse`
  - `refresh(session, tenant_id, refresh_token_str) -> TokenResponse` (rotación + detección de reuso)
  - `logout(session, tenant_id, refresh_token_str) -> None`
  - `totp_enroll(session, tenant_id, user_id) -> TOTPEnrollResponse`
  - `totp_confirm_enroll(session, tenant_id, user_id, code) -> bool`
  - `totp_verify_gate(session, tenant_id, partial_token_str, code) -> TokenResponse`
  - `forgot_password(session, tenant_id, email) -> None` (siempre retorna sin revelar existencia)
  - `reset_password(session, tenant_id, token_str, new_password) -> None`
- [x] Escribir `backend/tests/services/test_auth_service.py`:
  - login OK sin 2FA → TokenResponse
  - login OK con 2FA → PartialTokenResponse
  - login KO (password erróneo) → lanza excepción 401
  - refresh rotation: token consumido → nuevo par; token reusado → revoca familia + 401
  - logout → token revocado
  - totp_verify_gate: código correcto → sesión; código incorrecto → 401
  - forgot_password: email inexistente → no lanza, no revela
  - reset_password: token expirado → 400; token ya usado → 400

### 7. Router y rate limiting

- [x] Crear `backend/app/api/v1/routers/auth.py` con todos los endpoints (ver proposal §What Changes).
- [x] Configurar `slowapi` en `backend/app/main.py`: limiter por `f"{request.client.host}:{body.email}"`, 5/60s sobre `/login`.
- [x] Registrar el router en `main.py` bajo el prefix `/api/v1/auth`.

### 8. Dependency `get_current_user`

- [x] Extender `backend/app/core/dependencies.py`:
  - `get_current_user(token: str = Depends(oauth2_scheme), session = Depends(get_session)) -> CurrentUser`
  - Decodifica JWT, valida `exp`, extrae `sub` + `tenant_id` + `roles`.
  - Retorna `CurrentUser(id: UUID, tenant_id: UUID, roles: list[str])`.
  - `get_partial_token_user` — variante que valida `scope == "2fa_pending"`.
- [x] Escribir `backend/tests/core/test_dependencies.py`:
  - JWT válido → CurrentUser correcto
  - JWT expirado → 401
  - JWT con tenant_id alterado en body → identity sigue siendo la del JWT
  - partial_token con scope correcto → CurrentUser parcial

## Review Workload Forecast
- **Estimated changed lines:** ~480 líneas
- **400-line budget risk:** Medio — distribuido en 8 archivos nuevos, ninguno supera 200 LOC
- **Chained PRs recommended:** No
- **Decision needed before apply:** No — design cierra todas las decisiones clave
