## Context

El sistema ya tiene `Materia`, `Carrera`, `Cohorte` e `InstanciaDictado` (C-06). C-17 agrega las dos entidades de documentación y calendario académico que dependen de esa estructura: `ProgramaMateria` (E16) y `FechaAcademica` (E15). Ambas son CRUD puro de governance BAJO — no tienen lógica de negocio compleja ni impacto en seguridad. La única consideración no trivial es la gestión del archivo del programa (sin servicio de storage dedicado aún) y la generación del fragmento LMS para fechas.

El modelo de `FechaAcademica` (E15) es independiente del de `Evaluacion` (E13, C-14). `Evaluacion` gestiona instancias evaluativas con reservas de alumnos y resultados; `FechaAcademica` es puramente un calendario de fechas asociado a materia×cohorte×tipo×número, sin workflow ni reservas.

## Goals / Non-Goals

**Goals:**
- CRUD completo de `ProgramaMateria` con `referencia_archivo` opaca (sin upload real a storage — solo se guarda la referencia).
- CRUD completo de `FechaAcademica` con listado tabular y calendario.
- Endpoint de generación de fragmento de contenido LMS (texto formateado con las fechas).
- Aislamiento de tenant estricto en ambas entidades.
- Tests: unicidad por contexto académico, aislamiento, casos feliz + borde por entidad.

**Non-Goals:**
- Implementar un servicio de almacenamiento de archivos real (S3, minio, etc.) — `referencia_archivo` es un texto opaco.
- Vista de calendario frontend (es responsabilidad de C-22/C-23).
- Integración directa con el LMS para publicar el fragmento — el endpoint solo genera el texto.
- Lógica de vigencia de fechas académicas más allá del campo `periodo`.

## Decisions

### D1 — `referencia_archivo` como texto opaco

**Decisión**: `referencia_archivo` en `ProgramaMateria` es un campo `texto` libre que el cliente puede poblar con cualquier URL, path o ID de archivo.

**Alternativa considerada**: modelar un servicio de upload real (S3/minio) con un endpoint dedicado.

**Rationale**: C-17 tiene governance BAJO y no está en el camino crítico de ningún servicio de almacenamiento. El campo opaco permite que el cliente use cualquier backend externo (Google Drive, SharePoint, Moodle Files) sin acoplamiento. El upload real se puede agregar en un change posterior sin migración de schema.

---

### D2 — `FechaAcademica` independiente de `Evaluacion`

**Decisión**: `FechaAcademica` es una entidad propia (E15), no una extensión de `Evaluacion` (E13).

**Rationale**: `Evaluacion` (C-14) tiene un workflow de reservas y resultados por alumno. `FechaAcademica` es solo un calendario de fechas del cuatrimestre — sin alumnos asociados, sin resultados, sin reservas. Mezclarlos acoplaría dos dominios con ciclos de vida distintos.

---

### D3 — Unicidad por contexto académico

**Decisión**: 
- `ProgramaMateria`: unicidad `(tenant_id, materia_id, carrera_id, cohorte_id)` — un programa por contexto.
- `FechaAcademica`: unicidad `(tenant_id, materia_id, cohorte_id, tipo, numero, periodo)` — una fecha por instancia evaluativa.

**Rationale**: refleja la semántica del dominio. Si necesitan cambiar el programa de una materia en una cohorte, actualizan el registro existente (o lo reemplazan). Duplicados generarían ambigüedad en la vista de calendario y en la generación del fragmento LMS.

---

### D4 — Generación del fragmento LMS como endpoint sincrónico

**Decisión**: `GET /api/v1/fechas-academicas/lms-fragment?materia_id=&cohorte_id=&periodo=` devuelve un string formateado con las fechas del período.

**Rationale**: no hay razón para hacerlo asincrónico (es una consulta + formato). El resultado es texto plano formateado (Markdown o HTML simple), listo para copiar y pegar en el aula virtual del LMS.

---

### D5 — Permisos

- **Escritura** (crear/editar/eliminar): `estructura:gestionar` — COORDINADOR, ADMIN.
- **Lectura**: `estructura:leer` — TUTOR, PROFESOR, COORDINADOR, ADMIN.

Consistente con C-06 (estructura académica).

## Risks / Trade-offs

- **[Riesgo] `referencia_archivo` sin validación de URL** → Mitigation: el campo es opaco por decisión (D1). Validar que sea un texto no vacío es suficiente; la responsabilidad de la URL válida es del cliente.
- **[Riesgo] `FechaAcademica` duplica semánticamente `Evaluacion.FechaHora`** → Mitigation: son entidades con propósitos distintos (D2). Documentar claramente en el código y en la KB la diferencia de uso.
- **[Trade-off] Sin paginación en el listado de fechas académicas** → Para un cuatrimestre, el volumen es acotado (decenas de fechas por materia×cohorte). Se puede agregar paginación en un change posterior si escala.

## Migration Plan

1. `alembic upgrade head` crea las tablas `programa_materia` y `fecha_academica` (migration `017`).
2. No hay datos previos — sin seed ni backfill necesario.
3. Rollback: `alembic downgrade -1` elimina ambas tablas (sin dependencias en tablas existentes).

## Open Questions

_(ninguna — governance BAJO, dominio bien definido en KB)_
