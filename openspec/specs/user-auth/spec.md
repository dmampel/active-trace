# User Authentication Specification

## Purpose
Define the authentication system for activia-trace: login con credenciales, JWT access + refresh token con rotación, 2FA TOTP opcional por usuario, recuperación de contraseña, y la dependency `get_current_user` que ancla identidad y tenant en toda la app.

## Requirements

### Requirement: Login con email y password
El sistema SHALL validar las credenciales email + password del usuario contra el registro del tenant. Si son válidas y el usuario no tiene 2FA activo, SHALL emitir un JWT access token (TTL 15 min) y un refresh token opaco (TTL 7 días). Si el usuario tiene 2FA activo, SHALL emitir un `partial_token` de vida muy corta (5 min) en lugar de la sesión completa.

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

#### Scenario: Rate limit excedido
- **WHEN** el mismo par IP+email realiza más de 5 intentos de login en 60 segundos
- **THEN** el sistema responde 429 y rechaza el intento sin procesar las credenciales

---

### Requirement: Refresh token con rotación
El sistema SHALL aceptar un refresh token válido y emitir un nuevo par (access + refresh). El refresh token consumido SHALL quedar revocado inmediatamente. Si se detecta reuso de un token ya rotado, el sistema SHALL revocar toda la familia de sesión (detect token theft).

#### Scenario: Refresh exitoso
- **WHEN** el cliente envía un refresh token válido y vigente
- **THEN** el sistema responde 200 con nuevo `access_token` y nuevo `refresh_token`, y el token anterior queda revocado

#### Scenario: Reuso de refresh rotado
- **WHEN** el cliente envía un refresh token que ya fue rotado (ya existe una versión más nueva de la misma familia)
- **THEN** el sistema revoca todos los tokens de esa familia y responde 401

#### Scenario: Refresh token expirado
- **WHEN** el cliente envía un refresh token con `expires_at` en el pasado
- **THEN** el sistema responde 401

---

### Requirement: Logout
El sistema SHALL revocar el refresh token activo de la sesión, invalidando la capacidad de obtener nuevos access tokens.

#### Scenario: Logout exitoso
- **WHEN** el usuario autenticado envía su refresh token al endpoint de logout
- **THEN** el sistema revoca el token y responde 204

#### Scenario: Logout con token ya revocado
- **WHEN** el usuario envía un refresh token ya revocado
- **THEN** el sistema responde 204 (idempotente, no exponer estado del token)

---

### Requirement: Verificación de identidad por JWT
El sistema SHALL proveer una dependency `get_current_user` que valida el JWT, extrae `sub` (user_id) y `tenant_id`, y retorna la identidad del actor. La identidad y el tenant SHALL derivar exclusivamente del JWT verificado — jamás de parámetros de la request.

#### Scenario: Token válido
- **WHEN** un endpoint usa `get_current_user` y la request trae un JWT válido y vigente
- **THEN** la dependency retorna `CurrentUser(id, tenant_id, roles)` sin error

#### Scenario: Token ausente o malformado
- **WHEN** la request no trae `Authorization: Bearer <token>` o el token es inválido
- **THEN** la dependency levanta `HTTPException 401`

#### Scenario: Token expirado
- **WHEN** el JWT tiene `exp` en el pasado
- **THEN** la dependency levanta `HTTPException 401`

#### Scenario: Identidad inmutable por parámetro
- **WHEN** la request incluye un `user_id` o `tenant_id` en body, query string o header
- **THEN** el sistema ignora esos valores y usa exclusivamente los del JWT verificado

---

### Requirement: 2FA TOTP — enrolamiento
El sistema SHALL permitir a un usuario autenticado enrolar un segundo factor TOTP. El secreto TOTP SHALL almacenarse cifrado con AES-256 en reposo. El 2FA no queda activo hasta que el usuario lo confirme con un código válido.

#### Scenario: Inicio de enrolamiento
- **WHEN** el usuario autenticado solicita enrolar 2FA
- **THEN** el sistema genera un secreto TOTP, lo almacena cifrado (pendiente de confirmación), y responde con la URI `otpauth://` y una representación QR

#### Scenario: Confirmación de enrolamiento con código válido
- **WHEN** el usuario envía un código TOTP válido para confirmar el enrolamiento
- **THEN** el sistema activa `totp_enabled = true` en la cuenta

#### Scenario: Confirmación con código inválido
- **WHEN** el usuario envía un código TOTP incorrecto durante el enrolamiento
- **THEN** el sistema responde 400 y el 2FA permanece inactivo

---

### Requirement: 2FA TOTP — gate de login
El sistema SHALL exigir el código TOTP como segundo paso cuando el usuario tiene 2FA activo, usando el `partial_token` emitido en el primer paso.

#### Scenario: Verificación TOTP exitosa
- **WHEN** el usuario envía el `partial_token` + código TOTP válido
- **THEN** el sistema emite la sesión completa (access + refresh token)

