## ADDED Requirements

### Requirement: Perfil de Usuario con PII cifrada

El sistema SHALL mantener el perfil de cada persona del tenant como una extensión de la entidad de identidad `user`, con los atributos de negocio: `nombre`, `apellidos`, `dni`, `cuil`, `cbu`, `alias_cbu`, `banco`, `regional`, `legajo`, `legajo_profesional`, `facturador` (booleano) y `estado` (Activo/Inactivo). Los atributos `dni`, `cuil`, `cbu` y `alias_cbu` MUST almacenarse cifrados en reposo con AES-256-GCM y NUNCA exponerse en texto plano en logs. El `legajo` es un atributo de negocio opcional; NUNCA es credencial ni selector de sesión (la identidad es el UUID interno).

#### Scenario: PII cifrada en reposo
- **WHEN** se crea o actualiza un usuario con `dni`, `cuil`, `cbu` o `alias_cbu`
- **THEN** el valor persistido en la columna correspondiente está cifrado (no es igual al texto plano) y puede descifrarse al valor original

#### Scenario: PII no aparece en logs
- **WHEN** se ejecuta cualquier operación de creación o lectura de usuario
- **THEN** los valores de `dni`, `cuil`, `cbu` y `alias_cbu` no aparecen en texto plano en ningún log estructurado

#### Scenario: Legajo no es credencial ni selector de sesión
- **WHEN** una petición intenta identificar al usuario por su `legajo` en un parámetro, body o header
- **THEN** el sistema ignora ese dato para la identidad; la identidad se deriva exclusivamente del JWT verificado

---

### Requirement: Unicidad de email por tenant

El sistema SHALL garantizar que el par `(tenant_id, email)` sea único. No pueden existir dos usuarios con el mismo email dentro del mismo tenant; el mismo email puede existir en tenants distintos.

#### Scenario: Email duplicado en el mismo tenant rechazado
- **WHEN** un ADMIN intenta crear un usuario con un `email` que ya existe en su tenant
- **THEN** el sistema retorna 409 Conflict y no crea el usuario

#### Scenario: Mismo email en tenant distinto permitido
- **WHEN** existe un usuario con email `x@y.com` en el tenant A y un ADMIN del tenant B crea un usuario con el mismo email
- **THEN** el sistema crea el usuario en el tenant B exitosamente

---

### Requirement: ABM administrativo de usuarios

El sistema SHALL permitir a usuarios con permiso `usuarios:gestionar` crear, leer, editar y eliminar (soft delete) usuarios del tenant a través de `/api/v1/usuarios`. El listado NO expone PII cifrada en texto plano; el detalle administrativo (`GET /{id}`) descifra y devuelve la PII solo a quien tiene el permiso de gestión. Eliminar un usuario es soft delete (nunca borrado físico).

#### Scenario: Crear usuario exitosamente
- **WHEN** un usuario con permiso `usuarios:gestionar` envía POST `/api/v1/usuarios` con `email`, `nombre`, `apellidos` y demás campos válidos
- **THEN** el sistema crea el usuario con `estado=Activo`, cifra la PII, y retorna 201 con el recurso creado (sin PII en claro en el cuerpo de listado)

#### Scenario: Listado no expone PII en claro
- **WHEN** un usuario con permiso `usuarios:gestionar` solicita GET `/api/v1/usuarios`
- **THEN** la respuesta lista los usuarios del tenant del autenticado sin incluir `dni`, `cuil`, `cbu` ni `alias_cbu` en texto plano

#### Scenario: Detalle administrativo descifra PII
- **WHEN** un usuario con permiso `usuarios:gestionar` solicita GET `/api/v1/usuarios/{id}` de un usuario de su tenant
- **THEN** la respuesta incluye los valores descifrados de `dni`, `cuil`, `cbu` y `alias_cbu`

#### Scenario: Acceso sin permiso rechazado
- **WHEN** un usuario sin permiso `usuarios:gestionar` intenta GET `/api/v1/usuarios`
- **THEN** el sistema retorna 403 Forbidden

#### Scenario: Editar usuario
- **WHEN** un usuario con permiso `usuarios:gestionar` envía PATCH `/api/v1/usuarios/{id}` con campos válidos (incluida PII)
- **THEN** el sistema actualiza solo los campos enviados, recifra la PII modificada, y retorna 200

#### Scenario: Soft delete de usuario
- **WHEN** un usuario con permiso `usuarios:gestionar` envía DELETE `/api/v1/usuarios/{id}`
- **THEN** el sistema setea `deleted_at`, retorna 204, y el usuario no aparece en listados subsiguientes

#### Scenario: Aislamiento multi-tenant
- **WHEN** un ADMIN del tenant A solicita GET `/api/v1/usuarios/{id}` de un usuario que pertenece al tenant B
- **THEN** el sistema retorna 404 Not Found (no revela datos de otro tenant)

---

### Requirement: Schemas con extra forbid

El sistema SHALL validar los DTO de request de usuarios con Pydantic v2 y `extra='forbid'`, rechazando campos no declarados.

#### Scenario: Campo no declarado rechazado
- **WHEN** una petición de creación de usuario incluye un campo no declarado en el schema
- **THEN** el sistema retorna 422 Unprocessable Entity
