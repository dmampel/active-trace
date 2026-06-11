## 1. Permisos RBAC

- [x] 1.1 Registrar permisos `equipos:read_own`, `equipos:manage`, `equipos:export` en la migración de datos de permisos (o en el seed de permisos del tenant, según el patrón existente de C-04)
- [x] 1.2 Asignar `equipos:read_own` a roles PROFESOR, TUTOR, NEXO, COORDINADOR en el catálogo de permisos por rol
- [x] 1.3 Asignar `equipos:manage` a roles COORDINADOR y ADMIN
- [x] 1.4 Asignar `equipos:export` a roles COORDINADOR y ADMIN

## 2. Schemas Pydantic (DTOs)

- [x] 2.1 Crear `backend/app/schemas/equipo.py` con `extra='forbid'` en todos los schemas
- [x] 2.2 `MisAsignacionesQuery` — query params: `estado_vigencia?`, `materia_id?`, `rol?`, `carrera_id?`, `cohorte_id?`
- [x] 2.3 `AsignacionDetalleResponse` — campos: `id`, `rol`, `materia` (nombre), `carrera` (nombre), `cohorte` (nombre), `desde`, `hasta`, `estado_vigencia`, `responsable_id?`
- [x] 2.4 `BuscarUsuariosQuery` — query params: `q` (str, min_length=2), `limit` (int, default=20, le=50)
- [x] 2.5 `UsuarioBusquedaResponse` — campos: `id`, `nombre`, `apellido`, `legajo`
- [x] 2.6 `AsignacionMasivaRequest` — campos: `usuario_ids: list[UUID]` (min 1), `materia_id?`, `carrera_id?`, `cohorte_id`, `rol`, `desde`, `hasta?`
- [x] 2.7 `AsignacionMasivaResponse` — campo: `creadas: int`
- [x] 2.8 `ClonarEquipoRequest` — campos: `origen` (cohorte_id, materia_id?, carrera_id?), `destino` (cohorte_id, materia_id?, carrera_id?)
- [x] 2.9 `ClonarEquipoResponse` — campos: `clonadas: int`, `omitidas: int`
- [x] 2.10 `VigenciaEquipoRequest` — campos: `cohorte_id`, `materia_id?`, `carrera_id?`, `desde?`, `hasta?` (al menos uno de los dos)
- [x] 2.11 `VigenciaEquipoResponse` — campo: `actualizadas: int`

## 3. Extensión de AsignacionRepository

- [x] 3.1 Extender `list()` con filtros adicionales: `carrera_id`, `cohorte_id`, `materia_id`, `rol` (todos opcionales, aplicados como AND si presentes)
- [x] 3.2 Agregar método `list_for_usuario(usuario_id, tenant_id, filters)` que aplica mismos filtros pero fija `usuario_id` — para mis-asignaciones
- [x] 3.3 Agregar método `bulk_create(tenant_id, items: list[dict]) -> int` usando `insert().values([...])`; retorna count de filas insertadas
- [x] 3.4 Agregar método `clone(tenant_id, origen: dict, destino: dict) -> tuple[int, int]` — query vigentes del origen, filtra duplicados en destino, bulk insert; retorna (clonadas, omitidas)
- [x] 3.5 Agregar método `bulk_update_vigencia(tenant_id, filtro: dict, desde?, hasta?) -> int` — UPDATE con WHERE por cohorte/materia/carrera del tenant; retorna count
- [x] 3.6 Agregar método `export_query(tenant_id)` — retorna AsyncIterator/cursor con join a User, Materia, Carrera, Cohorte para el CSV

## 4. EquipoService

- [x] 4.1 Crear `backend/app/services/equipo_service.py` con clase `EquipoService`
- [x] 4.2 Implementar `mis_asignaciones(usuario_id, tenant_id, filters)` — llama al repo y deriva estado_vigencia
- [x] 4.3 Implementar `buscar_usuarios(tenant_id, q, limit)` — query ILIKE en `nombre` y `apellido` del modelo `Usuario`
- [x] 4.4 Implementar `asignacion_masiva(tenant_id, data)` — valida todos los IDs de contexto contra el tenant, llama `bulk_create`, registra auditoría `ASIGNACION_MASIVA_CREAR`
- [x] 4.5 Implementar `clonar_equipo(tenant_id, data)` — valida origen ≠ destino y pertenencia al tenant, llama `clone`, registra auditoría `ASIGNACION_CLONAR`
- [x] 4.6 Implementar `actualizar_vigencia(tenant_id, data)` — valida que al menos `desde` o `hasta` esté presente, llama `bulk_update_vigencia`, registra auditoría `ASIGNACION_VIGENCIA_BULK`
- [x] 4.7 Implementar `exportar_csv(tenant_id)` — usa `export_query` y `csv.writer` con `StreamingResponse` generator

## 5. Router de Equipos

- [x] 5.1 Crear `backend/app/api/v1/routers/equipos.py` con `APIRouter(prefix="/equipos", tags=["equipos"])`
- [x] 5.2 `GET /mis-asignaciones` — permiso `equipos:read_own`, llama `EquipoService.mis_asignaciones`
- [x] 5.3 `GET /usuarios/buscar` — permiso `equipos:manage`, llama `EquipoService.buscar_usuarios`
- [x] 5.4 `POST /masiva` — permiso `equipos:manage`, llama `EquipoService.asignacion_masiva`, retorna 201
- [x] 5.5 `POST /clonar` — permiso `equipos:manage`, llama `EquipoService.clonar_equipo`, retorna 201
- [x] 5.6 `PATCH /vigencia` — permiso `equipos:manage`, llama `EquipoService.actualizar_vigencia`
- [x] 5.7 `GET /exportar` — permiso `equipos:export`, retorna `StreamingResponse` desde `EquipoService.exportar_csv`
- [x] 5.8 Registrar el router en `backend/app/api/v1/router.py` (o equivalente)

## 6. Extensión del router Asignaciones

- [x] 6.1 Extender `GET /api/v1/asignaciones` para aceptar query params adicionales: `carrera_id`, `cohorte_id`, `materia_id`, `rol` — pasarlos al `AsignacionRepository.list()`

## 7. Tests de integración

- [x] 7.1 `tests/test_equipos_mis_asignaciones.py` — safety net + test lista propia + filtros + lista vacía
- [x] 7.2 `tests/test_equipos_buscar_usuarios.py` — coincidencias ILIKE + sin coincidencias + sin permiso 403
- [x] 7.3 `tests/test_equipos_masiva.py` — creación exitosa + contexto otro tenant 422 + lista vacía 422
- [x] 7.4 `tests/test_equipos_clonar.py` — clonado exitoso + duplicados omitidos + origen = destino 422 + sin vigentes
- [x] 7.5 `tests/test_equipos_vigencia.py` — actualización exitosa + sin asignaciones retorna 0 + sin cambios 422
- [x] 7.6 `tests/test_equipos_exportar.py` — export CSV headers correctos + content-type + sin permiso 403
- [x] 7.7 `tests/test_asignaciones_filtros.py` — filtros nuevos (`carrera_id`, `cohorte_id`, `materia_id`, `rol`) en GET /asignaciones
- [x] 7.8 Correr suite completa y verificar ≥80% coverage, ≥90% reglas de negocio
