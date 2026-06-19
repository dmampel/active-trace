## Context

El sistema no tiene tablón de avisos. Coordinadores y admins publican novedades institucionales hoy de forma externa (email masivo, grupos de WhatsApp), sin control de audiencia, sin ventana de vigencia y sin evidencia de recepción. C-15 introduce el módulo de avisos con segmentación de audiencia (Global / PorMateria / PorCohorte / PorRol), ventana temporal de visibilidad y confirmación explícita de lectura (acknowledgment).

Depende de C-06 (estructura-academica: Materia, Cohorte) y C-04 (rbac: guard `avisos:publicar`).

## Goals / Non-Goals

**Goals:**
- CRUD de avisos protegido por `avisos:publicar` (COORDINADOR / ADMIN).
- Feed de "mis avisos" para cualquier usuario autenticado, filtrado por su rol, alcance y cohorte, dentro de la ventana de vigencia.
- Endpoint de ACK: el usuario confirma lectura; el aviso deja de aparecer en el feed del usuario si `requiere_ack = true`.
- Contadores de vistas y confirmaciones derivados de `AcknowledgmentAviso` (sin denormalizar).
- Migración 015 limpia, sin downtime.

**Non-Goals:**
- Push notifications o websockets en tiempo real.
- Avisos dirigidos a un usuario individual específico (eso es mensajería interna, C-20).
- Adjuntos ni multimedia en el cuerpo del aviso.
- Feed público sin autenticación.

## Decisions

### D1 — Alcance y audiencia como campos directos en `Aviso`

**Decisión**: `alcance` (enum), `materia_id` (nullable), `cohorte_id` (nullable), `rol_destino` (nullable) viven en la misma tabla `aviso`, no en una tabla de "segmentos" separada.

**Alternativa descartada**: tabla N-N `aviso_audiencia` con un registro por segmento. Agrega join y complejidad para un dominio con pocas combinaciones. El esquema flat es más simple de filtrar y de indexar.

**Por qué**: el 90% de los avisos tiene un único segmento de audiencia (global o por cohorte). La flexibilidad de N-N no justifica el overhead en este dominio.

### D2 — Filtrado de "mis avisos" en capa de repositorio

**Decisión**: el repositorio aplica todos los filtros de audiencia y vigencia en una sola query con expresiones `OR` anidadas:

```sql
WHERE tenant_id = :tid
  AND activo = true
  AND inicio_en <= NOW() AND (fin_en IS NULL OR fin_en >= NOW())
  AND (
    alcance = 'Global'
    OR (alcance = 'PorRol' AND rol_destino = :rol_usuario)
    OR (alcance = 'PorMateria' AND materia_id IN (:mis_materias))
    OR (alcance = 'PorCohorte' AND cohorte_id IN (:mis_cohortes))
  )
ORDER BY orden ASC, inicio_en DESC
```

El servicio inyecta `mis_materias` y `mis_cohortes` resolviendo las asignaciones activas del usuario desde el contexto de sesión.

**Alternativa descartada**: filtrar en Python post-query. Costoso para volúmenes de cientos de avisos y no escala.

### D3 — Contadores derivados, sin denormalización

**Decisión**: `total_vistas` y `total_acks` se computan con `COUNT` sobre `AcknowledgmentAviso` en la query de detalle, nunca se almacenan como columnas en `aviso`.

**Por qué**: los avisos son de bajo volumen (decenas por tenant). Una agregación simple en DB es suficiente y evita inconsistencias por race conditions de update.

### D4 — ACK idempotente

**Decisión**: `POST /api/avisos/{id}/ack` es idempotente. Si el usuario ya confirmó, devuelve 200 sin error. La constraint unique en `(aviso_id, usuario_id)` protege a nivel DB.

### D5 — Soft delete / desactivación

**Decisión**: se usa el flag `activo = false` para "archivar" un aviso (no `deleted_at`). El modelo sigue la convención de soft delete del sistema (`deleted_at` en otras entidades), pero Aviso usa `activo` como semántica de publicación. El `deleted_at` global del sistema se aplica igual para baja real; `activo` controla visibilidad editorial.

## Risks / Trade-offs

- [Riesgo] Feed lento si un usuario tiene muchas asignaciones (muchos `materia_id`) → Mitigación: limitar la IN-list en el filtro a un máximo razonable (ej: 50 materias) y agregar índice compuesto `(tenant_id, alcance, activo, inicio_en)`.
- [Riesgo] Aviso con `rol_destino = NULL` puede interpretarse como "todos los roles" o "ningún rol" → Mitigación: la spec define explícitamente que `rol_destino = NULL` significa "todos los roles" cuando `alcance = Global` o `alcance = PorCohorte`; `PorRol` siempre requiere `rol_destino != NULL` (validado en schema Pydantic).
- [Trade-off] No hay websocket: el feed se actualiza solo al refrescar la página. Aceptable para la fase actual; websockets se añaden en C-20 o posterior.

## Migration Plan

1. Migración 015: `CREATE TABLE aviso (…); CREATE TABLE acknowledgment_aviso (…); CREATE UNIQUE INDEX uix_ack ON acknowledgment_aviso(aviso_id, usuario_id);`
2. Sin cambios destructivos a tablas existentes → rollback = `DROP TABLE acknowledgment_aviso; DROP TABLE aviso;`.
3. No requiere backfill.
