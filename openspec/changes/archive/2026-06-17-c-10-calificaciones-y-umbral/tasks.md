# Tasks — C-10 calificaciones-y-umbral

> Strict TDD en cada grupo: test que falla (RED) → código mínimo (GREEN) → triangular casos → refactor. DB real (sin mocks de DB). Cobertura ≥80% líneas, ≥90% en la derivación de `aprobado` e import/preview/selección. Identidad siempre desde el JWT, scope tenant por defecto, RBAC fail-closed.

## 1. Modelos y migración

- [x] 1.1 RED: test de modelo `Calificacion` — campos (`entrada_padron_id` FK CASCADE, `materia_id` UUID indexado sin FK, `actividad`, `nota_numerica`, `nota_textual`, `origen` enum `OrigenCalificacion`, `importado_at`, `tenant_id`), mixins UUID/Timestamp/SoftDelete/Tenant, sin columna `aprobado`
- [x] 1.2 RED: test de modelo `UmbralMateria` — `asignacion_id` FK, `materia_id` UUID indexado, `umbral_pct` (default 60), `valores_aprobatorios` (lista JSON), `tenant_id`, mixins
- [x] 1.3 GREEN: crear `backend/app/models/calificacion.py` (`OrigenCalificacion`, `Calificacion`, `UmbralMateria`) reusando mixins de `app/models/base.py`; registrarlos donde Alembic/metadata los detecte
- [x] 1.4 Escribir migración `backend/alembic/versions/009_calificaciones_tables.py` (down_revision `a8b9c0d1e2f3`): `create_table` `calificacion` y `umbral_materia` con índices por `tenant_id`/`materia_id`/`entrada_padron_id`/`asignacion_id`; `downgrade()` con drops. Una sola migración para este cambio de schema
- [x] 1.5 En la misma migración: sembrar permisos `calificaciones:importar` (→ PROFESOR, COORDINADOR) y `calificaciones:leer` (→ PROFESOR, TUTOR, COORDINADOR, ADMIN) con el patrón INSERT de `008_padron_tables`; `downgrade()` hace DELETE de esos permisos
- [x] 1.6 REFACTOR: verificar ≤500 LOC por archivo y snake_case en columnas/módulos

## 2. Derivación pura de `aprobado` (regla núcleo, ≥90%)

- [x] 2.1 RED: test `derivar_aprobado` numérica por encima del umbral (7/10, 60% → true)
- [x] 2.2 GREEN: crear `backend/app/domain/aprobado.py` con `derivar_aprobado(nota_numerica, nota_textual, umbral_pct, nota_maxima, valores_aprobatorios) -> bool` (sin I/O ni DB)
- [x] 2.3 TRIANGULAR: límite exacto inclusivo (6/10, 60% → true) y por debajo (5/10 → false)
- [x] 2.4 TRIANGULAR: textual en conjunto aprobatorio → true; fuera del conjunto → false
- [x] 2.5 TRIANGULAR: precedencia numérica sobre textual (5/10 + "Satisfactorio" → false)
- [x] 2.6 TRIANGULAR: sin ninguna nota → false
- [x] 2.7 REFACTOR: nombres claros, extraer constantes; tests verdes tras cada paso

## 3. Repositorios (filtro tenant por defecto)

- [x] 3.1 RED: test `CalificacionRepository` — crear/listar calificaciones filtra SIEMPRE por `tenant_id`; soft delete excluye `deleted_at` no nulo; aislamiento entre tenants
- [x] 3.2 GREEN: `backend/app/repositories/calificacion_repository.py` (sin lógica de negocio; queries scopeadas por tenant)
- [x] 3.3 RED: test `UmbralRepository` — obtener `UmbralMateria` por `(tenant, asignacion, materia)`; retorna None si no existe; upsert idempotente
- [x] 3.4 GREEN: `backend/app/repositories/umbral_repository.py`
- [x] 3.5 REFACTOR: deduplicar el patrón de scope tenant

## 4. Parser LMS, preview y selección (F1.1 — RN-01/RN-02)

