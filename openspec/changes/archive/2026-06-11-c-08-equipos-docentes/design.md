## Context

C-07 entregó el modelo `Asignacion` y los endpoints CRUD individuales en `/api/v1/asignaciones`. El modelo ya tiene los campos necesarios (`usuario_id`, `rol`, `materia_id`, `carrera_id`, `cohorte_id`, `desde`, `hasta`, `responsable_id`). C-08 construye operaciones colectivas sobre ese cimiento: vista propia del docente, asignación masiva, clonar equipo entre cohortes, ajustar vigencia en bloque y exportar el plantel.

No hay cambios de esquema de base de datos. El campo `comisiones: JSON` en `Asignacion` es un placeholder documentado — se resuelve en un change posterior.

## Goals / Non-Goals

**Goals:**
- Endpoint `GET /api/v1/equipos/mis-asignaciones` — vista propia del docente autenticado con filtros.
- Endpoint `POST /api/v1/equipos/masiva` — asignación en bloque con búsqueda asistida de usuarios.
- Endpoint `POST /api/v1/equipos/clonar` — duplica equipo origen → destino, respetando RN-12.
- Endpoint `PATCH /api/v1/equipos/vigencia` — actualiza `desde`/`hasta` de todas las asignaciones de un equipo.
- Endpoint `GET /api/v1/equipos/exportar` — descarga CSV del equipo activo del tenant.
- Endpoint `GET /api/v1/equipos/usuarios/buscar` — autocompletado de usuarios para la asignación masiva (RN-30).

**Non-Goals:**
- Frontend (C-23).
- Gestión de comisiones como entidad propia (change posterior).
- Lógica de liquidaciones sobre el equipo (C-18).

## Decisions

### D-1: Nuevo router `equipos` separado de `asignaciones`

`asignaciones` gestiona registros individuales; `equipos` opera sobre conjuntos. Mezclarlos haría el router difícil de razonar y de permisar. Un router propio permite permisos distintos (`equipos:read_own`, `equipos:manage`, `equipos:export`) sin contaminar `asignaciones`.

Alternativa descartada: añadir los endpoints en `/asignaciones/bulk`, `/asignaciones/clone`, etc. — crece en tamaño y los permisos quedan enredados.

### D-2: Bulk insert via `insert_all` + audit batch

Para la asignación masiva y el clonar, se usa `session.execute(insert(Asignacion).values([...]))` en un solo statement, seguido de un único evento de auditoría de tipo `ASIGNACION_MASIVA_CREAR` (o `ASIGNACION_CLONAR`) con metadatos agregados (count, destino). Emitir un evento por fila sería N+1 en auditoría.

### D-3: Clonar = query + insert, no update

Clonar lee todas las asignaciones activas del equipo origen (sin deleted), construye nuevos registros con `cohorte_id` (y opcionalmente `materia_id`/`carrera_id`) del destino, y hace bulk insert. Las asignaciones origen no se modifican — el histórico queda intacto (RN-12, append-only).

Duplicados (mismo usuario+rol+contexto ya existe en destino): se omiten silenciosamente y se reportan en el response (`omitidos: N`).

### D-4: Export via StreamingResponse CSV

`GET /api/v1/equipos/exportar` usa `StreamingResponse` con un generador que escribe filas CSV a medida que lee el cursor. Evita cargar todo el dataset en memoria. Content-Type: `text/csv`, Content-Disposition: `attachment; filename="equipo.csv"`.

Alternativa descartada: XLSX en memoria — requiere openpyxl y un buffer completo; innecesario para el volumen esperado.

### D-5: Autocompletado de usuarios = endpoint dedicado con ILIKE

`GET /api/v1/equipos/usuarios/buscar?q=<term>&limit=20` busca en `User` por `nombre ILIKE` o `apellido ILIKE` dentro del tenant. Retorna id + nombre + apellido + legajo. El cliente React llama en debounce desde el formulario de asignación masiva.

Alternativa descartada: buscar en el frontend sobre la lista completa de usuarios — en tenants grandes puede ser >1000 registros; no escala.

## Risks / Trade-offs

- [Bulk insert + FK constraints] Si algún `usuario_id` o contexto no pertenece al tenant, el INSERT falla a nivel DB con integridad referencial. Mitigación: validar todos los IDs contra el tenant ANTES del bulk insert en el Service; retornar 422 con detalle.
- [Clonar sin filtro de activos] Si se clonan asignaciones vencidas por error, el equipo destino queda sucio. Mitigación: la operación de clonar filtra solo `asignaciones no eliminadas con hasta IS NULL o hasta >= hoy`.
- [Export sin paginación] Un tenant grande con muchas asignaciones puede generar un CSV lento. Mitigación: StreamingResponse + cursor; aceptable para la escala actual. Si escala, se añade filtro de fecha o paginación en un change posterior.
