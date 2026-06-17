## 1. Dependencias y configuración

- [x] 1.1 Agregar `openpyxl` y `httpx` a `pyproject.toml` (ya instalados como dep de FastAPI/test, verificar versiones)
- [x] 1.2 Agregar variables de entorno `MOODLE_URL` y `MOODLE_TOKEN` al modelo `Settings` en `core/config.py` (opcionales, por si no usan Moodle)

## 2. Modelos SQLAlchemy

- [x] 2.1 Crear `backend/app/models/padron.py` con `VersionPadron` (TenantMixin, UUIDMixin, TimestampMixin, SoftDeleteMixin): `materia_id`, `cohorte_id`, `cargado_por`, `cargado_at`, `activa: bool`
- [x] 2.2 Agregar `EntradaPadron` al mismo archivo: `version_id`, `tenant_id`, `usuario_id (nullable)`, `nombre`, `apellidos`, `email (texto cifrado)`, `comision (nullable)`, `regional (nullable)`
- [x] 2.3 Crear `backend/app/models/tenant_moodle_config.py` con `TenantMoodleConfig`: `tenant_id (FK, unique)`, `moodle_url (cifrado)`, `moodle_token (cifrado)`
- [x] 2.4 Registrar los modelos en `backend/app/models/__init__.py`

## 3. Migración Alembic

- [x] 3.1 Generar migración: `alembic revision --autogenerate -m "add padron tables"` desde el directorio backend
- [x] 3.2 Revisar y ajustar el script generado: verificar índices en `(tenant_id, materia_id, cohorte_id, activa)` para `version_padron`, y FK correctas
- [x] 3.3 Aplicar migración en DB de test: `alembic upgrade head` y verificar que las tablas existen

## 4. Repositorios

- [x] 4.1 Crear `backend/app/repositories/padron_repository.py` con `PadronRepository(BaseRepository)`:
  - `get_activa(materia_id, cohorte_id, tenant_id)` → `VersionPadron | None`
  - `listar_versiones(materia_id, tenant_id)` → `list[VersionPadron]`
  - `activar_version(nueva_version_id, materia_id, cohorte_id, tenant_id)` → desactiva la anterior en la misma transacción, activa la nueva
  - `crear_version_con_entradas(version: VersionPadron, entradas: list[EntradaPadron])` → commit atómico
- [x] 4.2 Crear `backend/app/repositories/moodle_config_repository.py`:
  - `get_by_tenant(tenant_id)` → `TenantMoodleConfig | None`
  - `upsert(config: TenantMoodleConfig, tenant_id)` → crea o reemplaza

## 5. Integración Moodle WS

- [x] 5.1 Crear `backend/app/integrations/moodle_ws.py` con `MoodleWSClient`:
  - `__init__(moodle_url: str, token: str)` — recibe credenciales ya descifradas
  - `get_course_participants(course_id: int) -> list[dict]` → llama a `core_enrol_get_enrolled_users` del WS de Moodle con `httpx.AsyncClient`, timeout 10s
  - Mapea respuesta a lista de dicts `{nombre, apellidos, email}`
- [x] 5.2 Agregar `__init__.py` en `integrations/` si no existe (ya existe según estructura actual)

## 6. Schemas Pydantic

- [x] 6.1 Crear `backend/app/schemas/padron.py` con `ConfigDict(extra='forbid')`:
  - `ImportarPadronArchivoRequest` — vacío (usa `UploadFile` en el router)
  - `ImportarPadronMoodleRequest` — `course_id: int`
  - `EntradaPadronOut` — `id`, `nombre`, `apellidos`, `email`, `comision`, `regional`, `usuario_id`
  - `VersionPadronOut` — `id`, `materia_id`, `cohorte_id`, `cargado_por`, `cargado_at`, `activa`, `total_entradas`
  - `VersionPadronDetalleOut` — `VersionPadronOut` + `entradas: list[EntradaPadronOut]`
  - `ImportarResultadoOut` — `version_id`, `total_importado`, `activa`
  - `MoodleConfigRequest` — `moodle_url: str`, `moodle_token: str`

## 7. Servicio de padrón

- [x] 7.1 Crear `backend/app/services/padron_service.py` con `PadronService`:
  - `_parse_xlsx(file_bytes: bytes) -> list[dict]` — openpyxl read_only=True, valida columnas obligatorias, levanta `ValueError` si faltan, `TooLargeError` si >5.000 filas
  - `_parse_csv(file_bytes: bytes) -> list[dict]` — csv stdlib, mismas validaciones
  - `importar_archivo(materia_id, cohorte_id, cargado_por_id, file_bytes, filename, tenant_id, session)` → detecta formato, parsea, construye `VersionPadron` + `EntradaPadron` (cifra email), llama repo para commit atómico
  - `importar_moodle(materia_id, cohorte_id, cargado_por_id, course_id, tenant_id, session)` → lee config Moodle del repo (descifra), llama `MoodleWSClient`, construye versión, commit
  - `get_activo(materia_id, tenant_id, session)` → llama repo, descifra emails de entradas
  - `listar_versiones(materia_id, tenant_id, session)` → llama repo
  - `vaciar(materia_id, usuario_id, tenant_id, session)` → verifica que `cargado_por == usuario_id`, soft-delete

