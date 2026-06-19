## ADDED Requirements

### Requirement: Crear programa de materia
El sistema SHALL permitir a un usuario con permiso `estructura:gestionar` registrar el programa oficial de una materia para una combinación específica de materia × carrera × cohorte, incluyendo un título y una referencia de archivo opaca (URL, path o ID externo).

#### Scenario: Registro exitoso de programa
- **WHEN** un usuario con `estructura:gestionar` envía título, `materia_id`, `carrera_id`, `cohorte_id` y `referencia_archivo` válidos
- **THEN** el sistema crea el registro `ProgramaMateria` y devuelve 201 con los datos creados, incluyendo `id` y `cargado_at`

#### Scenario: Unicidad por contexto académico
- **WHEN** ya existe un `ProgramaMateria` para el mismo `(tenant_id, materia_id, carrera_id, cohorte_id)` y se intenta crear otro
- **THEN** el sistema devuelve 409 Conflict

#### Scenario: Aislamiento de tenant
- **WHEN** un usuario del tenant B intenta acceder al programa de materia del tenant A
- **THEN** el sistema devuelve 404 Not Found

#### Scenario: Permiso insuficiente
- **WHEN** un usuario sin `estructura:gestionar` intenta crear un programa
- **THEN** el sistema devuelve 403 Forbidden

---

### Requirement: Consultar programa de materia
El sistema SHALL permitir a usuarios con `estructura:leer` consultar el programa de una materia por su contexto académico (materia × carrera × cohorte) o por su `id`.

#### Scenario: Consulta por contexto académico
- **WHEN** un usuario con `estructura:leer` consulta con `materia_id`, `carrera_id` y `cohorte_id` como query params
- **THEN** el sistema devuelve el programa correspondiente (o lista vacía si no existe)

#### Scenario: Consulta por id
- **WHEN** un usuario con `estructura:leer` realiza `GET /api/v1/programas/{id}`
- **THEN** el sistema devuelve el programa con ese `id` dentro del tenant

#### Scenario: Programa inexistente
- **WHEN** se consulta un `id` que no existe en el tenant
- **THEN** el sistema devuelve 404 Not Found

---

### Requirement: Actualizar programa de materia
El sistema SHALL permitir a un usuario con `estructura:gestionar` actualizar el `titulo` y/o `referencia_archivo` de un programa existente.

#### Scenario: Actualización exitosa
- **WHEN** un usuario con `estructura:gestionar` envía `PATCH /api/v1/programas/{id}` con campos válidos
- **THEN** el sistema actualiza solo los campos enviados y devuelve el recurso actualizado

#### Scenario: Campos no enviados no modificados
- **WHEN** el PATCH incluye solo `referencia_archivo`
- **THEN** el `titulo` permanece sin cambios

---

### Requirement: Eliminar programa de materia (soft delete)
El sistema SHALL marcar un `ProgramaMateria` como eliminado (soft delete) cuando un usuario con `estructura:gestionar` lo solicite.

#### Scenario: Soft delete exitoso
- **WHEN** un usuario con `estructura:gestionar` realiza `DELETE /api/v1/programas/{id}`
- **THEN** el sistema marca el registro como eliminado y devuelve 204; la consulta posterior por ese `id` devuelve 404
