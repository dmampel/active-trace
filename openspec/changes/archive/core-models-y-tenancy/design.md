# Design: C-02 Core Models y Tenancy

## Architecture

El diseño se centra en la capa de persistencia (SQLAlchemy) y la seguridad de datos en reposo (Fernet). Mantenemos la filosofía Clean Architecture: los modelos no tienen lógica de negocio, y los repositorios abstraen las consultas SQL.

### SQLAlchemy Mixins (`backend/app/models/base.py`)
Para evitar duplicación y estandarizar entidades, usaremos herencia de mixins:
- `UUIDMixin`: Agrega `id` de tipo `UUID` con un `default=uuid.uuid4`.
- `TimestampMixin`: Agrega `created_at` y `updated_at` (actualizado onupdate).
- `SoftDeleteMixin`: Agrega `deleted_at` nuleable.
- `TenantMixin`: Agrega `tenant_id` de tipo `UUID` como Foreign Key hacia `tenant.id`, con `index=True` para performance, ya que todas las consultas filtran por aquí.

### El Modelo Raíz (`backend/app/models/tenant.py`)
- Clase `Tenant(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin)` (el Tenant no lleva `TenantMixin` obviamente).
- Campos básicos: `name` (String, unique), `is_active` (Boolean).

### Base Repository (`backend/app/repositories/base.py`)
Un repositorio genérico fuertemente tipado: `BaseRepository[ModelType, CreateSchemaType, UpdateSchemaType]`.
- En todos los métodos de consulta (`get`, `list`, `delete`, `update`), el parámetro `tenant_id: UUID` debe ser provisto. 
- **Fallo Cerrado**: Si la entidad mapeada hereda de `TenantMixin` y `tenant_id` es nulo, el repositorio levantará `MissingTenantScopeError`.
- **Soft Delete Transparente**: Toda consulta (`select`) incluirá por defecto `where(Model.deleted_at.is_(None))` a menos que un flag explícito (`include_deleted=True`) lo desactive. El método `delete()` simplemente ejecuta un `update()` estableciendo `deleted_at = func.now()`.

### AES-256 Encryption Helper (`backend/app/core/security.py`)
- Clase `AES256Cipher` envolviendo `cryptography.fernet.Fernet`.
- Requiere `ENCRYPTION_KEY` de 32 bytes (base64 url-safe).
- Métodos estáticos: `encrypt(plaintext: str) -> str` y `decrypt(ciphertext: str) -> str`.
- Usaremos esto desde el `Service` o `Repository` antes de guardar y después de leer campos sensibles. (Por diseño, no usaremos SQLAlchemy `TypeDecorator` mágico para PII para mantener el cifrado explícito y auditable en la capa de negocio/repositorio, evitando problemas con consultas asíncronas complejas).

## Data Model Changes

### Nuevas Tablas:
1. `tenant`:
   - `id` (UUID, PK)
   - `name` (String, UK)
   - `is_active` (Boolean)
   - `created_at`, `updated_at`, `deleted_at` (Timestamps)

### Migraciones Alembic:
- Generar `001_tenant` manualmente (o via `--autogenerate`) incluyendo la inicialización del enum si aplicara (no aplica en este caso).

## Edge Cases & Limitations

- **Múltiples Tenants**: Al requerir `tenant_id` en todas partes, un endpoint administrativo (SuperAdmin) que deba consultar todos los tenants tendrá que usar un método de bypass específico en el repositorio o consultar pasando `tenant_id=None` pero con un flag `bypass_tenant_scope=True` que indique la intención explícita.
- **Transición de Claves de Cifrado (Key Rotation)**: Fernet soporta rotación nativa mediante `MultiFernet`. En C-02 implementaremos solo una clave simple (`Fernet`), dejando la rotación para una etapa futura de madurez de infraestructura si fuera necesario.

## Dependencies

- Python `cryptography` package.
- `SQLAlchemy` >= 2.0 (async).