## 8. Router REST

- [x] 8.1 Crear `backend/app/api/v1/padron.py` con `APIRouter(prefix="/padron", tags=["padron"])`:
  - `POST /{materia_id}/importar` — `UploadFile`, permiso `padron:importar`, llama servicio, retorna `ImportarResultadoOut` 201
  - `POST /{materia_id}/importar-moodle` — `ImportarPadronMoodleRequest`, permiso `padron:importar`, llama servicio, retorna `ImportarResultadoOut` 201
  - `GET /{materia_id}/activo` — permiso `padron:leer`, retorna `VersionPadronDetalleOut` 200
  - `GET /{materia_id}/versiones` — permiso `padron:leer`, retorna `list[VersionPadronOut]` 200
  - `DELETE /{materia_id}/activo` — permiso `padron:importar`, llama `vaciar`, retorna 204
- [x] 8.2 Crear `backend/app/api/v1/admin/moodle_config.py`:
  - `PUT /admin/moodle-config` — `MoodleConfigRequest`, permiso `admin:config`, cifra url+token, upsert en repo, retorna 200
- [x] 8.3 Registrar ambos routers en `backend/app/api/v1/__init__.py` o `main.py`

## 9. RBAC — permisos nuevos

- [x] 9.1 Agregar permisos `padron:importar` y `padron:leer` a la matriz de permisos en `backend/app/core/rbac.py` (o donde viva la definición de permisos):
  - `padron:importar` → PROFESOR (scope materia propia), COORDINADOR
  - `padron:leer` → PROFESOR (scope materia propia), COORDINADOR, TUTOR, ADMIN
- [x] 9.2 Verificar que el guard `require_permission` funciona con los nuevos permisos (test de smoke)

## 10. Tests

- [x] 10.1 Crear directorio `backend/tests/fixtures/padron/` con:
  - `padron_valido.xlsx` — 5 filas con columnas nombre/apellidos/email/comision
  - `padron_valido.csv` — mismo contenido en csv
  - `padron_sin_email.xlsx` — xlsx sin columna email (para test de 400)
  - `padron_grande.xlsx` — script o fixture que genere >5.000 filas (puede ser generado en conftest)
- [x] 10.2 Tests unitarios de `PadronService._parse_xlsx` y `_parse_csv`:
  - Happy path xlsx
  - Happy path csv
  - Columna obligatoria faltante → ValueError
  - Archivo >5.000 filas → TooLargeError
  - Columnas extra ignoradas
- [x] 10.3 Tests de integración del router `POST /{materia_id}/importar` (TestClient, mocked `get_current_user`):
  - Importar xlsx correctamente → 201
  - Importar csv correctamente → 201
  - Sin permiso `padron:importar` → 403
  - materia de otro tenant → 404
  - Columna faltante → 400
  - Archivo grande → 413
- [x] 10.4 Tests de integración del router `GET /{materia_id}/activo`:
  - Con versión activa → 200 con entradas (email descifrado)
  - Sin versión activa → 404
  - Sin permiso `padron:leer` → 403
- [x] 10.5 Test de reemplazo de versión (upsert destructivo RN-05): importar dos veces y verificar que solo queda una versión activa, la anterior con `activa=false`
- [x] 10.6 Test de `DELETE /{materia_id}/activo`:
  - Vaciar propio → 204 y versión soft-deleted
  - Intentar vaciar de otro usuario → 403
- [x] 10.7 Tests del `MoodleWSClient` con `respx` (mock httpx):
  - `get_course_participants` exitoso → lista de dicts
  - Moodle responde 403 → excepción tipada `MoodleAuthError`
  - Timeout → excepción tipada `MoodleUnavailableError`
- [x] 10.8 Test de integración `POST /{materia_id}/importar-moodle`:
  - Config Moodle no configurada → 422
  - Moodle auth error → 503
  - Éxito → 201

## 11. Auditoría

- [x] 11.1 Registrar evento `PADRON_IMPORTADO` en el servicio de importación (archivo y Moodle) con `payload: {version_id, total_entradas, fuente: "archivo"|"moodle"}`
- [x] 11.2 Registrar evento `PADRON_VACIADO` en el servicio de vaciado con `payload: {version_id, materia_id}`
