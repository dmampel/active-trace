## 1. Migración Alembic

- [x] 1.1 Crear migración `005_estructura_academica.py` con tablas `carrera`, `cohorte`, `materia`, `instancia_dictado`
- [x] 1.2 Agregar índices: `(tenant_id)` en cada tabla, `(tenant_id, codigo)` en carrera y materia, `(tenant_id, carrera_id, nombre)` en cohorte, `(tenant_id, materia_id, cohorte_id, periodo)` en instancia_dictado
- [x] 1.3 Agregar constraints únicos correspondientes a los índices anteriores
- [x] 1.4 Agregar INSERT de los 4 permisos `estructura:leer|crear|editar|eliminar` en tabla `permission`
- [x] 1.5 Asignar permisos a roles en tabla `role_permission`: ADMIN(4), COORDINADOR(3: leer+crear+editar), PROFESOR(1: leer), TUTOR(1: leer)
- [x] 1.6 Implementar `downgrade()` que revierte tablas e inserts de permisos

## 2. Modelos SQLAlchemy

- [x] 2.1 Crear `app/models/estructura.py` con clases `Carrera`, `Cohorte`, `Materia`, `InstanciaDictado` usando `UUIDMixin + TimestampMixin + SoftDeleteMixin + TenantMixin`
- [x] 2.2 Definir `Carrera`: campos `codigo: str`, `nombre: str`, `estado: enum(Activa|Inactiva)`
- [x] 2.3 Definir `Cohorte`: campos `carrera_id: UUID (FK, NOT NULL)`, `nombre: str`, `anio: int`, `vig_desde: date`, `vig_hasta: date | None`, `estado: enum`
- [x] 2.4 Definir `Materia`: campos `codigo: str`, `nombre: str`, `estado: enum`
- [x] 2.5 Definir `InstanciaDictado`: campos `materia_id: UUID (FK)`, `cohorte_id: UUID (FK)`, `nombre: str`, `periodo: str`, `estado: enum`
- [x] 2.6 Exportar los 4 modelos desde `app/models/__init__.py`

## 3. Schemas Pydantic

- [x] 3.1 Crear `app/schemas/estructura.py` con schemas Request/Response para `Carrera` (Create, Update, Read)
- [x] 3.2 Crear schemas para `Cohorte` (Create, Update, Read) — `carrera_id` requerido en Create
- [x] 3.3 Crear schemas para `Materia` (Create, Update, Read)
- [x] 3.4 Crear schemas para `InstanciaDictado` (Create, Update, Read) — `materia_id`, `cohorte_id`, `periodo` requeridos en Create
- [x] 3.5 Todos los schemas con `model_config = ConfigDict(extra='forbid')`

## 4. Repositorios

- [x] 4.1 Crear `app/repositories/estructura_repository.py` con `CarreraRepository`; métodos: `create`, `get_by_id`, `list_active`, `update`, `soft_delete`; filtrar siempre por `tenant_id`
- [x] 4.2 Agregar `CohorteRepository` al mismo archivo; `list_active` acepta `carrera_id` opcional como filtro
- [x] 4.3 Agregar `MateriaRepository`; mismo patrón
- [x] 4.4 Agregar `InstanciaDictadoRepository`; `list_active` acepta `cohorte_id` y `materia_id` como filtros opcionales
- [x] 4.5 Cada `create` verifica unicidad antes de insertar y lanza `IntegrityError`-safe (deja que el constraint de DB maneje; captura en service)

## 5. Servicio

- [x] 5.1 Crear `app/services/estructura_service.py` con `EstructuraService`
- [x] 5.2 Método `create_carrera`: delega a repo, captura constraint único → `HTTPException(409)`, audita `ESTRUCTURA_CARRERA_CREAR`
- [x] 5.3 Método `create_cohorte`: valida que `carrera_id` exista en el tenant, captura constraint → 409, audita `ESTRUCTURA_COHORTE_CREAR`
- [x] 5.4 Método `create_materia`: captura constraint → 409, audita `ESTRUCTURA_MATERIA_CREAR`
- [x] 5.5 Método `create_instancia`: valida `materia_id` y `cohorte_id` en tenant, captura constraint → 409, audita `ESTRUCTURA_INSTANCIA_CREAR`
- [x] 5.6 Métodos `update_*` y `delete_*` para cada entidad con auditoría correspondiente (`_EDITAR`, `_ELIMINAR`)

## 6. Router REST

- [x] 6.1 Crear `app/api/v1/routers/estructura.py` con `APIRouter(prefix="/estructura", tags=["estructura"])`
- [x] 6.2 Endpoints Carrera: `POST /carreras`, `GET /carreras`, `GET /carreras/{id}`, `PATCH /carreras/{id}`, `DELETE /carreras/{id}` — guards con `require_permission`
- [x] 6.3 Endpoints Cohorte: `POST /cohortes`, `GET /cohortes`, `GET /cohortes/{id}`, `PATCH /cohortes/{id}`, `DELETE /cohortes/{id}`
- [x] 6.4 Endpoints Materia: `POST /materias`, `GET /materias`, `GET /materias/{id}`, `PATCH /materias/{id}`, `DELETE /materias/{id}`
- [x] 6.5 Endpoints InstanciaDictado: `POST /instancias`, `GET /instancias`, `GET /instancias/{id}`, `PATCH /instancias/{id}`, `DELETE /instancias/{id}`
- [x] 6.6 Registrar el router en `app/main.py` bajo `/api/v1`

## 7. Tests — Migración y Modelos

- [x] 7.1 Test: migración Alembic `upgrade` + `downgrade` en SQLite de test no lanza errores
- [x] 7.2 Test: crear `Carrera` con datos válidos persiste en DB
- [x] 7.3 Test: constraint único `(tenant_id, codigo)` en Carrera lanza error si se duplica
- [x] 7.4 Test: `InstanciaDictado` constraint único `(tenant_id, materia_id, cohorte_id, periodo)` se verifica en DB

## 8. Tests — Repositorios

- [x] 8.1 Test: `CarreraRepository.list_active` retorna solo registros del tenant correcto y sin `deleted_at`
- [x] 8.2 Test: `CohorteRepository.list_active` filtra por `carrera_id` correctamente
- [x] 8.3 Test: `soft_delete` setea `deleted_at` y el registro desaparece de `list_active`
- [x] 8.4 Test: `InstanciaDictadoRepository.list_active` filtra por `cohorte_id`

## 9. Tests — Servicio y Endpoints

- [x] 9.1 Test: POST `/carreras` con datos válidos retorna 201 y el recurso creado
- [x] 9.2 Test: POST `/carreras` con código duplicado retorna 409
- [x] 9.3 Test: POST `/cohortes` con `carrera_id` de otro tenant retorna 422
- [x] 9.4 Test: POST `/instancias` con combinación duplicada retorna 409
- [x] 9.5 Test: GET `/carreras` sin token retorna 401
- [x] 9.6 Test: GET `/carreras` con token de rol PROFESOR retorna 200 (tiene `estructura:leer`)
- [x] 9.7 Test: POST `/carreras` con rol PROFESOR retorna 403
- [x] 9.8 Test: DELETE `/carreras/{id}` con rol COORDINADOR retorna 403
- [x] 9.9 Test: crear carrera genera entrada en AuditLog con `accion=ESTRUCTURA_CARRERA_CREAR`
- [x] 9.10 Test: DELETE `/instancias/{id}` con rol ADMIN retorna 204 y genera AuditLog
