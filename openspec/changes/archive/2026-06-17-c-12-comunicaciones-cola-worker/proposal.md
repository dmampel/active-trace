## Why

El flujo central del PROFESOR (FL-02) culmina en la comunicación a alumnos atrasados: sin una cola de envío asíncrona con estado, preview y aprobación, el sistema puede analizar quién está atrasado pero no puede notificarlo de forma controlada y auditable. C-12 cierra el camino crítico al agregar la capa de despacho que convierte el análisis de C-11 en acción real.

## What Changes

- **Nuevo modelo `Comunicacion`** (E21): destinatario cifrado AES-256, lote_id para agrupación masiva, máquina de estados Pendiente → Enviando → Enviado / Error / Cancelado (RN-15).
- **Worker asíncrono** en `backend/app/workers/`: consume registros en estado Pendiente y despacha emails, transicionando estados en cada paso.
- **Plantillas con sustitución**: variables `{{alumno.nombre}}`, `{{materia.nombre}}`, `{{lote.descripcion}}` resueltas en preview y en despacho.
- **Preview obligatorio** (RN-16): endpoint `POST /api/v1/comunicaciones/preview` que renderiza asunto + cuerpo sin persistir ni enviar.
- **Envío individual y masivo** (F3.2): `POST /api/v1/comunicaciones/enviar` — guard `comunicacion:enviar`; soporta un destinatario o un lote.
- **Aprobación humana configurable por tenant** (F3.3, RN-17): si `requiere_aprobacion=True` en la config del tenant, los mensajes masivos quedan en Pendiente hasta que un usuario con `comunicacion:aprobar` los aprueba o cancela (`POST /api/v1/comunicaciones/lotes/{lote_id}/aprobar|cancelar`).
- **Cancelación individual** (F3.2): `POST /api/v1/comunicaciones/{id}/cancelar` — solo en estado Pendiente.
- **Migración Alembic** `0014_comunicacion.py`: tabla `comunicacion`, índices por tenant + estado + lote.
- **Audit log** `COMUNICACION_ENVIAR` en toda transición de envío confirmado.

## Capabilities

### New Capabilities
- `comunicaciones`: Gestión del ciclo de vida de mensajes salientes a alumnos: preview, encolado, aprobación, cancelación y tracking de estados; incluye worker asíncrono de despacho.

### Modified Capabilities

(ninguna — no cambian requisitos de specs existentes)

## Impact

- **Backend**: nuevos módulos en `models/`, `schemas/`, `repositories/`, `services/`, `routers/`, `workers/`.
- **Migración**: tabla `comunicacion` con cifrado de columna `destinatario`.
- **Seguridad**: permisos nuevos `comunicacion:enviar` y `comunicacion:aprobar`; destinatario cifrado en reposo (AES-256).
- **Worker**: proceso independiente que corre junto a la API (misma imagen Docker, arranque separado por compose); ADR-003 resuelto a favor del worker propio con asyncio.
- **Dependencias externas**: proveedor SMTP configurable por tenant vía variables de entorno (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`); en test se usa un mock/stub.
- **Desbloquea**: C-22 frontend-academico-docente (tracking de estado de comunicaciones).
