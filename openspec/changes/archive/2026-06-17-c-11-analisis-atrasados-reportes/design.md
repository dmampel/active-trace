## Context

C-10 dejó disponibles `Calificacion` (nota numérica o textual por alumno × actividad), `UmbralMateria` (umbral_pct + valores_aprobatorios por asignación docente) y `EntradaPadron` (alumno del padrón con email cifrado). C-11 es la capa de análisis que opera sobre esos datos: no escribe nada, solo lee y computa.

El flujo central del PROFESOR (FL-02, pasos 5–6) depende de esta capa para mostrar atrasados, ranking y reportes. La función pura de derivación de `aprobado` ya existe en `domain/aprobado.py` (C-10); C-11 la reutiliza y agrega nuevas funciones puras de análisis en `domain/atrasados.py`.

## Goals / Non-Goals

**Goals:**

- Proveer endpoints de lectura para atrasados, ranking, reportes rápidos, notas finales y TPs sin corregir.
- Separar claramente el cómputo (domain puro) de la consulta (repository) y la orquestación (service).
- Respetar el scope de aislamiento: PROFESOR solo ve sus alumnos (su `asignacion_id`); COORDINADOR/ADMIN ven el tenant completo.
- Sin migraciones — solo lectura de tablas existentes.

**Non-Goals:**

- Persistir el estado de "atrasado" en una tabla (evita estado inconsistente con datos variables).
- Enviar comunicaciones (eso es C-12).
- Frontend (eso es C-22).
- Lógica de calificación manual (C-10).

## Decisions

### D1 — Dominio puro en `domain/atrasados.py`

Toda la lógica de cómputo vive en funciones puras sin I/O:

- `es_atrasado(calificaciones, umbral_pct, valores_aprobatorios) → bool` (RN-06)
- `calcular_ranking(alumnos_calificaciones, ...) → list[RankingItem]` (RN-09)
- `calcular_notas_finales(alumnos_calificaciones, actividades_seleccionadas) → list[NotaFinal]`
- `detectar_tp_sin_corregir(calificaciones_textuales, finalizaciones) → list[TpPendiente]` (RN-07, RN-08)

**Alternativa rechazada**: lógica en el repository con SQL complejo → mezcla capas, dificulta testing, acumula deuda.

### D2 — Repository solo agrega datos crudos

`AnalisisRepository` ejecuta las consultas de agregación (JOIN calificacion + entrada_padron + umbral_materia) y devuelve DTOs internos simples. El service pasa esos DTOs a las funciones de dominio.

Esto preserva la regla "Nunca lógica de negocio en Repositories".

### D3 — Scope con `asignacion_id` como pivot

El scope del PROFESOR se resuelve desde la sesión → `usuario_id` → `Asignacion` activa para la materia pedida → `asignacion_id`. El repository filtra por `(tenant_id, asignacion_id)`.

COORDINADOR/ADMIN reciben `materia_id` (+ `tenant_id`) y no se restringe por `asignacion_id`, por lo que ven todos los alumnos de esa materia en el tenant.

**Por qué `asignacion_id` y no `usuario_id` directamente**: un PROFESOR puede tener múltiples asignaciones activas en una misma materia (distintas cohortes). El umbral también está anclado a `asignacion_id`, así que es el scope natural.

### D4 — Export CSV en streaming

Los endpoints de exportación devuelven `StreamingResponse` con `text/csv`. No se genera un archivo temporal en disco. El nombre del archivo incluye materia_id y fecha UTC.

### D5 — Permiso único `atrasados:ver`

Un solo permiso cubre todos los endpoints de análisis. La distinción de scope (solo mis alumnos vs. todo el tenant) se resuelve en el service según el rol, no con permisos separados. Esto simplifica la matriz de permisos y es coherente con el patrón establecido en C-07/C-08.

### D6 — Finalizaciones como payload del cliente en detección de TPs

La detección de TPs sin corregir (F2.6) requiere cruzar calificaciones con el reporte de finalización del LMS. Ese reporte se sube al endpoint como archivo (POST multipart). El service hace el cruce en memoria: no persiste las finalizaciones (son input de una sola operación, sin valor histórico). Esto evita una tabla nueva y simplifica el modelo.

## Risks / Trade-offs

- **Volumen de calificaciones**: para tenants con muchos alumnos × actividades, el JOIN puede ser costoso. Mitigación: índice compuesto `(tenant_id, materia_id)` ya existe en `calificacion` (C-10); agregar índice en `(tenant_id, asignacion_id)` para el scope del PROFESOR.
- **Finalizaciones en memoria**: si el CSV de finalización es muy grande, puede presionar la RAM del worker. Mitigación: leer el CSV en streaming con `csv.reader`; no cargarlo completo en una lista.
- **`atrasado` no persiste**: si el cliente pide el estado de atrasado frecuentemente (p. ej. polling), el cómputo se repite. Mitigación: la respuesta del endpoint tiene un `Cache-Control: no-store` explícito (datos académicos deben ser siempre frescos). Si el rendimiento es problema futuro, se puede agregar caché TTL corta, pero eso es C-12 o posterior.

## Open Questions

- _(ninguna — el dominio es suficientemente claro para arrancar la implementación)_
