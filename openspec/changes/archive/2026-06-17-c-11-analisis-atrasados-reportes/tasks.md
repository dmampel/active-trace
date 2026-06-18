## 1. Permiso y schemas base

- [x] 1.1 Agregar permiso `atrasados:ver` a la matriz RBAC (roles: TUTOR, PROFESOR, COORDINADOR, ADMIN) en `app/core/permissions.py` o donde esté definida la matriz.
- [x] 1.2 Crear `app/schemas/analisis.py` con los schemas Pydantic v2 (`extra='forbid'`): `AtrasadoItem`, `AtrasadoResponse`, `RankingItem`, `RankingResponse`, `ReporteRapidoResponse`, `NotaFinalItem`, `NotaFinalResponse`, `TpPendienteItem`, `MonitorItem`, `MonitorResponse`.
- [x] 1.3 Tests unitarios de schemas: validar que campos requeridos son obligatorios y que `extra='forbid'` rechaza campos extra.

## 2. Dominio puro — `domain/atrasados.py`

- [x] 2.1 Implementar `es_atrasado(calificaciones: list[CalificacionDTO], actividades_seleccionadas: list[str], umbral_pct: int, valores_aprobatorios: list[str]) -> bool` (RN-06).
- [x] 2.2 Implementar `calcular_ranking(alumnos: list[AlumnoCalificacionesDTO], ...) -> list[RankingItem]` — excluir sin aprobadas (RN-09), ordenar desc.
- [x] 2.3 Implementar `calcular_notas_finales(alumnos: list[AlumnoCalificacionesDTO], actividades_seleccionadas: list[str]) -> list[NotaFinalItem]` — actividades faltantes valen 0.
- [x] 2.4 Implementar `detectar_tp_sin_corregir(calificaciones: list[CalificacionDTO], finalizaciones: list[FinalizacionDTO]) -> list[TpPendienteItem]` — solo escala textual (RN-07, RN-08).
- [x] 2.5 Tests unitarios `tests/domain/test_atrasados.py`: mínimo 2 casos por función (happy path + edge). Usar datos sintéticos; cero dependencias de DB.

## 3. Repository — `repositories/analisis_repository.py`

- [x] 3.1 Implementar `AnalisisRepository` con `get_calificaciones_por_asignacion(asignacion_id, materia_id, tenant_id)` → lista de `AlumnoCalificacionesDTO` (JOIN calificacion + entrada_padron filtrando por scope docente).
- [x] 3.2 Implementar `get_calificaciones_por_materia(materia_id, tenant_id, ...)` → lista de `AlumnoCalificacionesDTO` para scope coordinación/admin (sin restricción por asignacion_id).
- [x] 3.3 Implementar `get_umbral(asignacion_id, materia_id, tenant_id) -> UmbralDTO` — fallback a 60% si no existe.
- [x] 3.4 Tests de integración `tests/repositories/test_analisis_repository.py` con DB de test: insertar fixtures de `CalificacionFactory` + `EntradaPadronFactory`, verificar que los métodos retornan el scope correcto.

## 4. Service — `services/analisis_service.py`

- [x] 4.1 Implementar `AnalisisService.get_atrasados(materia_id, usuario_sesion, ...)` — resuelve scope (PROFESOR → asignacion_id; COORD/ADMIN → materia completa), llama repository, llama `es_atrasado` del dominio.
- [x] 4.2 Implementar `AnalisisService.get_ranking(materia_id, usuario_sesion)` — llama `calcular_ranking` del dominio.
- [x] 4.3 Implementar `AnalisisService.get_reporte_rapido(materia_id, usuario_sesion)` — métricas agregadas (total, atrasados, pct_aprobacion por actividad).
- [x] 4.4 Implementar `AnalisisService.get_notas_finales(materia_id, actividades, usuario_sesion)` — llama `calcular_notas_finales`.
- [x] 4.5 Implementar `AnalisisService.detectar_tp_sin_corregir(materia_id, archivo_finalizaciones, usuario_sesion)` — parsea CSV en streaming, cruza con calificaciones textuales (RN-08).
- [x] 4.6 Tests de integración `tests/services/test_analisis_service.py` con DB de test y fixtures reales: verificar scope isolation (PROFESOR A no ve alumnos de PROFESOR B con misma materia_id), atrasado detectado correctamente, ranking excluye sin aprobadas.

## 5. Monitor general y de seguimiento

- [x] 5.1 Implementar `AnalisisRepository.get_monitor_general(materia_id, tenant_id, filtros)` con filtros: comision, busqueda_libre, estado_actividad.
- [x] 5.2 Implementar `AnalisisRepository.get_monitor_seguimiento(asignacion_id, materia_id, tenant_id, filtros)` con filtros: alumno, comision, actividad, min_actividades_cumplidas.
- [x] 5.3 Agregar soporte de filtro `fecha_desde`/`fecha_hasta` en `get_monitor_seguimiento` para scope coordinación (F2.9) — filtra por `calificacion.importado_at`.
- [x] 5.4 Implementar `AnalisisService.get_monitor(materia_id, usuario_sesion, filtros)` — despacha a monitor_general o monitor_seguimiento según rol.
- [x] 5.5 Tests de integración del monitor: filtro por comision, filtro por busqueda libre, filtro de fechas, auditoría generada en monitor general.

## 6. Router — `routers/analisis.py`

- [x] 6.1 Crear `app/routers/analisis.py` con prefijo `/api/v1/analisis`. Guard `require_permission("atrasados:ver")` en todos los endpoints.
- [x] 6.2 `GET /atrasados?materia_id=&actividades=` → `AtrasadoResponse`.
- [x] 6.3 `GET /ranking?materia_id=` → `RankingResponse`.
- [x] 6.4 `GET /reporte?materia_id=` → `ReporteRapidoResponse`.
- [x] 6.5 `GET /notas-finales?materia_id=&actividades=` → `NotaFinalResponse`.
- [x] 6.6 `POST /tp-sin-corregir?materia_id=` (multipart, archivo CSV de finalización) → `list[TpPendienteItem]`.
- [x] 6.7 `GET /tp-sin-corregir/export?materia_id=` (CSV) → `StreamingResponse` con `Content-Disposition: attachment`.
- [x] 6.8 `GET /monitor?materia_id=&...filtros...` → `MonitorResponse` (con auditoría en COORDINADOR/ADMIN).
- [x] 6.9 Registrar router en `app/main.py`.

## 7. Tests de API (router)

- [x] 7.1 Tests `tests/api/v1/routers/test_analisis.py` con `TestClient` + mock de `get_current_user` + fixtures de DB.
- [x] 7.2 Test: sin permiso `atrasados:ver` → 403.
- [x] 7.3 Test: PROFESOR solo recibe sus alumnos (scope isolation).
- [x] 7.4 Test: ranking vacío cuando no hay alumnos con aprobadas.
- [x] 7.5 Test: reporte rápido vacío cuando no hay calificaciones.
- [x] 7.6 Test: `POST /tp-sin-corregir` con CSV válido → detecta pendientes textuales, ignora numéricas.
- [x] 7.7 Test: `GET /monitor` con COORDINADOR genera evento auditoría `ANALISIS_ATRASADOS_VER`.
- [x] 7.8 Test: export CSV de notas finales retorna `text/csv` con filas correctas.

## 8. Auditoría y código de acción

- [x] 8.1 Agregar código `ANALISIS_ATRASADOS_VER` al catálogo de códigos de auditoría (RN-24).
- [x] 8.2 Verificar que el middleware/servicio de auditoría registra correctamente el evento al acceder al monitor general.
