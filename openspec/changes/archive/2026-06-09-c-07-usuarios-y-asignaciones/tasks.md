
# Tasks — c-07-usuarios-y-asignaciones

> Strict TDD: por cada task de lógica, primero el test que falla, luego el código mínimo, luego triangulación y refactor. DB real (no mocks). Cada archivo backend ≤500 LOC. Governance CRÍTICO: el modelo de datos y el cifrado de PII deben revisarse antes de avanzar a endpoints.

## 1. Modelo de datos y migración

- [x] 1.1 Extender `backend/app/models/user.py` (`User`) con columnas de perfil: `nombre`, `apellidos`, `dni_enc`, `cuil_enc`, `cbu_enc`, `alias_cbu_enc`, `banco`, `regional`, `legajo`, `legajo_profesional`, `facturador` (bool default False), `estado` (reutiliza `EstadoEntidad`, default Activa). Columnas nuevas nullables/con default.
- [x] 1.2 Crear `backend/app/models/asignacion.py`: modelo `Asignacion` (UUIDMixin, TimestampMixin, SoftDeleteMixin, TenantMixin) con `usuario_id` (FK user.id), enum `RolDominio` (PROFESOR/TUTOR/COORDINADOR/NEXO/ADMIN/FINANZAS), `materia_id`/`carrera_id`/`cohorte_id` (FK nullables, ondelete RESTRICT), `comisiones` (JSONB lista, default []), `responsable_id` (FK user.id nullable), `desde` (Date NOT NULL), `hasta` (Date nullable). Índices: tenant_id, usuario_id.
- [x] 1.3 Registrar `Asignacion` en `backend/app/models/__init__.py`.
- [x] 1.4 Migración Alembic `006`: enum `roldominio`, columnas PII en `user`, tabla `asignacion`. Verificar `downgrade` reversible sin pérdida de datos previos.
- [x] 1.5 Verificar/seed: permisos `usuarios:gestionar` y `equipos:asignar` existen en el catálogo (vienen de C-04). Si `equipos:asignar` falta, agregarlo y asociarlo a roles COORDINADOR y ADMIN. Agregar `atrasados:ver` y `calificaciones:ver` al catálogo y asociarlos al rol NEXO (PA-25 resuelta: NEXO tiene solo lectura sobre progreso académico de su población; sin permisos financieros — esos son de FINANZAS).

## 2. Cifrado de PII (Service-level)

- [x] 2.1 Test: helper de cifrado/descifrado de PII usa `AES256GCMCipher` con la clave de config; round-trip de `dni`/`cuil`/`cbu`/`alias_cbu` recupera el valor original.
- [x] 2.2 Implementar el cifrado/descifrado de PII en el Service de usuarios (nunca en Repository ni Model).
- [x] 2.3 Test: el valor persistido en columnas `*_enc` NO coincide con el texto plano (está cifrado).
- [x] 2.4 Test: la PII no aparece en texto plano en logs durante crear/leer usuario.

## 3. Repository de usuarios

- [x] 3.1 Test: crear usuario filtra/asigna `tenant_id` del autenticado; lookup por id acotado a tenant (otro tenant → None).
- [x] 3.2 Test: unicidad `(tenant_id, email)` — duplicado en mismo tenant rechaza; mismo email en otro tenant permite.
- [x] 3.3 Implementar `usuario_repository.py` (o extender `user_repository.py`): create, get_by_id (scope tenant + deleted_at null), list_active, update, soft_delete. Siguiendo el patrón de `estructura_repository.py`.
- [x] 3.4 Test: soft_delete setea `deleted_at`; el usuario no aparece en list_active.

## 4. Service y schemas de usuarios

- [x] 4.1 Crear schemas Pydantic v2 (`extra='forbid'`): `UsuarioCreate`, `UsuarioUpdate`, `UsuarioListItem` (SIN PII en claro), `UsuarioDetail` (CON PII descifrada).
- [x] 4.2 Test: schema rechaza campo no declarado (422).
- [x] 4.3 Implementar `usuario_service.py`: orquesta cifrado PII, unicidad email (409), reglas de negocio, mapeo a DTO de listado (sin PII) vs detalle (con PII).
- [x] 4.4 Test: el DTO de listado NO incluye `dni`/`cuil`/`cbu`/`alias_cbu`; el DTO de detalle SÍ (descifrado).
- [x] 4.5 Test: desactivar usuario (`estado=Inactiva`) cierra en cascada todas sus asignaciones vigentes — establece `hasta = fecha_baja` en cada una y genera audit `ASIGNACION_MODIFICAR` por cada cierre.
- [x] 4.6 Test: la cascada emite una alerta/evento hacia cada `responsable_id` único de las asignaciones afectadas (vacancia generada); si `responsable_id` es null en alguna asignación, se omite sin error.
- [x] 4.7 Implementar la cascada de cierre en `usuario_service.py`: al setear `estado=Inactiva`, buscar asignaciones con `hasta IS NULL OR hasta >= fecha_baja`, setear `hasta = fecha_baja`, registrar auditoría y emitir la alerta a cada `responsable_id` distinto.

