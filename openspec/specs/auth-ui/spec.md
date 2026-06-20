## ADDED Requirements

### Requirement: Cliente HTTP centralizado con interceptor JWT
El sistema SHALL proveer un cliente Axios centralizado en `src/shared/services/api.ts` que adjunta automáticamente el `Authorization: Bearer <access_token>` en cada request. El cliente SHALL interceptar respuestas 401 y ejecutar un refresh de token transparente (sin intervención del componente) antes de reintentar el request original.

#### Scenario: Request con token válido adjunta header Authorization
- **WHEN** un hook de feature realiza un GET a cualquier endpoint protegido
- **THEN** el header `Authorization: Bearer <token>` está presente en la request HTTP

#### Scenario: Refresh transparente en 401
- **WHEN** el servidor devuelve 401 porque el access token expiró
- **THEN** el cliente ejecuta `POST /api/auth/refresh` de forma transparente y reintenta el request original con el nuevo token, sin que el componente reciba el 401

#### Scenario: Refresh fallido redirige a login
- **WHEN** el refresh también retorna 401 (refresh token expirado o revocado)
- **THEN** el cliente limpia los tokens del almacenamiento, cancela todos los requests en cola y redirige al usuario a `/login`

#### Scenario: Requests concurrentes con token expirado esperan en cola
- **WHEN** dos requests concurrentes reciben 401 simultáneamente
- **THEN** solo se emite un refresh (no dos); ambas requests se resuelven con el nuevo token tras el refresh exitoso

### Requirement: Pantalla de login
El sistema SHALL proveer una pantalla de login accesible en `/login` con campos de email y contraseña, validados con React Hook Form + Zod antes de enviar al backend. Un login exitoso SHALL almacenar los tokens y redirigir a `/` (o a la ruta previa guardada por el guard).

#### Scenario: Login exitoso redirige al dashboard
- **WHEN** el usuario ingresa credenciales válidas y envía el formulario
- **THEN** se almacenan los tokens, el `AuthContext` refleja la sesión activa y el router navega a `/`

#### Scenario: Login fallido muestra mensaje de error
- **WHEN** el servidor devuelve 401 (credenciales inválidas)
- **THEN** el formulario muestra un mensaje de error legible y NO redirige

#### Scenario: Campos requeridos se validan en cliente
- **WHEN** el usuario envía el formulario con email vacío o sin formato válido
- **THEN** Zod/RHF muestra el error de validación sin emitir el request al backend

### Requirement: Pantalla de segundo factor TOTP
Si el backend responde al login con un estado de `2fa_required`, el sistema SHALL mostrar una pantalla de ingreso de código TOTP antes de emitir los tokens de sesión.

#### Scenario: Pantalla 2FA aparece tras login con 2FA habilitado
- **WHEN** el backend devuelve `{"status": "2fa_required", "temp_token": "..."}` en el login
- **THEN** el router navega a `/login/2fa` mostrando el campo de código TOTP

#### Scenario: Código TOTP correcto completa la autenticación
- **WHEN** el usuario ingresa un código TOTP válido y el backend lo verifica
- **THEN** se almacenan los tokens y el usuario accede al dashboard

#### Scenario: Código TOTP incorrecto muestra error
- **WHEN** el usuario ingresa un código TOTP inválido
- **THEN** se muestra un mensaje de error sin cerrar la pantalla de 2FA

### Requirement: Flujo de recuperación de contraseña
El sistema SHALL proveer dos pantallas: (1) `/forgot-password` donde el usuario ingresa su email para solicitar el token de recuperación; (2) `/reset-password?token=<t>` donde ingresa y confirma la nueva contraseña.

#### Scenario: Solicitud de recuperación enviada exitosamente
- **WHEN** el usuario ingresa su email en `/forgot-password` y envía el formulario
- **THEN** el sistema llama a `POST /api/auth/forgot` y muestra un mensaje de confirmación (sin revelar si el email existe)

#### Scenario: Nueva contraseña establece la sesión o redirige a login
- **WHEN** el usuario establece una nueva contraseña válida en `/reset-password`
- **THEN** el backend procesa el reset y el sistema redirige a `/login` con mensaje de éxito

### Requirement: AuthGuard de rutas por permiso
El sistema SHALL proveer un componente `AuthGuard` que envuelve rutas protegidas. Sin sesión activa SHALL redirigir a `/login` guardando la ruta de origen. Con sesión pero sin el permiso requerido SHALL mostrar una pantalla de acceso denegado (403) en lugar de la ruta solicitada.

#### Scenario: Sin sesión redirige a login conservando la ruta
- **WHEN** un usuario no autenticado navega a una ruta protegida (e.g., `/dashboard`)
- **THEN** el router navega a `/login` y tras un login exitoso redirige a `/dashboard`

#### Scenario: Con sesión pero sin permiso muestra 403
- **WHEN** un usuario autenticado navega a una ruta que requiere un permiso que no posee
- **THEN** se renderiza la pantalla de error 403 (acceso denegado) sin mostrar el contenido de la ruta

#### Scenario: Con sesión y permiso correcto renderiza el contenido
- **WHEN** un usuario autenticado navega a una ruta y posee el permiso requerido
- **THEN** se renderiza el componente de la ruta normalmente

### Requirement: Layout raíz con menú adaptado a permisos
El sistema SHALL proveer un layout raíz que rodea todas las rutas protegidas. El menú de navegación SHALL mostrar solo los links a las secciones para las cuales el usuario posee al menos un permiso relevante.

#### Scenario: Links del menú reflejan los permisos de la sesión
- **WHEN** un usuario con rol PROFESOR inicia sesión
- **THEN** el menú muestra las secciones de su rol (comisiones, atrasados) pero NO las de FINANZAS ni ADMIN

#### Scenario: Menu se actualiza si la sesión cambia
- **WHEN** el access token se renueva y los permisos del usuario cambian
- **THEN** el menú refleja los nuevos permisos en la siguiente navegación

### Requirement: Logout explícito
El sistema SHALL proveer una acción de logout que llame a `POST /api/auth/logout` en el backend, limpie los tokens del almacenamiento local y redirija a `/login`.

#### Scenario: Logout limpia sesión y redirige
- **WHEN** el usuario activa la acción de logout
- **THEN** se llama al endpoint de logout, se eliminan los tokens locales, el `AuthContext` queda vacío y el router navega a `/login`

#### Scenario: Logout con red caída igual limpia sesión local
- **WHEN** el usuario activa logout y el request al backend falla (red caída)
- **THEN** los tokens locales se eliminan de todas formas y el usuario llega a `/login` (best-effort cleanup)
