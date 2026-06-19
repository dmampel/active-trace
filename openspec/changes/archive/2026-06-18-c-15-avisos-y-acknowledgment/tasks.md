## 1. Migración DB

- [x] 1.1 Crear migración Alembic `015_avisos_acknowledgment` con tabla `aviso` (id, tenant_id, alcance, materia_id nullable, cohorte_id nullable, rol_destino nullable, severidad, titulo, cuerpo, inicio_en, fin_en, orden, activo, requiere_ack, deleted_at)
- [x] 1.2 Agregar tabla `acknowledgment_aviso` (id, aviso_id FK→aviso, usuario_id FK→usuario, confirmado_at) con unique index `uix_ack_aviso_usuario (aviso_id, usuario_id)`
- [x] 1.3 Verificar que `alembic upgrade head` aplica la migración sin errores en la DB de test

## 2. Modelos SQLAlchemy

- [x] 2.1 Crear `backend/app/models/aviso.py` con clase `Aviso` (columnas según migración, enums `AlcanceAviso` y `SeveridadAviso`)
- [x] 2.2 Crear clase `AcknowledgmentAviso` en el mismo archivo con relación `aviso → acknowledgments`
- [x] 2.3 Registrar ambos modelos en `backend/app/models/__init__.py`

## 3. Schemas Pydantic

- [x] 3.1 Crear `backend/app/schemas/aviso.py` con `AvisoCreate` (todos los campos requeridos + validaciones: PorMateria exige materia_id, PorCohorte exige cohorte_id, PorRol exige rol_destino)
- [x] 3.2 Crear `AvisoUpdate` (todos los campos opcionales, mismas validaciones cross-field)
- [x] 3.3 Crear `AvisoResponse` (incluye `total_vistas: int` y `total_acks: int` derivados)
- [x] 3.4 Crear `AvisoFeedItem` (vista del destinatario: sin contadores, con flag `ya_confirmado: bool`)
- [x] 3.5 Todos los schemas con `model_config = ConfigDict(extra='forbid')`

## 4. Repositorio

- [x] 4.1 Crear `backend/app/repositories/aviso_repository.py` con método `create(aviso_data, tenant_id) → Aviso`
- [x] 4.2 Implementar `get_by_id(aviso_id, tenant_id) → Aviso | None` (filtra por tenant; raise 404 si no existe)
- [x] 4.3 Implementar `list_all(tenant_id) → list[Aviso]` (todos, incluyendo inactivos y vencidos; ordenados por orden ASC)
- [x] 4.4 Implementar `update(aviso_id, tenant_id, data) → Aviso`
- [x] 4.5 Implementar `soft_delete(aviso_id, tenant_id)` (marca deleted_at)
- [x] 4.6 Implementar `get_feed(tenant_id, rol_usuario, materias_ids, cohortes_ids, usuario_id) → list[Aviso]` con filtro de alcance y ventana de vigencia (query SQL directa, sin filtrado en Python)
- [x] 4.7 Implementar `upsert_ack(aviso_id, usuario_id, tenant_id) → AcknowledgmentAviso` (idempotente: INSERT OR IGNORE vía ON CONFLICT DO NOTHING)
- [x] 4.8 Implementar `count_acks(aviso_id) → int` para los contadores derivados

## 5. Servicio

- [x] 5.1 Crear `backend/app/services/aviso_service.py` con método `create_aviso(data, current_user) → AvisoResponse`
- [x] 5.2 Implementar `get_aviso(aviso_id, current_user) → AvisoResponse` (con contadores derivados)
- [x] 5.3 Implementar `list_avisos(current_user) → list[AvisoResponse]`
- [x] 5.4 Implementar `update_aviso(aviso_id, data, current_user) → AvisoResponse`
- [x] 5.5 Implementar `delete_aviso(aviso_id, current_user)`
- [x] 5.6 Implementar `get_mis_avisos(current_user) → list[AvisoFeedItem]` resolviendo asignaciones activas del usuario para inyectar `materias_ids` y `cohortes_ids` al repositorio; excluir avisos con `requiere_ack=true` ya confirmados por el usuario
- [x] 5.7 Implementar `confirm_ack(aviso_id, current_user) → None` (valida que el aviso existe en el tenant, luego upsert_ack)

## 6. Router

- [x] 6.1 Crear `backend/app/routers/avisos.py` con rutas: `POST /`, `GET /`, `GET /{id}`, `PATCH /{id}`, `DELETE /{id}` — todas con `require_permission("avisos:publicar")`
- [x] 6.2 Agregar ruta `GET /mis-avisos` sin restricción de permiso especial (cualquier usuario autenticado)
- [x] 6.3 Agregar ruta `POST /{id}/ack` sin restricción de permiso especial (cualquier usuario autenticado)
- [x] 6.4 Registrar el router en `backend/app/main.py` con prefix `/api/avisos`

## 7. Permisos RBAC

- [x] 7.1 Verificar que el permiso `avisos:publicar` existe en el seed/catálogo de permisos y está asignado a COORDINADOR y ADMIN
- [x] 7.2 Si no existe, agregarlo en el módulo de seed de permisos (ver patrón de C-04/C-07)

## 8. Tests

- [x] 8.1 Crear `backend/tests/test_avisos.py` con fixture que inserta un tenant, usuario COORDINADOR, usuario ALUMNO y usuario PROFESOR con asignaciones en materias y cohortes distintas
- [x] 8.2 Test: COORDINADOR crea aviso global → 201
- [x] 8.3 Test: COORDINADOR crea aviso PorCohorte sin cohorte_id → 422
- [x] 8.4 Test: COORDINADOR crea aviso PorRol sin rol_destino → 422
- [x] 8.5 Test: PROFESOR intenta crear aviso → 403
- [x] 8.6 Test: listar avisos (COORDINADOR) incluye inactivos y vencidos
- [x] 8.7 Test: feed mis-avisos excluye aviso con fin_en < NOW()
- [x] 8.8 Test: feed mis-avisos excluye aviso inactivo (activo=false)
- [x] 8.9 Test: aviso Global aparece para todos los roles en el feed
- [x] 8.10 Test: aviso PorRol=PROFESOR no aparece en feed de TUTOR
- [x] 8.11 Test: aviso PorCohorte=A no aparece para usuario de cohorte B
- [x] 8.12 Test: feed ordenado por orden ASC
- [x] 8.13 Test: ALUMNO confirma ack de aviso con requiere_ack=true → 200, aviso desaparece del feed
- [x] 8.14 Test: ACK idempotente — segundo POST /ack no falla ni duplica registro
- [x] 8.15 Test: aviso con requiere_ack=false sigue en feed tras confirmar
- [x] 8.16 Test: contador total_acks = 3 tras 3 usuarios distintos confirmar
- [x] 8.17 Test: contador no cambia por ack idempotente (sigue en 1)
- [x] 8.18 Test: POST /ack en aviso de otro tenant → 404
- [x] 8.19 Test: soft delete → aviso no aparece en feed ni en listado de gestión
