## Why

El sistema ya tiene identidad de autenticación (`user`: email + password + 2FA, C-03) y asignación de roles globales sin contexto (`user_rol`, C-04), pero NO tiene el perfil completo de la persona (nombre, apellidos, datos fiscales y bancarios) ni el vínculo de un usuario a un rol **dentro de un contexto académico** (materia/carrera/cohorte/comisión) con vigencia temporal. Sin esto no se puede armar equipos docentes (C-08), cargar padrón (C-09), liquidar honorarios (C-18) ni resolver permisos efectivos acotados por vigencia. C-07 es el cuello de botella de GATE 6: lo desbloquea casi toda la FASE 4.

El dominio (KB E4/E5) define `Usuario` y `Asignacion` como entidades centrales. La PII (DNI, CUIL, CBU, alias_cbu, email) es dato sensible: debe cifrarse en reposo con AES-256-GCM (ya disponible en `core/security.py`) y nunca exponerse en logs ni respuestas en texto plano sin permiso.

## What Changes

- **Perfil de Usuario con PII cifrada**: se extiende la entidad de identidad existente (`user`) con los atributos de negocio de la persona — `nombre`, `apellidos`, `dni` [cifrado], `cuil` [cifrado], `cbu` [cifrado], `alias_cbu` [cifrado], `banco`, `regional`, `legajo`, `legajo_profesional`, `facturador`, `estado`. El `email` ya existente pasa a tratarse como PII. `legajo` es atributo de negocio opcional, jamás credencial ni selector de sesión (identidad = UUID interno).
- **ABM de Usuarios** `/api/v1/usuarios` con guard `usuarios:gestionar` (ADMIN): crear, leer, editar, soft-delete. La PII se descifra solo para quien tiene permiso de gestión; en listados y logs nunca aparece en claro.
- **Entidad `Asignacion`** (Usuario ↔ Rol ↔ contexto académico): `rol` (enum del dominio), `materia_id`/`carrera_id`/`cohorte_id` (nullables para roles de tenant global), `comisiones` (lista), `responsable_id` (jerarquía docente), `desde`/`hasta` (vigencia, `hasta` nulo = abierta). `estado_vigencia` (Vigente/Vencida) es **derivado por fechas, no almacenado**.
- **CRUD de Asignaciones** `/api/v1/asignaciones` con guard `equipos:asignar` (COORDINADOR, ADMIN). Una asignación vencida no otorga permisos pero **se conserva en el histórico** (soft delete, nunca hard delete). Genera auditoría `ASIGNACION_MODIFICAR`.
- **Permisos efectivos acotados por vigencia**: la resolución de permisos del usuario (C-04) se complementa para que una asignación contextual solo otorgue acceso mientras esté vigente.
- `Migración 006: usuario (columnas PII) + asignacion`.
- Permisos nuevos en el catálogo seed: `usuarios:gestionar`, `equipos:asignar`.

## Capabilities

### New Capabilities
- `usuario-management`: perfil completo de la persona con PII cifrada (DNI/CUIL/CBU/alias_cbu/email AES-256-GCM), ABM administrativo, unicidad `(tenant_id, email)`, soft delete, legajo como atributo de negocio.
- `asignaciones`: vínculo Usuario↔Rol↔contexto académico con vigencia temporal, jerarquía `responsable_id`, histórico append-only, CRUD permisado y auditado, derivación de `estado_vigencia`.

### Modified Capabilities
- `rbac`: la resolución de permisos efectivos se acota por la **vigencia** de las asignaciones contextuales (una asignación vencida no autoriza). Cambio de comportamiento a nivel de requirement.

## Impact

- **Modelos**: extiende `backend/app/models/user.py` (columnas PII en `User`); nuevo `backend/app/models/asignacion.py`.
- **Repositories**: nuevo `usuario_repository.py` (o extiende `user_repository.py`), nuevo `asignacion_repository.py` — scope de tenant por defecto.
- **Services**: `usuario_service.py` (cifrado/descifrado PII, reglas de negocio), `asignacion_service.py` (vigencia, jerarquía).
- **Schemas**: DTOs Pydantic v2 `extra='forbid'`; respuestas NO incluyen PII en claro salvo con permiso de gestión.
- **API**: nuevos routers `usuarios.py`, `asignaciones.py` bajo `/api/v1`.
- **RBAC**: depende de cómo se relacionan `user_rol` (rol global, C-04) y `Asignacion` (rol contextual) — decisión en design.md. Permisos nuevos en seed.
- **Auditoría**: integra `ASIGNACION_MODIFICAR` (C-05).
- **Migración**: Alembic `006` (una sola por cambio de schema).
- **Cifrado**: usa `AES256GCMCipher` de `core/security.py` (fix-security).
- **Governance**: CRÍTICO (PII + parte de RBAC) → diseño aprobado antes de implementar.