- [x] 4.1 RED: test detección de columna numérica por sufijo `(Real)` (RN-01) y que otras columnas NO se interpretan como nota numérica
- [x] 4.2 RED: test detección de escala textual (RN-02) sobre valores configurados
- [x] 4.3 GREEN: parser en `backend/app/services/calificacion_parser.py` que clasifica actividades (numérica|textual) y arma la estructura de preview (actividades + alumnos) SIN persistir
- [x] 4.4 RED+GREEN: `preview()` no escribe ninguna `Calificacion` (assert sobre DB real)
- [x] 4.5 RED+GREEN: importar solo las actividades seleccionadas — dadas 3 actividades y selección de 2, persiste calificaciones de esas 2
- [x] 4.6 TRIANGULAR: filas con nota textual vs numérica vs vacías mapean a `Calificacion` correctamente
- [x] 4.7 REFACTOR: separar parsing puro de la persistencia; mantener archivo ≤500 LOC (extraer parser a módulo aparte si hace falta)

## 5. Cruce reporte de finalización (F1.2 — RN-07/RN-08)

- [x] 5.1 RED: test entrega textual finalizada sin calificación → figura como "sin corregir" (RN-07)
- [x] 5.2 GREEN: método de cruce en el service que compara reporte de finalización vs calificaciones importadas
- [x] 5.3 TRIANGULAR: actividad numérica finalizada sin nota → NO figura (RN-08)
- [x] 5.4 TRIANGULAR: entrega textual ya calificada → NO figura como sin corregir
- [x] 5.5 REFACTOR

## 6. Configuración de umbral (F2.1 — RN-03, scope aislado RN-04)

- [x] 6.1 RED: test `UmbralService.configurar` persiste `UmbralMateria` para la asignación del docente en sesión (tenant del JWT)
- [x] 6.2 GREEN: `backend/app/services/umbral_service.py`
- [x] 6.3 RED+GREEN: resolución de umbral — usa el `UmbralMateria` de la asignación; si no existe, defecto del tenant (60%)
- [x] 6.4 RED+GREEN: aislamiento de scope — cambiar el umbral del docente A no afecta el de B ni la derivación de sus calificaciones
- [x] 6.5 Integrar `derivar_aprobado` en el service: resolver umbral + nota_maxima y derivar al proyectar (no persistir `aprobado`)
- [x] 6.6 REFACTOR

## 7. Auditoría

- [x] 7.1 RED: test que una importación exitosa registra `AuditLog` con `accion = "CALIFICACIONES_IMPORTAR"`, `materia_id`, `filas_afectadas`, IP y user agent, atribuido al actor real del JWT
- [x] 7.2 GREEN: registrar el evento en el service tras persistir, reusando el patrón de auditoría de padrón
- [x] 7.3 TRIANGULAR: importación que no persiste filas (preview / selección vacía) no genera el evento de import
- [x] 7.4 REFACTOR

## 8. Schemas y endpoints (RBAC fail-closed, identidad JWT, scope tenant)

- [x] 8.1 Crear `backend/app/schemas/calificacion.py` — DTOs de preview, selección de actividades, import resultado, config de umbral, salida "sin corregir"; TODOS con `model_config = ConfigDict(extra='forbid')`
- [x] 8.2 RED: test endpoint importar — 403 sin `calificaciones:importar` (fail-closed); 404 si `materia_id` fuera del tenant
- [x] 8.3 GREEN: `backend/app/api/v1/routers/calificaciones.py` — endpoints de preview, import (con selección), reporte de finalización y config de umbral; cada uno con `Depends(require_permission(...))`; identidad desde `CurrentUser` del JWT, nunca de URL/body
- [x] 8.4 RED+GREEN: endpoint de lectura exige `calificaciones:leer`; TUTOR con el permiso lee sin error
- [x] 8.5 RED+GREEN: identidad derivada del JWT — `tenant_id`/`usuario_id` en body/URL se ignoran
- [x] 8.6 Registrar el router en `app/main.py`
- [x] 8.7 REFACTOR

## 9. Verificación final

- [x] 9.1 Correr la suite completa contra DB real; confirmar cobertura ≥80% líneas y ≥90% en `derivar_aprobado` e import/preview/selección
- [x] 9.2 Verificar reglas duras: sin lógica de negocio en routers, sin acceso DB desde services (solo vía repos), `extra='forbid'` en todos los schemas, ≤500 LOC por archivo, una sola migración
- [x] 9.3 Marcar `[x]` C-10 en `CHANGES.md`
