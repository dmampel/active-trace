# Tasks: C-02 Core Models y Tenancy

## Execution Plan

### 1. Setup Cryptography & Security Helper
- [x] Instalar la librería `cryptography` (`uv add cryptography`) en el contenedor del backend.
- [ ] Implementar `backend/app/core/security.py` con `AES256Cipher` y sus métodos estáticos.
- [ ] Escribir `backend/tests/core/test_security_aes.py` verificando el cifrado bidireccional y el rechazo de claves incorrectas.

### 2. Tenancy Exceptions & Core
- [x] Implementar `backend/app/core/tenancy.py` declarando la excepción `MissingTenantScopeError`.

### 3. SQLAlchemy Base Models & Mixins
- [x] Modificar `backend/app/models/__init__.py` para exportar clases base.
- [x] Crear `backend/app/models/base.py` con `UUIDMixin`, `TimestampMixin`, `SoftDeleteMixin` y `TenantMixin`.
- [x] Crear el modelo raíz `backend/app/models/tenant.py` heredando de los mixins correspondientes.
- [x] Escribir `backend/tests/models/test_mixins.py` para asegurar que el base se comporta como se espera.

### 4. Generic Base Repository
- [x] Escribir `backend/app/repositories/base.py` con `BaseRepository[ModelType, CreateSchemaType, UpdateSchemaType]`.
- [x] Implementar validación estricta de `tenant_id` en el repositorio, levantando `MissingTenantScopeError` si aplica.
- [x] Implementar el borrado lógico (`soft delete`) y la ocultación por defecto en los `get` y `list`.
- [x] Escribir `backend/tests/repositories/test_base_repository.py` con tests de aislamiento multi-tenant y verificación de `deleted_at`.

### 5. Database Migration
- [x] Generar migración de Alembic para crear la tabla `tenant`.
- [x] Aplicar la migración y confirmar que la base de datos se levanta con la estructura correcta.

## Review Workload Forecast
- **Estimated changed lines:** ~350 lines
- **400-line budget risk:** Low
- **Chained PRs recommended:** No
- **Decision needed before apply:** No
