## Context

El sistema ya cuenta con multi-tenancy row-level, RBAC fino (`modulo:accion`), soft-delete y audit-log (C-01 a C-05). El modelo de usuarios y asignaciones está completo (C-07): `Usuario` y `Asignacion` existen con sus tenant_id. El módulo de tareas internas es un nuevo dominio que depende únicamente de esos fundamentos. No hay cambios retrocompatibles sobre módulos existentes.

## Goals / Non-Goals

**Goals:**
- Modelo `Tarea` + `ComentarioTarea` con máquina de estados explícita.
- CRUD REST completo: alta, consulta propia, consulta global (admin), transición de estado, agregar comentario.
- Guard `tareas:gestionar` aplicado a todos los endpoints; vista global restringida a COORDINADOR/ADMIN.
- Row-level multi-tenancy en repositorio (todos los queries incluyen `tenant_id` por defecto).
- Tests TDD: safety-net → RED → GREEN → TRIANGULATE → REFACTOR. Cobertura ≥80% líneas, ≥90% reglas de negocio.

**Non-Goals:**
- Notificaciones push/email al asignado al recibir una tarea (pertenece a C-12/comunicaciones).
- Interfaz frontend (pertenece a C-23).
- Adjuntos o evidencias binarias en comentarios.
- Integración con Moodle.

## Decisions

### D1 — Máquina de estados como enum Python, transiciones validadas en el servicio

**Elección**: `EstadoTarea(str, Enum)` con valores `pendiente | en_progreso | resuelta | cancelada`. Las transiciones válidas se declaran como un dict en `tarea_service.py`:

```
TRANSICIONES = {
    "pendiente":    {"en_progreso", "cancelada"},
    "en_progreso":  {"resuelta", "cancelada", "pendiente"},
    "resuelta":     set(),
    "cancelada":    set(),
}
```

**Por qué no en el modelo SQLAlchemy**: mantener la lógica de transición en el service respeta la regla de no poner lógica de negocio en los modelos. El modelo es solo persistencia.

**Alternativa descartada**: usar PostgreSQL CHECK constraints para las transiciones — añade complejidad de migración sin ganancia real dado que la validación en el service ya garantiza integridad.

### D2 — `contexto_id` como UUID nullable sin FK foránea tipada

**Elección**: `contexto_id` es un UUID nullable sin constraint de FK. Puede referenciar cualquier entidad del dominio (alumno, comisión, entrega, etc.) sin acoplamiento de schema.

**Por qué**: agregar FKs tipadas requeriría una tabla de polimorfismo o múltiples columnas opcionales. La referencia libre es suficiente para la trazabilidad de contexto requerida en F8.1/F8.2.

**Riesgo aceptado**: no hay integridad referencial garantizada por la BD para `contexto_id`. El servicio puede validar la existencia si el contexto es relevante en el futuro.

### D3 — Paginación por offset/limit en el endpoint de admin

**Elección**: `GET /api/tareas?page=1&size=50&estado=&asignado_a=&materia_id=` con paginación offset. Consistente con el resto de endpoints de lista del sistema.

**Por qué**: keyset pagination agrega complejidad sin beneficio claro a las escalas previstas (cientos, no millones de tareas).

### D4 — ComentarioTarea como append-only, sin edición ni borrado

**Elección**: los comentarios son inmutables una vez creados (soft-delete deshabilitado para comentarios). El hilo es auditable.

**Por qué**: la trazabilidad del hilo es un requisito implícito de auditoría (todo en el sistema es append-only, alineado con la regla dura de soft-delete global). Editar un comentario rompe la narrativa del workflow.

## Risks / Trade-offs

- **[Riesgo] Alto throughput**: cientos de tareas simultáneas en período activo → **Mitigación**: índices en `(tenant_id, asignado_a, estado)` y `(tenant_id, asignado_por, estado)` para las queries más frecuentes. Sin caché de aplicación en esta fase.
- **[Trade-off] `contexto_id` sin tipo**: sacrifica integridad referencial por flexibilidad. Aceptable en esta fase; se puede tipar más adelante agregando `contexto_tipo: enum` si se necesita.
- **[Riesgo] Permiso `tareas:gestionar` aún no existe en la BD**: se crea en la migración. Si el seed de permisos ya fue ejecutado, hay que asegurarse de insertar el nuevo permiso de forma idempotente.

## Migration Plan

1. Alembic `016_tareas_internas`: crea tablas `tarea` y `comentario_tarea`, agrega índices, inserta permiso `tareas:gestionar` en la tabla de permisos de forma idempotente.
2. No hay datos existentes que migrar.
3. Rollback: `downgrade` elimina las tablas y el permiso.