## 5. API de usuarios

- [x] 5.1 Crear router `backend/app/api/v1/routers/usuarios.py` bajo `/api/v1/usuarios` con guard `require_permission("usuarios:gestionar")` en todos los endpoints.
- [x] 5.2 Implementar POST (201), GET listado (sin PII), GET /{id} detalle (con PII descifrada), PATCH (200), DELETE (204 soft delete). Identidad/tenant SIEMPRE desde `get_current_user`.
- [x] 5.3 Registrar el router en la app.
- [x] 5.4 Test integración: crear → listar (sin PII) → detalle (con PII) → editar → soft delete.
- [x] 5.5 Test integración: sin permiso → 403; sin token → 401; usuario de otro tenant → 404; email duplicado → 409.

## 6. Repository y vigencia de asignaciones

- [x] 6.1 Test: derivación de `estado_vigencia` — `desde<=hoy` y (`hasta` null o `hoy<=hasta`) ⇒ Vigente; `hasta` en pasado ⇒ Vencida.
- [x] 6.2 Implementar la derivación de `estado_vigencia` en `asignacion_service.py` (no almacenado).
- [x] 6.3 Test: repository scope tenant por defecto; validación de que `materia_id`/`carrera_id`/`cohorte_id` del body pertenecen al tenant (otro tenant → no encontrado).
- [x] 6.4 Implementar `asignacion_repository.py`: create, get_by_id (scope tenant + deleted_at null), list con filtros (usuario_id, materia_id, cohorte_id, rol, vigencia), update, soft_delete.
- [x] 6.5 Test: histórico — asignación con `hasta` en el pasado se conserva y es consultable; soft_delete no borra físicamente.

## 7. Service, schemas y API de asignaciones

- [x] 7.1 Crear schemas Pydantic v2 (`extra='forbid'`): `AsignacionCreate`, `AsignacionUpdate`, `AsignacionRead` (incluye `estado_vigencia` derivado y `responsable_id`).
- [x] 7.2 Test: schema rechaza campo no declarado (422); contexto global (sin materia/carrera/cohorte) aceptado.
- [x] 7.3 Implementar `asignacion_service.py`: validación de contexto contra tenant, jerarquía `responsable_id`, multi-rol.
- [x] 7.4 Crear router `backend/app/api/v1/routers/asignaciones.py` bajo `/api/v1/asignaciones` con guard `require_permission("equipos:asignar")`. POST/GET(filtros)/PATCH/DELETE. Registrarlo en la app.
- [x] 7.5 Test integración: crear (201) → filtrar por usuario → editar vigencia → soft delete; sin permiso → 403; contexto de otro tenant → 422.
- [x] 7.6 Integrar auditoría `ASIGNACION_MODIFICAR` (C-05) en create/update/delete; test que verifica el registro de auditoría.

## 8. Resolución RBAC acotada por asignaciones contextuales

- [x] 8.1 Test: una `asignacion` contextual vigente con rol PROFESOR incluye los permisos del rol en los permisos efectivos.
- [x] 8.2 Test: una `asignacion` contextual vencida (`hasta` en pasado) NO contribuye a los permisos efectivos, pero el registro se conserva.
- [x] 8.3 Extender la resolución de permisos efectivos (C-04) para considerar el plano contextual (`asignacion`) además del global (`user_rol`), acotando por vigencia y tenant.
- [x] 8.4 Test: revocación (soft delete) de una asignación vigente quita el permiso en la siguiente request.

## 9. Cierre

- [x] 9.1 Suite completa GREEN; cobertura ≥80% líneas, ≥90% en reglas de negocio (vigencia, cifrado, unicidad, RBAC).
- [x] 9.2 Verificar que ningún archivo backend supera 500 LOC; refactor si hace falta.
- [x] 9.3 Marcar `[x]` C-07 en `CHANGES.md` y archivar el change.
