## Why

El sistema ya gestiona estructura académica (carreras, cohortes, materias, instancias de dictado) pero carece de dos capacidades de calendario y documentación curricular que los actores coordinadores y docentes necesitan para operar un cuatrimestre: el programa oficial de cada materia y las fechas de evaluaciones (parciales, TPs, coloquios). Sin esto, la coordinación gestiona estos datos fuera del sistema, rompiendo la trazabilidad y la capacidad de generar contenido para el aula virtual del LMS.

## What Changes

- Nuevo modelo `ProgramaMateria`: asocia un documento (referencia de archivo opaca) a una combinación materia × carrera × cohorte, con título y timestamp de carga.
- Nuevo modelo `FechaAcademica`: calendariza instancias evaluativas (Parcial / TP / Coloquio / Recuperatorio) por materia × cohorte × tipo × número dentro de un período.
- API `/api/v1/programas` — upload de archivo + asociación y consulta por materia/carrera/cohorte. Permiso `estructura:gestionar`.
- API `/api/v1/fechas-academicas` — CRUD completo con listado tabular y calendario, más endpoint de generación de fragmento LMS. Permiso `estructura:gestionar` (escritura) / `estructura:leer` (lectura).
- Migración Alembic `017_programas_fechas_academicas`: tablas `programa_materia` y `fecha_academica`.
- Cobertura de tests: CRUD completo, unicidad por materia×carrera×cohorte (programa), unicidad por materia×cohorte×tipo×número×periodo (fecha), aislamiento de tenant, generación de fragmento LMS.

## Capabilities

### New Capabilities

- `programas-materias`: Gestión del programa oficial de cada materia (upload, asociación materia×carrera×cohorte, consulta por contexto académico).
- `fechas-academicas`: Calendarización y CRUD de instancias evaluativas (parciales, TPs, coloquios, recuperatorios) con vista tabular, calendario y generación de fragmento LMS.

### Modified Capabilities

_(ninguna — no cambian requerimientos de specs existentes)_

## Impact

- **Nuevas tablas**: `programa_materia`, `fecha_academica` (ambas con `tenant_id`, soft delete).
- **Nuevos routers**: `backend/api/v1/programas.py`, `backend/api/v1/fechas_academicas.py`.
- **Nuevos repositories/services**: `ProgramaMateriaRepository`, `FechaAcademicaRepository`, sus services correspondientes.
- **Dependencias**: requiere `C-06 estructura-academica` (modelos `Materia`, `Carrera`, `Cohorte`, `InstanciaDictado` ya presentes).
- **Sin dependencia de C-14**: `FechaAcademica` (E15) es entidad independiente, no confundir con `Evaluacion` (E13) de C-14 — son modelos distintos con propósitos distintos (calendarización vs. gestión de evaluaciones con reservas).