#### Scenario: Código TOTP inválido
- **WHEN** el usuario envía el `partial_token` + código TOTP incorrecto
- **THEN** el sistema responde 401; el `partial_token` permanece válido hasta su expiración

#### Scenario: Partial token expirado
- **WHEN** el usuario envía un `partial_token` con `exp` en el pasado
- **THEN** el sistema responde 401 y requiere reiniciar el login

---

### Requirement: Recuperación de contraseña
El sistema SHALL permitir al usuario solicitar un enlace de recuperación enviado al email registrado. El token de recuperación es de un solo uso y expira en 30 minutos. El sistema SHALL responder siempre con 200 para no revelar si el email existe en el tenant.

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
## MODIFIED Requirements

### Requirement: JWT access token contiene roles vigentes del usuario

El access token SHALL incluir en el claim `roles` la lista de nombres de roles vigentes del usuario (asignaciones activas en `user_rol` al momento del login o refresh). Antes de C-04, este claim siempre era `[]`.

El claim `roles` es informativo — NO es la fuente de autorización. La autorización se resuelve siempre desde la DB via `require_permission`.

#### Scenario: Login sin 2FA emite token con roles vigentes
- **WHEN** un usuario con asignación vigente de rol COORDINADOR hace login exitoso (sin 2FA)
- **THEN** el access token decodificado contiene `roles: ["COORDINADOR"]`

#### Scenario: Refresh rota y emite token con roles actualizados
- **WHEN** un usuario rota su refresh token
- **THEN** el nuevo access token contiene los roles vigentes al momento del refresh (no los del login original)

#### Scenario: Usuario sin asignaciones vigentes tiene roles vacíos
- **WHEN** un usuario autenticado no tiene ninguna asignación vigente en `user_rol`
- **THEN** el access token tiene `roles: []` y el guard `require_permission` retorna 403 para cualquier endpoint protegido

---

### Requirement: Iniciar sesión de impersonación
El sistema SHALL permitir que un usuario con permiso `impersonacion:usar` inicie una sesión de impersonación sobre otro usuario del mismo tenant. El sistema SHALL emitir un JWT de corta duración (TTL 60 min) con el `sub` del actor real y un claim adicional `impersonado_id`. El sistema SHALL registrar la acción en el audit log con código `IMPERSONACION_INICIAR`.

#### Scenario: Impersonación exitosa
- **WHEN** un usuario autenticado con permiso `impersonacion:usar` llama `POST /auth/impersonate` con `{"target_user_id": "<uuid>"}`
- **THEN** el sistema responde 200 con un `impersonate_token` JWT de 60 min, el audit log registra `IMPERSONACION_INICIAR`, y el JWT contiene `impersonado_id=target_user_id`

#### Scenario: Impersonación sin permiso
- **WHEN** un usuario sin permiso `impersonacion:usar` llama `POST /auth/impersonate`
- **THEN** el sistema responde 403

#### Scenario: Impersonación a usuario de otro tenant
- **WHEN** el actor intenta impersonar un `target_user_id` que pertenece a otro tenant
- **THEN** el sistema responde 404 (no revelar existencia de usuario cross-tenant)

#### Scenario: Impersonación anidada rechazada
- **WHEN** el actor ya tiene un token con `impersonado_id` activo e intenta llamar `POST /auth/impersonate`
- **THEN** el sistema responde 400 con error "No se puede impersonar desde una sesión de impersonación activa"

---

### Requirement: Finalizar sesión de impersonación
El sistema SHALL proveer un endpoint para que el actor real finalice la sesión de impersonación. El sistema SHALL registrar la acción en el audit log con código `IMPERSONACION_FINALIZAR`.

#### Scenario: Fin de impersonación exitoso
- **WHEN** el actor real llama `POST /auth/impersonate/end` con un token que tiene `impersonado_id`
- **THEN** el sistema responde 200, el audit log registra `IMPERSONACION_FINALIZAR`, y el `impersonate_token` queda descartado

#### Scenario: Fin de impersonación sin sesión activa
- **WHEN** un usuario sin sesión de impersonación llama `POST /auth/impersonate/end`
- **THEN** el sistema responde 400 con error "No hay sesión de impersonación activa"

---

### Requirement: `get_current_user` expone impersonado_id
La dependency `get_current_user` SHALL leer el claim `impersonado_id` del JWT (si presente) y exponerlo en el objeto `CurrentUser`. El `actor_id` del `CurrentUser` SHALL siempre ser el `sub` del JWT (usuario real), nunca el `impersonado_id`.

#### Scenario: Token con impersonado_id
- **WHEN** el JWT contiene el claim `impersonado_id`
- **THEN** `get_current_user` retorna `CurrentUser(id=sub, tenant_id=..., impersonado_id=impersonado_id)`

#### Scenario: Token normal sin impersonado_id
- **WHEN** el JWT no contiene el claim `impersonado_id`
- **THEN** `get_current_user` retorna `CurrentUser(id=sub, tenant_id=..., impersonado_id=None)`
