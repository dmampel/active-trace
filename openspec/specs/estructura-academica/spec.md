## ADDED Requirements

### Requirement: Gestión de Carreras
El sistema SHALL permitir a usuarios con permisos `estructura:*` crear, leer, editar y eliminar (soft delete) carreras del tenant. Cada carrera tiene un código único dentro del tenant. Una carrera inactiva no admite nuevas cohortes.

#### Scenario: Crear carrera exitosamente
- **WHEN** un usuario con permiso `estructura:crear` envía POST `/api/v1/estructura/carreras` con `codigo` y `nombre` válidos
- **THEN** el sistema crea la carrera con `estado=Activa` y retorna 201 con el recurso creado

#### Scenario: Código duplicado rechazado
- **WHEN** un usuario intenta crear una carrera con un `codigo` ya existente en el mismo tenant
- **THEN** el sistema retorna 409 Conflict

#### Scenario: Listar carreras filtra por tenant
- **WHEN** un usuario con permiso `estructura:leer` solicita GET `/api/v1/estructura/carreras`
- **THEN** el sistema retorna únicamente las carreras activas (no eliminadas) del tenant del usuario autenticado

#### Scenario: Editar carrera
- **WHEN** un usuario con permiso `estructura:editar` envía PATCH `/api/v1/estructura/carreras/{id}` con campos válidos
- **THEN** el sistema actualiza los campos enviados y retorna 200 con el recurso actualizado

#### Scenario: Eliminar carrera (soft delete)
- **WHEN** un usuario con permiso `estructura:eliminar` envía DELETE `/api/v1/estructura/carreras/{id}`
- **THEN** el sistema setea `deleted_at` y retorna 204; la carrera no aparece en listados subsiguientes

#### Scenario: Acceso sin permiso rechazado
- **WHEN** un usuario sin permiso `estructura:leer` intenta GET `/api/v1/estructura/carreras`
- **THEN** el sistema retorna 403 Forbidden

---

### Requirement: Gestión de Cohortes
El sistema SHALL permitir crear, leer, editar y eliminar (soft delete) cohortes. Cada cohorte pertenece a exactamente una carrera (`carrera_id` NOT NULL). El par `(tenant_id, carrera_id, nombre)` es único.

#### Scenario: Crear cohorte exitosamente
- **WHEN** un usuario con permiso `estructura:crear` envía POST `/api/v1/estructura/cohortes` con `carrera_id`, `nombre`, `anio` y `vig_desde` válidos
- **THEN** el sistema crea la cohorte con `estado=Activa` y retorna 201

#### Scenario: Nombre duplicado en misma carrera rechazado
- **WHEN** un usuario intenta crear una cohorte con `nombre` ya existente para el mismo `carrera_id` dentro del tenant
- **THEN** el sistema retorna 409 Conflict

#### Scenario: Carrera inexistente rechazada
- **WHEN** un usuario intenta crear una cohorte referenciando un `carrera_id` que no existe en el tenant
- **THEN** el sistema retorna 422 Unprocessable Entity

#### Scenario: Listar cohortes por carrera
- **WHEN** un usuario con permiso `estructura:leer` solicita GET `/api/v1/estructura/cohortes?carrera_id={id}`
- **THEN** el sistema retorna únicamente las cohortes activas de esa carrera dentro del tenant

#### Scenario: Soft delete de cohorte
- **WHEN** un usuario con permiso `estructura:eliminar` envía DELETE `/api/v1/estructura/cohortes/{id}`
- **THEN** el sistema setea `deleted_at` y retorna 204

---

### Requirement: Gestión de Materias
El sistema SHALL permitir crear, leer, editar y eliminar (soft delete) materias del catálogo curricular del tenant. El par `(tenant_id, codigo)` es único. La materia es el catálogo del plan de estudios; no representa una oferta concreta de cursado.

#### Scenario: Crear materia exitosamente
- **WHEN** un usuario con permiso `estructura:crear` envía POST `/api/v1/estructura/materias` con `codigo` y `nombre` válidos
- **THEN** el sistema crea la materia con `estado=Activa` y retorna 201

#### Scenario: Código duplicado rechazado
- **WHEN** un usuario intenta crear una materia con un `codigo` ya existente en el mismo tenant
- **THEN** el sistema retorna 409 Conflict

