## 1. Migración y modelo

- [x] 1.1 Crear modelo SQLAlchemy `Comunicacion` en `backend/app/models/comunicacion.py`: `id`, `tenant_id`, `enviado_por`, `materia_id`, `destinatario` (cifrado), `asunto`, `cuerpo`, `estado` (enum), `lote_id`, `enviado_at`, `aprobado_at`, `created_at`, `deleted_at` (soft delete); índices en `(tenant_id, estado)`, `(tenant_id, lote_id)`
- [x] 1.2 Agregar `requiere_aprobacion: bool = False` al modelo `Tenant` (si no existe) con migración separada o inline
- [x] 1.3 Crear migración Alembic `0014_comunicacion.py`: tabla `comunicacion` con todos los campos; verificar que `destinatario` es TEXT (el cifrado es app-level)
- [x] 1.4 Crear enum Python `EstadoComunicacion` con valores `Pendiente | Enviando | Enviado | Error | Cancelado`

## 2. Schemas Pydantic v2

- [x] 2.1 Crear `ComunicacionPreviewRequest`: `asunto: str`, `cuerpo: str`, `contexto: dict` (variables de sustitución)
- [x] 2.2 Crear `ComunicacionPreviewResponse`: `asunto_renderizado: str`, `cuerpo_renderizado: str`, `warnings: list[str]`
- [x] 2.3 Crear `ComunicacionEnviarRequest`: `destinatarios: list[str]` (emails), `asunto: str`, `cuerpo: str`, `materia_id: UUID`, `lote_descripcion: str | None`; validar `len(destinatarios) >= 1`
- [x] 2.4 Crear `ComunicacionEnviarResponse`: `lote_id: UUID | None`, `ids_encolados: list[UUID]`, `total: int`
- [x] 2.5 Crear `ComunicacionResponse`: todos los campos excepto `destinatario` raw → campo `destinatario_masked: str`
- [x] 2.6 Crear `LoteAccionRequest` (vacío — la acción la define el endpoint) y `LoteAccionResponse`: `lote_id`, `afectados: int`, `estado_nuevo: str`
- [x] 2.7 Todos los schemas con `model_config = ConfigDict(extra='forbid')`

## 3. Repository

- [x] 3.1 Crear `ComunicacionRepository` en `backend/app/repositories/comunicacion_repository.py` con `create()`, `get_by_id()`, `list_by_tenant()` (filtros: estado, lote_id, materia_id, rango fechas), `update_estado()`, `get_pendientes_para_worker()` (estado=Pendiente, aprobado_at IS NOT NULL o tenant.requiere_aprobacion=False), `reset_enviando_huerfanos()`
- [x] 3.2 Todos los métodos reciben `tenant_id: UUID` como primer argumento y aplican filtro tenant-scope por defecto
- [x] 3.3 `destinatario` se cifra en `create()` (usando `cipher.encrypt()`) y se descifra en lectura interna solo cuando lo necesita el worker (`get_pendientes_para_worker()` devuelve el email descifrado en un campo separado)

## 4. Service

- [x] 4.1 Crear `ComunicacionService` con `preview(request, context) -> PreviewResponse`: resuelve variables `{{...}}` con `str.format_map`; registra variables no resueltas en `warnings`
- [x] 4.2 Implementar `encolar(request, usuario_id, tenant_id) -> EnviarResponse`: genera `lote_id` si N>1, persiste N registros en estado Pendiente, audit log `COMUNICACION_ENVIAR` (queda pendiente de confirmación — el audit real se genera al llegar a Enviado en el worker)
- [x] 4.3 Implementar `aprobar_lote(lote_id, tenant_id, aprobador_id) -> LoteAccionResponse`: actualiza `aprobado_at` en todos los Pendiente del lote
- [x] 4.4 Implementar `cancelar_lote(lote_id, tenant_id, usuario_id) -> LoteAccionResponse`: transiciona a Cancelado todos los Pendiente del lote
- [x] 4.5 Implementar `cancelar_individual(comunicacion_id, tenant_id, usuario_id) -> ComunicacionResponse`: valida estado=Pendiente; retorna 422 si no
- [x] 4.6 Implementar `listar(tenant_id, filtros) -> list[ComunicacionResponse]`: delega a repository; enmascara `destinatario` en respuesta
- [x] 4.7 Ningún método del service accede directamente a la DB — siempre vía repository

## 5. Router

- [x] 5.1 Crear `backend/app/routers/comunicaciones.py` con `prefix="/api/v1/comunicaciones"`, `tags=["comunicaciones"]`
- [x] 5.2 `POST /preview` — guard `comunicacion:enviar`; llama `service.preview()`; no requiere persistencia
- [x] 5.3 `POST /enviar` — guard `comunicacion:enviar`; llama `service.encolar()`; retorna `EnviarResponse`
- [x] 5.4 `POST /lotes/{lote_id}/aprobar` — guard `comunicacion:aprobar`; llama `service.aprobar_lote()`
- [x] 5.5 `POST /lotes/{lote_id}/cancelar` — guard `comunicacion:aprobar`; llama `service.cancelar_lote()`
- [x] 5.6 `POST /{comunicacion_id}/cancelar` — guard `comunicacion:enviar`; llama `service.cancelar_individual()`
- [x] 5.7 `GET /` — guard `comunicacion:ver`; query params `estado`, `lote_id`, `materia_id`, `desde`, `hasta`; retorna `list[ComunicacionResponse]`
- [x] 5.8 Registrar router en `backend/app/main.py`

## 6. Worker asíncrono

