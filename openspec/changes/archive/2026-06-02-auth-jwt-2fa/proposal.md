## Why

Con C-01 (infrastructure) y C-02 (tenant model + base repository) archivados, el próximo bloqueante del camino crítico es la capa de autenticación. Sin ella, ningún endpoint puede resolver la identidad del usuario ni su tenant — haciendo imposible aplicar cualquier regla de negocio con scope de tenant. Todo el árbol de dependencias (C-04 RBAC → C-06 estructura → C-07 usuarios → ...) está bloqueado hasta que `get_current_user` exista y sea confiable.

## What Changes

- `POST /api/v1/auth/login` — valida email + password (Argon2id), emite JWT access (15 min) + refresh token con rotación. Si el usuario tiene 2FA activo, la respuesta es un `partial_token` que requiere verificación TOTP antes de emitir la sesión completa.
- `POST /api/v1/auth/refresh` — consume el refresh token actual (lo invalida), emite un nuevo par. Reuso de un token ya rotado revoca toda la familia de sesión.
- `POST /api/v1/auth/logout` — revoca el refresh token activo de la sesión.
- `POST /api/v1/auth/2fa/enroll` — genera secreto TOTP y QR para el usuario autenticado.
- `POST /api/v1/auth/2fa/verify` — confirma el código TOTP y activa 2FA en la cuenta.
- `POST /api/v1/auth/2fa/confirm` — gate intermedio: valida TOTP después del login y emite la sesión completa.
- `POST /api/v1/auth/forgot-password` — genera token de un solo uso y lo envía al email registrado.
- `POST /api/v1/auth/reset-password` — consume el token de recuperación (lo invalida) y reemplaza el password.
- Modelos nuevos: `User` (auth fields), `RefreshToken`, `PasswordResetToken`.
- Migración Alembic: tablas `user`, `refresh_token`, `password_reset_token`.
- Rate limiting: 5 intentos / 60 s por combinación IP+email en el endpoint de login.
- Dependency `get_current_user` actualizada para resolver identity + tenant_id desde JWT verificado.

## Capabilities

### New Capabilities
- `user-auth`: Autenticación completa — login, refresh rotation, logout, 2FA TOTP opcional, recuperación de contraseña por email, y la dependency `get_current_user` que ancla identidad + tenant en toda la app.

### Modified Capabilities
*(ninguna — los specs existentes no cambian de requerimientos)*

## Impact

- **Archivos nuevos**: `app/models/user.py`, `app/schemas/auth.py`, `app/services/auth_service.py`, `app/repositories/user_repository.py`, `app/api/v1/routers/auth.py`, `alembic/versions/002_auth_tables.py`.
- **Archivos modificados**: `app/core/dependencies.py` (implementa `get_current_user`), `app/core/security.py` (agrega JWT + Argon2id helpers), `app/main.py` (registra router auth + rate limiter).
- **Dependencias nuevas**: `python-jose[cryptography]`, `passlib[argon2]`, `pyotp`, `slowapi`, `python-multipart`.
- **Governance**: CRÍTICO — auth + multi-tenancy. No se escribe código sin aprobación del cambio.
