## Context

C-13 agrega el módulo de encuentros sincrónicos y guardias. Los encuentros permiten a docentes planificar series de clases virtuales recurrentes y llevar registro de su realización (URL de grabación). Las guardias permiten a tutores registrar las atenciones cubiertas, con supervisión global de coordinación.

La arquitectura sigue el patrón establecido en el proyecto: Routers → Services → Repositories → Models. El módulo depende de `Asignacion` (C-07) para vincular slots y guardias al docente/tutor correcto en su contexto de materia.

## Goals / Non-Goals

**Goals:**
- Implementar `SlotEncuentro`, `InstanciaEncuentro` y `Guardia` con migración Alembic.
- Generación automática de instancias al crear un slot recurrente (RN-13).
- CRUD de instancias con edición granular por instancia (RN-14).
- Endpoint de bloque HTML para exportación al LMS.
- Vista admin transversal (tenant-scoped) para COORDINADOR/ADMIN.
- Registro de guardias por TUTOR; consulta global + export CSV para COORDINADOR/ADMIN.

**Non-Goals:**
- Frontend / UI (C-23).
- Integración automática con el LMS (el HTML se copia manualmente).
- Notificaciones push sobre encuentros.
- Coloquios o evaluaciones (C-14).

## Decisions

### D1 — Separación de SlotEncuentro e InstanciaEncuentro
**Decisión**: mantener slot e instancia como entidades separadas.  
**Rationale**: una instancia puede editarse sin tocar el slot ni las demás instancias de la misma serie (RN-14). Fusionar ambas entidades obligaría a duplicar datos o a gestionar deltas complejos.  
**Alternativa descartada**: un único modelo con campo `es_recurrente` + auto-join.

### D2 — Generación de instancias en el service, no en la DB
**Decisión**: la generación de instancias recurrentes se hace en `EncuentrosService.crear_slot()` con un loop Python que calcula las N fechas (fecha_inicio + n * 7 días) y hace `bulk_insert`.  
**Rationale**: más testeable (sin triggers de BD), portable entre motores, auditable.  
**Alternativa descartada**: stored procedure / trigger en PostgreSQL.

### D3 — Bloque HTML generado en el service (Jinja2)
**Decisión**: el endpoint `GET /api/encuentros/html-block` usa una plantilla Jinja2 embebida en el service para generar el HTML. No se guarda en base de datos.  
**Rationale**: el contenido es derivado de las instancias existentes; guardarlo duplicaría datos y requeriría sincronización.  
**Alternativa descartada**: retornar JSON y que el front renderice el HTML.

### D4 — Export de guardias como CSV en streaming
**Decisión**: `GET /api/guardias/export` usa `StreamingResponse` con `csv.writer` para no cargar todos los registros en memoria.  
**Rationale**: en tenants con muchas guardias la carga en memoria es innecesaria; streaming es el patrón ya usado en C-09 (export padrón).

### D5 — Permisos
| Permiso | Roles |
|---|---|
| `encuentros:gestionar` | PROFESOR, COORDINADOR, ADMIN |
| `encuentros:ver_admin` | COORDINADOR, ADMIN |
| `guardias:registrar` | TUTOR |
| `guardias:consultar` | TUTOR (propias), COORDINADOR, ADMIN (todas) |
| `guardias:exportar` | COORDINADOR, ADMIN |

## Risks / Trade-offs

- **[Riesgo] Generación masiva de instancias**: un slot con `cant_semanas = 200` generaría 200 filas en una sola request. Mitigación: validar `cant_semanas <= 52` (1 año) en el schema Pydantic.
- **[Riesgo] HTML injection en campos de texto** (titulo, comentario) al generar el bloque HTML. Mitigación: Jinja2 hace auto-escape por defecto; usar `{{ var }}` (no `{{ var | safe }}`).
- **[Trade-off] Instancias no se re-generan al editar el slot**: editar `cant_semanas` de un slot existente NO agrega ni quita instancias. Esto simplifica la implementación pero requiere eliminar y recrear el slot para corregir errores de configuración. Documentar en el spec.

## Migration Plan

1. Crear migración Alembic `013_slot_encuentro_instancia_guardia` con las tres tablas nuevas.
2. No hay datos pre-existentes que migrar.
3. Rollback: `downgrade` elimina las tres tablas (no hay dependencias en otras tablas existentes).

## Open Questions

- ¿El campo `horario` de `Guardia` es texto libre (ej. "14:00–14:45") o dos campos `hora_inicio`/`hora_fin`? → KB dice texto libre; se mantiene así para simplicidad.
- ¿`InstanciaEncuentro` tiene soft delete? → Sí, aplica la regla dura #13. Se agrega `deleted_at`.