- [x] 6.1 Crear `backend/app/workers/comunicacion_worker.py` con función `async def run_worker(db_session_factory, smtp_client, poll_interval=10)`
- [x] 6.2 Al arrancar: llamar `repo.reset_enviando_huerfanos()` (mensajes en Enviando con `enviado_at IS NULL` y `created_at < now() - 5min` → Error)
- [x] 6.3 Loop principal: SELECT pendientes elegibles → para cada uno: UPDATE Enviando → SMTP send → UPDATE Enviado/Error; continuar con el siguiente aunque uno falle
- [x] 6.4 En estado Enviado: registrar audit log `COMUNICACION_ENVIAR` con `usuario_id=enviado_por`, `tenant_id`, `comunicacion_id`
- [x] 6.5 Crear `SmtpClient` stub/interface en `backend/app/workers/smtp_client.py`: método `async def send(to: str, subject: str, body: str) -> bool`; implementación real lee `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`
- [x] 6.6 Arrancar worker como `asyncio.create_task` en el `lifespan` de FastAPI (`main.py`)

## 7. Permisos y seed

- [x] 7.1 Insertar permisos `comunicacion:enviar`, `comunicacion:aprobar`, `comunicacion:ver` en la tabla `permiso` (seed en migración o fixture de datos)
- [x] 7.2 Asignar `comunicacion:enviar` a PROFESOR, COORDINADOR, ADMIN
- [x] 7.3 Asignar `comunicacion:aprobar` a COORDINADOR, ADMIN
- [x] 7.4 Asignar `comunicacion:ver` a PROFESOR (propias), COORDINADOR, ADMIN

## 8. Tests unitarios — service

- [x] 8.1 Safety net: correr tests existentes; capturar baseline antes de tocar código
- [x] 8.2 `test_preview_resuelve_variables`: preview con `{{alumno.nombre}}` → nombre real en respuesta
- [x] 8.3 `test_preview_warnings_variable_desconocida`: variable `{{foo.bar}}` → literal + entry en `warnings`
- [x] 8.4 `test_preview_no_persiste`: llamar preview → verificar 0 registros en DB
- [x] 8.5 `test_encolar_individual_crea_pendiente`: encolar 1 dest → 1 registro Pendiente, lote_id=None, destinatario cifrado
- [x] 8.6 `test_encolar_masivo_mismo_lote`: encolar 3 dest → 3 registros con mismo `lote_id`
- [x] 8.7 `test_encolar_sin_destinatarios_falla`: lista vacía → ValueError / 422
- [x] 8.8 `test_aprobar_lote_actualiza_aprobado_at`: aprobar lote → todos los Pendiente del lote tienen `aprobado_at IS NOT NULL`
- [x] 8.9 `test_cancelar_lote_transiciona_cancelado`: cancelar lote → todos Pendiente → Cancelado
- [x] 8.10 `test_cancelar_individual_pendiente_ok`: Pendiente → Cancelado
- [x] 8.11 `test_cancelar_individual_enviado_falla`: Enviado → 422

## 9. Tests unitarios — máquina de estados y worker

- [x] 9.1 `test_transicion_pendiente_enviando_valida`
- [x] 9.2 `test_transicion_enviando_enviado_valida`
- [x] 9.3 `test_transicion_enviando_error_valida`
- [x] 9.4 `test_transicion_inversa_rechazada`: intentar Enviado → Pendiente → raise
- [x] 9.5 `test_worker_despacha_pendiente_aprobado`: stub SMTP ok → mensaje queda en Enviado, `enviado_at` registrado
- [x] 9.6 `test_worker_smtp_falla_pasa_a_error`: stub SMTP lanza exception → mensaje queda en Error
- [x] 9.7 `test_worker_no_procesa_sin_aprobacion_cuando_requiere`: tenant con `requiere_aprobacion=True`, mensaje sin `aprobado_at` → worker lo omite
- [x] 9.8 `test_worker_reset_huerfanos_al_arrancar`: mensaje Enviando sin `enviado_at` viejo → worker lo resetea a Error al iniciar

## 10. Tests de API (router + integración)

- [x] 10.1 `test_preview_201_con_variables`: POST /preview con contexto → 200 con variables resueltas
- [x] 10.2 `test_enviar_sin_permiso_403`: usuario sin `comunicacion:enviar` → 403
- [x] 10.3 `test_enviar_individual_201`: POST /enviar → 201, 1 Comunicacion en DB
- [x] 10.4 `test_enviar_masivo_lote_generado`: POST /enviar 3 dest → 201, `lote_id` en respuesta, 3 registros en DB
- [x] 10.5 `test_aprobar_lote_sin_permiso_403`: usuario sin `comunicacion:aprobar` → 403
- [x] 10.6 `test_aprobar_lote_200`: POST /lotes/{id}/aprobar → 200, `aprobado_at` set en todos
- [x] 10.7 `test_cancelar_lote_200`: POST /lotes/{id}/cancelar → 200, todos Cancelado
- [x] 10.8 `test_cancelar_individual_ok`: POST /{id}/cancelar sobre Pendiente → 200 Cancelado
- [x] 10.9 `test_cancelar_individual_no_pendiente_422`: POST /{id}/cancelar sobre Enviado → 422
- [x] 10.10 `test_listado_scoped_por_tenant`: mensajes de tenant A no visibles desde tenant B
- [x] 10.11 `test_listado_destinatario_enmascarado`: campo `destinatario_masked` nunca expone email en claro
- [x] 10.12 `test_listado_filtro_estado`: ?estado=Pendiente → solo Pendiente
- [x] 10.13 `test_audit_log_en_envio`: después de que el worker despacha → AuditLog con `COMUNICACION_ENVIAR`
