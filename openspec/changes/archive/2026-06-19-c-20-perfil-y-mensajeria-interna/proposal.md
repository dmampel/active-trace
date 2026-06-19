## Why

Hoy un usuario solo puede tener sus datos editados por un ADMIN a través del ABM administrativo (`usuario-management`, permiso `usuarios:gestionar`). Falta la capacidad de **autogestión**: que cada persona autenticada edite su propio perfil (Épica 11, F11.1) sin pasar por administración. Además, el sistema necesita un canal de **mensajería interna entre usuarios registrados** (F3.4, F11.2, FL-10) — distinto de los emails salientes a alumnos — para avisos de coordinación, notificaciones del sistema y respuestas dentro de un hilo. C-07 (usuarios y asignaciones) ya está completo, por lo que la base de identidad existe y estas capacidades pueden construirse encima.

## What Changes

- **Perfil propio (F11.1)**: nuevo endpoint `/api/v1/perfil` (GET/PATCH) operando SIEMPRE sobre el usuario del JWT verificado (nunca por id en URL/body). Campos editables por el propio usuario: `nombre`, `apellidos`, `dni`, `sexo`, `cbu`, `alias_cbu`, `banco`, `regional`, `email`, `modalidad_cobro` (factura/liquidación → mapea a `facturador`), `legajo_profesional`. El `cuil` es **solo lectura** (no modificable por el usuario). PII (`dni`, `cbu`, `alias_cbu`) cifrada AES-256 en reposo, recifrada al actualizar, jamás en texto plano en logs.
- **Mensajería interna (F3.4, F11.2, FL-10)**: nueva capacidad de inbox entre usuarios registrados, paralela e independiente de las comunicaciones salientes a alumnos (`ComunicacionDocente` de C-12). Endpoints `/api/v1/inbox/*`:
  - listar hilos recibidos por el usuario autenticado,
  - abrir/leer un hilo (marca leído),
  - responder dentro del hilo,
  - generar un nuevo mensaje hacia el inbox de otro usuario del mismo tenant.
- **Cierre de sesión explícito (F11.3)**: reusa el logout ya implementado en C-03 (auth). No se introduce lógica nueva; se documenta como capacidad cubierta.
- Nuevas entidades: `hilo_mensaje` (conversación con asunto, participantes) y `mensaje_interno` (cuerpo, autor, estado de lectura por destinatario), ambas con `tenant_id`, soft delete y aislamiento por usuario/tenant.
- Migración Alembic: una sola, para las dos tablas nuevas (`hilo_mensaje`, `mensaje_interno`).

## Capabilities

### New Capabilities
- `perfil-propio`: autogestión del perfil del usuario autenticado vía `/api/v1/perfil`; identidad desde JWT, edición de campos propios, `cuil` solo lectura, PII cifrada.
- `mensajeria-interna`: bandeja de mensajes interna entre usuarios registrados (hilos, lectura, respuesta, envío) aislada por tenant y por usuario, vía `/api/v1/inbox/*`.

### Modified Capabilities
<!-- No se modifican requisitos de specs existentes. El logout (F11.3) ya está cubierto por la capacidad user-auth (C-03); el ABM administrativo de usuario-management permanece intacto. -->

## Impact

- **Modelos nuevos**: `HiloMensaje`, `MensajeInterno` (+ migración Alembic única).
- **Backend**: nuevos routers `perfil` e `inbox`, services y repositories asociados (flujo Routers → Services → Repositories → Models). Reusa el modelo `Usuario` existente para el perfil.
- **RBAC**: nuevos permisos `perfil:editar` (autoservicio) e `inbox:usar`; fail-closed. El perfil NO requiere `usuarios:gestionar`.
- **Auth**: depende de la identidad del JWT (C-03/C-04) y reusa el logout de C-03 para F11.3.
- **Sin breaking changes**: no altera `usuario-management` ni las comunicaciones a alumnos.
- **APIs nuevas**: `GET/PATCH /api/v1/perfil`, `GET /api/v1/inbox`, `GET /api/v1/inbox/{hilo_id}`, `POST /api/v1/inbox/{hilo_id}/responder`, `POST /api/v1/inbox`.
