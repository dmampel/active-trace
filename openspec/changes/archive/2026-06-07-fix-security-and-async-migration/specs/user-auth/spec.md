## MODIFIED Requirements

### Requirement: Login con email y password
El sistema SHALL validar las credenciales email + password del usuario contra el registro del tenant. La comparación de email SHALL ser case-insensitive (normalizado a lowercase). Si son válidas y el usuario no tiene 2FA activo, SHALL emitir un JWT access token (TTL 15 min) y un refresh token opaco (TTL 7 días). Si el usuario tiene 2FA activo, SHALL emitir un `partial_token` de vida muy corta (5 min) en lugar de la sesión completa. El endpoint SHALL aplicar rate limiting (5 intentos por minuto por IP).

#### Scenario: Login exitoso sin 2FA
- **WHEN** el usuario envía email y password correctos y no tiene 2FA activo
- **THEN** el sistema responde 200 con `access_token`, `refresh_token` y `token_type: "bearer"`

#### Scenario: Login exitoso con 2FA activo
- **WHEN** el usuario envía email y password correctos y tiene 2FA activo
- **THEN** el sistema responde 200 con `partial_token` y `requires_2fa: true`, sin emitir sesión completa

#### Scenario: Credenciales incorrectas
- **WHEN** el usuario envía email o password incorrectos
- **THEN** el sistema responde 401 con mensaje genérico (sin revelar cuál campo falló)

#### Scenario: Usuario inactivo
- **WHEN** el usuario tiene `is_active = false`
- **THEN** el sistema responde 401 con mensaje genérico

#### Scenario: Rate limit excedido en login
- **WHEN** la misma IP realiza más de 5 intentos de login en 60 segundos
- **THEN** el sistema responde 429 y rechaza el intento sin procesar las credenciales

#### Scenario: Login con email en mayúsculas
- **WHEN** el usuario envía `Admin@UTN.com` y el registro en la DB es `admin@utn.com`
- **THEN** el sistema autentica correctamente (comparación case-insensitive)

---

### Requirement: Recuperación de contraseña
El sistema SHALL permitir al usuario solicitar un enlace de recuperación enviado al email registrado. El token de recuperación es de un solo uso y expira en 30 minutos. El sistema SHALL responder siempre con 200 para no revelar si el email existe en el tenant. El endpoint SHALL aplicar rate limiting (5 solicitudes por minuto por IP).

#### Scenario: Solicitud de recuperación (email registrado)
- **WHEN** el usuario solicita recuperación con un email que existe en el tenant
- **THEN** el sistema genera un token de recuperación de un solo uso, lo almacena hasheado, y envía el email. Responde 200.

#### Scenario: Solicitud de recuperación (email no registrado)
- **WHEN** el usuario solicita recuperación con un email que no existe en el tenant
- **THEN** el sistema responde 200 sin revelar que el email no existe (respuesta idéntica al caso exitoso)

#### Scenario: Reset con token válido
- **WHEN** el usuario envía el token de recuperación y una nueva contraseña
- **THEN** el sistema actualiza el password (Argon2id), invalida el token, y responde 200

#### Scenario: Reset con token ya usado
- **WHEN** el usuario envía un token de recuperación que ya fue consumido
- **THEN** el sistema responde 400

#### Scenario: Reset con token expirado
- **WHEN** el usuario envía un token de recuperación con `expires_at` en el pasado
- **THEN** el sistema responde 400

#### Scenario: Rate limit excedido en forgot-password
- **WHEN** la misma IP realiza más de 5 solicitudes de recuperación en 60 segundos
- **THEN** el sistema responde 429

---

### Requirement: 2FA TOTP — enrolamiento
El sistema SHALL permitir a un usuario autenticado enrolar un segundo factor TOTP. El secreto TOTP SHALL almacenarse cifrado con AES-256-GCM en reposo. El 2FA no queda activo hasta que el usuario lo confirme con un código válido. El endpoint SHALL aplicar rate limiting (5 intentos por minuto por IP).

#### Scenario: Inicio de enrolamiento
- **WHEN** el usuario autenticado solicita enrolar 2FA
- **THEN** el sistema genera un secreto TOTP, lo almacena cifrado (pendiente de confirmación), y responde con la URI `otpauth://` y una representación QR

#### Scenario: Confirmación de enrolamiento con código válido
- **WHEN** el usuario envía un código TOTP válido para confirmar el enrolamiento
- **THEN** el sistema activa `totp_enabled = true` en la cuenta

#### Scenario: Confirmación con código inválido
- **WHEN** el usuario envía un código TOTP incorrecto durante el enrolamiento
- **THEN** el sistema responde 400 y el 2FA permanece inactivo

#### Scenario: Rate limit excedido en enrolamiento
- **WHEN** la misma IP realiza más de 5 solicitudes de enrolamiento en 60 segundos
- **THEN** el sistema responde 429

---

### Requirement: Iniciar sesión de impersonación
El sistema SHALL permitir que un usuario con permiso `impersonacion:usar` inicie una sesión de impersonación sobre otro usuario del mismo tenant. El sistema SHALL emitir un JWT de corta duración (TTL configurable via `IMPERSONATION_TOKEN_EXPIRE_MINUTES`, default 60 min) con el `sub` del actor real y un claim adicional `impersonado_id`. El sistema SHALL registrar la acción en el audit log con código `IMPERSONACION_INICIAR`. El endpoint SHALL aplicar rate limiting (5 solicitudes por minuto por IP).

#### Scenario: Impersonación exitosa
- **WHEN** un usuario autenticado con permiso `impersonacion:usar` llama `POST /auth/impersonate` con `{"target_user_id": "<uuid>"}`
- **THEN** el sistema responde 200 con un `impersonate_token` JWT con TTL según `IMPERSONATION_TOKEN_EXPIRE_MINUTES`, el audit log registra `IMPERSONACION_INICIAR`, y el JWT contiene `impersonado_id=target_user_id`

#### Scenario: Impersonación sin permiso
- **WHEN** un usuario sin permiso `impersonacion:usar` llama `POST /auth/impersonate`
- **THEN** el sistema responde 403

#### Scenario: Impersonación a usuario de otro tenant
- **WHEN** el actor intenta impersonar un `target_user_id` que pertenece a otro tenant
- **THEN** el sistema responde 404 (no revelar existencia de usuario cross-tenant)

#### Scenario: Impersonación anidada rechazada
- **WHEN** el actor ya tiene un token con `impersonado_id` activo e intenta llamar `POST /auth/impersonate`
- **THEN** el sistema responde 400 con error "No se puede impersonar desde una sesión de impersonación activa"

#### Scenario: Rate limit excedido en impersonación
- **WHEN** la misma IP realiza más de 5 solicitudes de impersonación en 60 segundos
- **THEN** el sistema responde 429

## ADDED Requirements

### Requirement: Refresh y reset tokens con scope de tenant en DB
Los queries `get_refresh_token_by_hash` y `get_reset_token_by_hash` SHALL incluir el filtro `tenant_id` en la query SQL, no solo validarlo en el service después del fetch.

#### Scenario: Refresh token buscado con tenant correcto
- **WHEN** el service solicita un refresh token por hash con un `tenant_id` válido
- **THEN** el repository retorna el token si y solo si pertenece a ese tenant

#### Scenario: Refresh token de otro tenant no retornado
- **WHEN** el service solicita un refresh token por hash con un `tenant_id` que no corresponde al token
- **THEN** el repository retorna `None` (el service no recibe el token para validarlo a posteriori)
