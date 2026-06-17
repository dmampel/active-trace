## Why

El sistema ya gestiona usuarios, roles y estructura académica, pero aún no puede incorporar los alumnos reales de una materia. Sin el padrón no hay base para calificaciones, análisis de atrasados ni comunicaciones dirigidas — bloqueando toda la épica de valor del producto.

## What Changes

- Nuevo modelo `VersionPadron` + `EntradaPadron`: padrón versionado por (materia, cohorte), con historial preservado al reemplazar.
- Importación de padrón desde archivo xlsx/csv (F1.3): crea una nueva versión activa, desactiva la anterior.
- Importación de listado de participantes desde Moodle Web Services (F1.4): cliente dedicado `moodle_ws.py` que llama a la API de Moodle y genera un `VersionPadron` equivalente.
- Vaciar datos de padrón de una materia (F1.5): elimina entradas del usuario en scope, no afecta otros docentes.
- Endpoints REST para listar versiones, ver entradas y activar/desactivar versiones.

## Capabilities

### New Capabilities

- `padron-ingesta`: VersionPadron y EntradaPadron — modelo, repositorio, servicio de importación desde archivo (xlsx/csv) y desde Moodle WS, endpoints REST con RBAC fino, operación de vaciado scope-isolated.

### Modified Capabilities

- `asignaciones`: las consultas de padrón necesitan saber qué materias y cohortes tiene asignadas un usuario — se extiende el repositorio con filtros de contexto pero sin cambio de contrato de API ni de requisitos funcionales.

## Impact

- **Backend nuevos**: `backend/app/models/padron.py`, `backend/app/repositories/padron_repository.py`, `backend/app/services/padron_service.py`, `backend/app/routers/padron.py`, `backend/app/integrations/moodle_ws.py`
- **Migración Alembic**: tablas `version_padron` y `entrada_padron`
- **Dependencias**: `openpyxl` (xlsx), `httpx` (cliente Moodle WS async)
- **Config**: variables de entorno `MOODLE_URL`, `MOODLE_TOKEN` por tenant (via AES-256 en DB)
- **Tests**: pytest con DB de test real, fixtures de xlsx/csv en `tests/fixtures/`
