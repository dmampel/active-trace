## 1. Migración Alembic

- [x] 1.1 Crear migración `013_slot_encuentro_instancia_guardia` con tablas `slot_encuentro`, `instancia_encuentro`, `guardia`
- [x] 1.2 Agregar enums: `DiaSemana`, `EstadoInstanciaEncuentro`, `EstadoGuardia` en la migración
- [x] 1.3 Verificar que `upgrade()` y `downgrade()` ejecutan sin errores contra la DB de test

## 2. Modelos SQLAlchemy

- [x] 2.1 Crear modelo `SlotEncuentro` en `backend/app/models/encuentro.py` con todos los campos de E9 y soft delete (`deleted_at`)
- [x] 2.2 Crear modelo `InstanciaEncuentro` en el mismo archivo con campos de E10, FK a `SlotEncuentro` nullable, soft delete
- [x] 2.3 Crear modelo `Guardia` en `backend/app/models/guardia.py` con campos de E11 y soft delete
- [x] 2.4 Registrar los tres modelos en `backend/app/models/__init__.py`
- [x] 2.5 Verificar que `alembic check` no detecta diferencias entre modelos y migración

## 3. Schemas Pydantic

- [x] 3.1 Crear `SlotEncuentroCreate` con validador que exige exactamente uno de `cant_semanas > 0` o `fecha_unica` (excluyentes); `cant_semanas <= 52`
- [x] 3.2 Crear `SlotEncuentroResponse` con lista anidada de `InstanciaEncuentroResponse`
- [x] 3.3 Crear `InstanciaEncuentroUpdate` con campos opcionales: `estado`, `meet_url`, `video_url`, `comentario`
- [x] 3.4 Crear `InstanciaEncuentroResponse`
- [x] 3.5 Crear `GuardiaCreate` con campos de E11; validar que `horario` no esté vacío
- [x] 3.6 Crear `GuardiaResponse`
- [x] 3.7 Crear `GuardiaFilter` (query params: `materia_id`, `estado`, `desde`, `hasta`) para listado y export
- [x] 3.8 Todos los schemas con `model_config = ConfigDict(extra='forbid')`

## 4. Repositorios

- [x] 4.1 Crear `SlotEncuentroRepository` con `create`, `get_by_id`, `list_by_asignacion`, `list_all_tenant` — todos con scope de `tenant_id`
- [x] 4.2 Crear `InstanciaEncuentroRepository` con `bulk_create`, `get_by_id`, `update`, `list_by_slot`, `list_all_tenant`
- [x] 4.3 Crear `GuardiaRepository` con `create`, `get_by_id`, `list_by_asignacion`, `list_all_tenant` con filtros opcionales (`materia_id`, `estado`, rango fechas)
- [x] 4.4 Verificar que ningún query omite el filtro `tenant_id`

## 5. Servicios

- [x] 5.1 Crear `EncuentrosService.crear_slot()`: aplica RN-13 — si `cant_semanas > 0` genera N instancias con fechas espaciadas 7 días; si `fecha_unica` genera 1 instancia
- [x] 5.2 Crear `EncuentrosService.editar_instancia()`: aplica RN-14 — edita solo los campos provistos sin tocar el slot ni otras instancias
- [x] 5.3 Crear `EncuentrosService.listar_slots_propios()`: retorna slots del usuario autenticado (por `asignacion_id`)
- [x] 5.4 Crear `EncuentrosService.listar_admin()`: retorna todas las instancias del tenant para COORDINADOR/ADMIN
- [x] 5.5 Crear `EncuentrosService.generar_html_block()`: usa plantilla Jinja2 con auto-escape para generar tabla HTML con encuentros; realizados muestran `video_url` como link
- [x] 5.6 Crear `GuardiaService.registrar()`: crea guardia asociando `asignacion_id` desde la sesión JWT, nunca del body
- [x] 5.7 Crear `GuardiaService.listar()`: TUTOR filtra por su `asignacion_id`; COORDINADOR/ADMIN obtiene todas del tenant con filtros opcionales
- [x] 5.8 Crear `GuardiaService.exportar_csv()`: retorna generador de filas CSV (para `StreamingResponse`)

## 6. Routers

- [x] 6.1 Crear `backend/app/routers/encuentros.py` con:
  - `POST /api/encuentros/slots` — permiso `encuentros:gestionar`
  - `GET /api/encuentros/slots` — permiso `encuentros:gestionar`
  - `PATCH /api/encuentros/instancias/{id}` — permiso `encuentros:gestionar`
  - `GET /api/encuentros/admin` — permiso `encuentros:ver_admin`
  - `GET /api/encuentros/html-block` — permiso `encuentros:gestionar`
- [x] 6.2 Crear `backend/app/routers/guardias.py` con:
  - `POST /api/guardias` — permiso `guardias:registrar`
  - `GET /api/guardias` — permiso `guardias:consultar`
  - `GET /api/guardias/export` — permiso `guardias:exportar`; retorna `StreamingResponse` con `Content-Type: text/csv`
- [x] 6.3 Registrar ambos routers en `backend/app/main.py`
- [x] 6.4 Agregar los permisos nuevos (`encuentros:gestionar`, `encuentros:ver_admin`, `guardias:registrar`, `guardias:consultar`, `guardias:exportar`) a la seed de roles en el script de fixtures o en el módulo RBAC

## 7. Tests — Encuentros

- [x] 7.1 Safety net: correr suite completa, capturar baseline N tests passing
- [x] 7.2 Test: `crear_slot_recurrente` genera exactamente N instancias con fechas correctas
- [x] 7.3 Test: `crear_slot_recurrente` con `cant_semanas = 53` → HTTP 422
- [x] 7.4 Test: `crear_encuentro_unico` genera exactamente 1 instancia
- [x] 7.5 Test: `fecha_unica` y `cant_semanas > 0` simultáneos → HTTP 422
- [x] 7.6 Test: `editar_instancia` solo modifica la instancia objetivo, las demás del slot quedan intactas
- [x] 7.7 Test: editar instancia de otro tenant → HTTP 404
- [x] 7.8 Test: ALUMNO `POST /api/encuentros/slots` → HTTP 403
- [x] 7.9 Test: PROFESOR `GET /api/encuentros/admin` → HTTP 403
- [x] 7.10 Test: HTML block escapa caracteres especiales en título (`<script>`)
- [x] 7.11 Test: HTML block incluye link al video en encuentros `Realizado` con `video_url`
- [x] 7.12 Test: aislamiento tenant — slots de tenant B no visibles para usuario de tenant A

## 8. Tests — Guardias

- [x] 8.1 Test: TUTOR registra guardia → HTTP 201; `asignacion_id` tomada de JWT, no del body
- [x] 8.2 Test: PROFESOR intenta `POST /api/guardias` → HTTP 403
- [x] 8.3 Test: TUTOR `GET /api/guardias` → solo sus propias guardias
- [x] 8.4 Test: COORDINADOR `GET /api/guardias` → todas las guardias del tenant
- [x] 8.5 Test: filtro por `materia_id` retorna solo guardias de esa materia
- [x] 8.6 Test: TUTOR `GET /api/guardias/export` → HTTP 403
- [x] 8.7 Test: COORDINADOR `GET /api/guardias/export` → CSV con headers correctos
- [x] 8.8 Test: aislamiento tenant en guardias — guardias de tenant B no visibles para usuario de tenant A
