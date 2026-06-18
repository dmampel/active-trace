## Context

El módulo de coloquios cubre el ciclo de evaluación formal (FL-07): COORDINADOR/PROF crea una convocatoria con turnos y cupos; ALUMNOs reservan; el resultado queda registrado. Comparte el patrón de Clean Architecture ya establecido (Router → Service → Repository → Model) y el row-level multi-tenancy obligatorio en cada tabla.

Entidades nuevas: `Evaluacion`, `ReservaEvaluacion`, `ResultadoEvaluacion`, `FechaAcademica`. No hay entidades existentes que se modifiquen.

## Goals / Non-Goals

**Goals:**
- CRUD completo de convocatorias (Evaluacion) con cupos por turno.
- Reserva atómica de turno por ALUMNO: restar cupo sin race condition.
- Registro de resultados (nota_final) por alumno y evaluación.
- Calendarización de fechas académicas (FechaAcademica) independiente del flujo de reserva.
- Panel de métricas: convocados, reservas activas, cupos libres, notas registradas.
- Importación de alumnos habilitados a una convocatoria (lista de alumno_ids).

**Non-Goals:**
- Frontend: cubierto en C-23.
- Notificaciones por email al alumno al reservar: no está en KB.
- Workflow de aprobación de reservas: el cupo es la única restricción.

## Decisions

### D1 — Control de cupo con UPDATE atómico

**Decisión**: la reserva decrementa cupos con `UPDATE evaluacion SET cupos_libres = cupos_libres - 1 WHERE id = :id AND cupos_libres > 0 RETURNING id`. Si no hay filas retornadas → HTTP 409 Conflict.

**Alternativa descartada**: leer cupo y luego actualizar en dos queries. Introduce race condition bajo carga concurrente.

**Rationale**: un solo roundtrip, sin lock explícito, suficiente para la escala esperada (decenas de reservas simultáneas).

### D2 — `Evaluacion.dias_disponibles` como campo denormalizado de cupos

**Decisión**: la entidad `Evaluacion` guarda `cupos_por_dia` (JSONB: `{fecha: cupos_libres}`) para representar múltiples turnos dentro de una convocatoria. Esto refleja el modelo de negocio: una convocatoria puede tener varios días con cupos distintos.

**Alternativa descartada**: tabla separada `TurnoEvaluacion`. Añade join innecesario para el caso de uso central (reservar un turno).

**Rationale**: el JSONB es consultable y actualizable de forma atómica con `jsonb_set`. La complejidad es baja; si el modelo crece se puede normalizar.

### D3 — `FechaAcademica` como módulo separado al de reservas

**Decisión**: `FechaAcademica` (calendarización de parciales/TPs/coloquios por materia × cohorte) tiene su propio router `/api/fechas-academicas` y service desacoplado de coloquios.

**Rationale**: F5.4 y FL-07 son flujos independientes. La FechaAcademica es un registro informativo; la Evaluacion con reservas es operativa.

### D4 — Permisos RBAC nuevos

| Permiso | Roles |
|---------|-------|
| `coloquios:gestionar` | COORDINADOR, ADMIN |
| `coloquios:ver` | COORDINADOR, ADMIN, PROFESOR |
| `coloquios:reservar` | ALUMNO |
| `fechas_academicas:gestionar` | COORDINADOR, ADMIN |
| `fechas_academicas:ver` | todos los roles |

### D5 — Importación de alumnos habilitados

**Decisión**: endpoint `POST /api/coloquios/{id}/alumnos` recibe lista de alumno_ids y hace upsert en una tabla asociativa `evaluacion_alumno` (alumno habilitado para la convocatoria). El panel de métricas calcula `convocados` como `COUNT(evaluacion_alumno)`.

**Alternativa descartada**: ligar directamente a VersionPadron. Demasiado acoplamiento; las convocatorias pueden incluir subsets del padrón.

## Risks / Trade-offs

- [Race condition en reserva] → Mitigado con UPDATE atómico (D1). Verificar en test de carga si se requiere.
- [JSONB para cupos] → Si el tenant necesita audit trail de cambios de cupo por día, JSONB dificulta el tracking. Mitigation: AuditLog registra la acción completa.
- [Un sola migración para 4 tablas] → Regla del proyecto. Si falla en prod, rollback de la migración entera.

## Migration Plan

1. Ejecutar migración Alembic: crea `evaluacion`, `evaluacion_alumno`, `reserva_evaluacion`, `resultado_evaluacion`, `fecha_academica`.
2. Registrar permisos nuevos en seed de RBAC (mismo patrón de C-04).
3. Rollback: `alembic downgrade -1`.