#### Scenario: Listar materias
- **WHEN** un usuario con permiso `estructura:leer` solicita GET `/api/v1/estructura/materias`
- **THEN** el sistema retorna todas las materias activas del tenant

#### Scenario: Obtener materia por id
- **WHEN** un usuario con permiso `estructura:leer` solicita GET `/api/v1/estructura/materias/{id}`
- **THEN** el sistema retorna la materia si pertenece al tenant del usuario, o 404 si no existe

#### Scenario: Soft delete de materia
- **WHEN** un usuario con permiso `estructura:eliminar` envía DELETE `/api/v1/estructura/materias/{id}`
- **THEN** el sistema setea `deleted_at` y retorna 204

---

### Requirement: Gestión de Instancias de Dictado
El sistema SHALL permitir crear, leer, editar y eliminar (soft delete) instancias de dictado. Una instancia representa la oferta concreta de una materia en una cohorte y período. El conjunto `(tenant_id, materia_id, cohorte_id, periodo)` es único. Padrón, calificaciones y encuentros se asociarán a la instancia.

#### Scenario: Crear instancia exitosamente
- **WHEN** un usuario con permiso `estructura:crear` envía POST `/api/v1/estructura/instancias` con `materia_id`, `cohorte_id`, `periodo` y `nombre` válidos
- **THEN** el sistema crea la instancia con `estado=Activa` y retorna 201

#### Scenario: Instancia duplicada rechazada
- **WHEN** un usuario intenta crear una instancia con la misma combinación `(materia_id, cohorte_id, periodo)` dentro del tenant
- **THEN** el sistema retorna 409 Conflict

#### Scenario: Materia o cohorte de otro tenant rechazada
- **WHEN** un usuario envía `materia_id` o `cohorte_id` que no pertenecen al tenant del usuario autenticado
- **THEN** el sistema retorna 422 Unprocessable Entity

#### Scenario: Listar instancias por cohorte
- **WHEN** un usuario con permiso `estructura:leer` solicita GET `/api/v1/estructura/instancias?cohorte_id={id}`
- **THEN** el sistema retorna las instancias activas de esa cohorte dentro del tenant

#### Scenario: Soft delete de instancia
- **WHEN** un usuario con permiso `estructura:eliminar` envía DELETE `/api/v1/estructura/instancias/{id}`
- **THEN** el sistema setea `deleted_at` y retorna 204

---

### Requirement: Permisos RBAC para estructura académica
El sistema SHALL registrar los permisos `estructura:leer`, `estructura:crear`, `estructura:editar` y `estructura:eliminar`. ADMIN recibe los cuatro; COORDINADOR recibe `leer`, `crear` y `editar`; PROFESOR y TUTOR reciben solo `leer`.

#### Scenario: ADMIN puede crear carrera
- **WHEN** un usuario con rol ADMIN intenta crear una carrera
- **THEN** el sistema permite la acción (tiene `estructura:crear`)

#### Scenario: PROFESOR no puede crear carrera
- **WHEN** un usuario con rol PROFESOR intenta crear una carrera
- **THEN** el sistema retorna 403 Forbidden (no tiene `estructura:crear`)

#### Scenario: COORDINADOR puede editar pero no eliminar
- **WHEN** un usuario con rol COORDINADOR intenta PATCH sobre una carrera
- **THEN** el sistema permite la acción (tiene `estructura:editar`)

#### Scenario: COORDINADOR no puede eliminar
- **WHEN** un usuario con rol COORDINADOR intenta DELETE sobre una carrera
- **THEN** el sistema retorna 403 Forbidden (no tiene `estructura:eliminar`)

---

### Requirement: Auditoría de operaciones de escritura
El sistema SHALL registrar en el AuditLog cada operación de creación, edición y eliminación sobre Carrera, Cohorte, Materia e InstanciaDictado.

#### Scenario: Crear carrera genera entrada de auditoría
- **WHEN** un usuario crea una carrera exitosamente
- **THEN** el sistema registra una entrada en AuditLog con `accion=ESTRUCTURA_CARRERA_CREAR` y `actor_id` del usuario autenticado

#### Scenario: Eliminar instancia genera entrada de auditoría
- **WHEN** un usuario elimina una instancia de dictado
- **THEN** el sistema registra una entrada en AuditLog con `accion=ESTRUCTURA_INSTANCIA_ELIMINAR`
