## ADDED Requirements

### Requirement: Crear fecha académica
El sistema SHALL permitir a un usuario con `estructura:gestionar` registrar una instancia evaluativa (parcial, TP, coloquio, recuperatorio) para una materia y cohorte dentro de un período, con número de instancia, fecha y título descriptivo.

#### Scenario: Registro exitoso de fecha académica
- **WHEN** un usuario con `estructura:gestionar` envía `materia_id`, `cohorte_id`, `tipo` (Parcial|TP|Coloquio|Recuperatorio), `numero`, `periodo`, `fecha` y `titulo` válidos
- **THEN** el sistema crea el registro `FechaAcademica` y devuelve 201 con los datos creados

#### Scenario: Unicidad por instancia evaluativa
- **WHEN** ya existe una `FechaAcademica` para el mismo `(tenant_id, materia_id, cohorte_id, tipo, numero, periodo)` y se intenta crear otro
- **THEN** el sistema devuelve 409 Conflict

#### Scenario: Tipo de evaluación inválido
- **WHEN** se envía un `tipo` fuera del enum permitido
- **THEN** el sistema devuelve 422 Unprocessable Entity

#### Scenario: Aislamiento de tenant
- **WHEN** un usuario del tenant B intenta acceder a fechas académicas del tenant A
- **THEN** el sistema devuelve resultados vacíos o 404 según corresponda

#### Scenario: Permiso insuficiente
- **WHEN** un usuario sin `estructura:gestionar` intenta crear una fecha académica
- **THEN** el sistema devuelve 403 Forbidden

---

### Requirement: Listar fechas académicas
El sistema SHALL permitir a usuarios con `estructura:leer` listar las fechas académicas filtradas por materia, cohorte y/o período.

#### Scenario: Listado filtrado por materia y cohorte
- **WHEN** un usuario con `estructura:leer` consulta `GET /api/v1/fechas-academicas?materia_id=&cohorte_id=`
- **THEN** el sistema devuelve todas las fechas académicas del tenant para ese contexto, ordenadas por fecha ascendente

#### Scenario: Listado filtrado por período
- **WHEN** se agrega `periodo` como query param
- **THEN** el sistema devuelve solo las fechas del período indicado

#### Scenario: Sin resultados
- **WHEN** no hay fechas académicas para los filtros indicados
- **THEN** el sistema devuelve lista vacía (200)

---

### Requirement: Actualizar fecha académica
El sistema SHALL permitir a un usuario con `estructura:gestionar` actualizar campos de una `FechaAcademica` existente (`fecha`, `titulo`, `tipo`, `numero`, `periodo`).

#### Scenario: Actualización exitosa de fecha
- **WHEN** un usuario con `estructura:gestionar` envía `PATCH /api/v1/fechas-academicas/{id}` con una nueva `fecha`
- **THEN** el sistema actualiza solo el campo enviado y devuelve el recurso actualizado

#### Scenario: Actualización genera conflicto de unicidad
- **WHEN** la actualización produciría un duplicado de la clave única `(tenant_id, materia_id, cohorte_id, tipo, numero, periodo)`
- **THEN** el sistema devuelve 409 Conflict

---

### Requirement: Eliminar fecha académica (soft delete)
El sistema SHALL marcar una `FechaAcademica` como eliminada (soft delete) cuando un usuario con `estructura:gestionar` lo solicite.

#### Scenario: Soft delete exitoso
- **WHEN** un usuario con `estructura:gestionar` realiza `DELETE /api/v1/fechas-academicas/{id}`
- **THEN** el sistema marca el registro como eliminado y devuelve 204; la consulta posterior por ese `id` devuelve 404

---

### Requirement: Generar fragmento de contenido para LMS
El sistema SHALL generar un fragmento de texto formateado con las fechas evaluativas de una materia y cohorte en un período, listo para publicar en el aula virtual del LMS.

#### Scenario: Generación exitosa del fragmento
- **WHEN** un usuario con `estructura:leer` consulta `GET /api/v1/fechas-academicas/lms-fragment` con `materia_id`, `cohorte_id` y `periodo`
- **THEN** el sistema devuelve un texto (Markdown) con las fechas listadas ordenadas cronológicamente, incluyendo tipo, número, título y fecha

#### Scenario: Sin fechas en el período
- **WHEN** no hay `FechaAcademica` para el contexto y período indicados
- **THEN** el sistema devuelve un fragmento vacío o con mensaje indicando que no hay fechas registradas
