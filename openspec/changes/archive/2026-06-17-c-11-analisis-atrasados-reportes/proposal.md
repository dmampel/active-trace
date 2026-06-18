## Why

Con C-10 implementado, el sistema ya tiene las calificaciones importadas y el umbral configurado por docente. El siguiente paso del flujo central (FL-02, pasos 5–6) es exponer el análisis académico: detectar atrasados, ordenarlos por rendimiento, mostrar reportes rápidos y exportar trabajos pendientes de corrección. Sin C-11, el flujo del PROFESOR no puede derivar valor de los datos importados.

## What Changes

- Cómputo de **alumnos atrasados** (RN-06): alumnos con actividades faltantes o nota inferior al umbral configurado.
- **Ranking** de actividades aprobadas por alumno, filtrado a quienes tienen al menos una aprobada (RN-09).
- **Reportes rápidos** por materia: métricas consolidadas (total alumnos, aprobados, tasa de aprobación por actividad).
- **Notas finales agrupadas**: suma ponderada de las actividades seleccionadas por docente, lista para exportar.
- **Detección de TPs sin corregir** (F2.6, RN-07, RN-08): solo actividades textuales finalizadas sin nota.
- **Export CSV** del listado de atrasados y de TPs sin corregir.
- **Monitor general** (F2.7): vista transversal de todos los alumnos del tenant con filtros por materia, comisión, estado de actividad.
- **Monitor tutor/profesor** (F2.8): restringido a los alumnos del usuario autenticado; filtros por alumno, comisión, actividad, mínimo de actividades cumplidas.
- **Monitor coordinación/admin** (F2.9): extiende F2.8 con filtro de rango de fechas.
- Endpoints `GET /api/analisis/*` con guard `atrasados:ver`. Sin nuevas tablas — toda la lógica opera sobre `calificacion`, `umbral_materia` y `entrada_padron`.
- Registro de auditoría `ANALISIS_ATRASADOS_VER` en accesos al monitor general.

## Capabilities

### New Capabilities

- `analisis-atrasados`: cómputo de alumnos atrasados, ranking de actividades aprobadas, reportes rápidos por materia, notas finales agrupadas, detección y exportación de TPs sin corregir, monitores de seguimiento por rol (tutor/profesor/coordinación/admin).

### Modified Capabilities

_(ninguna — C-11 no modifica requisitos de calificaciones, umbral ni padrón; solo consume esos datos)_

## Impact

- **Backend — nuevos módulos**: `routers/analisis.py`, `services/analisis_service.py`, `repositories/analisis_repository.py`, `schemas/analisis.py`.
- **Backend — domain puro**: `domain/atrasados.py` (función pura de cómputo — sin dependencias de infraestructura).
- **Sin migraciones**: no hay nuevas tablas ni columnas. Toda la lógica es de lectura sobre modelos existentes.
- **Dependencias**: `Calificacion`, `UmbralMateria`, `EntradaPadron` (C-09, C-10). `Asignacion` para resolver el scope docente (C-07).
- **Permisos nuevos**: `atrasados:ver` para acceder a cualquier endpoint de análisis.
- **Auditoria**: `ANALISIS_ATRASADOS_VER` al consultar el monitor general (F9.2).
