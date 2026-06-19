## 1. Modelos y migración (mensajería)

- [x] 1.1 Crear modelo SQLAlchemy `HiloMensaje` (`id` UUID, `tenant_id`, `asunto`, `creado_por` FK Usuario, `created_at`, `deleted_at`) en el módulo de mensajeria
- [x] 1.2 Crear modelo SQLAlchemy `MensajeInterno` (`id` UUID, `tenant_id`, `hilo_id` FK, `autor_id` FK, `destinatario_id` FK, `cuerpo`, `leido` bool, `created_at`, `deleted_at`)
- [x] 1.3 Generar una única migración Alembic para `hilo_mensaje` y `mensaje_interno` (índices por `tenant_id`, `destinatario_id`, `hilo_id`)
- [x] 1.4 Agregar permisos `perfil:editar` e `inbox:usar` al catálogo/seed RBAC (patrón C-04)

## 2. Perfil propio — schemas y repository

- [x] 2.1 Definir schemas Pydantic `PerfilRead` (incluye `cuil` descifrado) y `PerfilUpdate` (sin `cuil`, `extra='forbid'`, mapeo `modalidad_cobro`→`facturador`)
- [x] 2.2 Reusar/extender el repository de `Usuario` para lectura/actualización por id derivado del JWT, filtrando por `tenant_id`

## 3. Perfil propio — service y router (TDD)

- [x] 3.1 RED+GREEN: service `leer_perfil` que resuelve el usuario desde el JWT y descifra PII propia (incluido `cuil`)
- [x] 3.2 RED+GREEN: service `actualizar_perfil` que actualiza solo campos editables, recifra PII y valida unicidad `(tenant_id, email)` (409 en duplicado)
- [x] 3.3 RED+GREEN: router `GET /api/v1/perfil` con `require_permission('perfil:editar')`, identidad desde JWT
- [x] 3.4 RED+GREEN: router `PATCH /api/v1/perfil` con `require_permission('perfil:editar')`
- [x] 3.5 Test: intento de modificar `cuil` → 422; campo no declarado → 422 (`extra='forbid'`)
- [x] 3.6 Test: PII (`dni`/`cbu`/`alias_cbu`) cifrada en reposo y ausente en texto plano en logs
- [x] 3.7 Test: identidad siempre desde JWT (ignora `usuario_id`/`legajo` en query/body/header); sin JWT → 401

## 4. Mensajería interna — repository (TDD)

- [x] 4.1 RED+GREEN: repository de hilos/mensajes filtrado por `tenant_id` por defecto y por participación del usuario
- [x] 4.2 RED+GREEN: query de hilos donde el usuario es destinatario; soft delete respetado (excluye `deleted_at` no nulo)

## 5. Mensajería interna — service y router (TDD)

- [x] 5.1 RED+GREEN: service+router `GET /api/v1/inbox` lista hilos recibidos del usuario del JWT (`require_permission('inbox:usar')`)
- [x] 5.2 RED+GREEN: service+router `GET /api/v1/inbox/{hilo_id}` devuelve mensajes ordenados y marca `leido=true` los dirigidos al usuario
- [x] 5.3 RED+GREEN: service+router `POST /api/v1/inbox/{hilo_id}/responder` agrega mensaje al hilo (`autor_id` del JWT, schema `extra='forbid'`)
- [x] 5.4 RED+GREEN: service+router `POST /api/v1/inbox` crea hilo + primer mensaje hacia un destinatario del mismo tenant
- [x] 5.5 Test aislamiento por usuario: hilo ajeno no aparece en inbox y su acceso directo → 404
- [x] 5.6 Test aislamiento por tenant: hilos de otro tenant nunca visibles ni accesibles
- [x] 5.7 Test: responder/leer en hilo donde no se participa → 404; destinatario de otro tenant en `POST /api/v1/inbox` → 404/422

## 6. Sesión y cierre (F11.3)

- [x] 6.1 Verificar que el logout de C-03 cubre F11.3 (cierre de sesión explícito); documentar reuso sin código nuevo

## 7. Cierre del change

- [x] 7.1 Cobertura: ≥80% líneas y ≥90% reglas de negocio en perfil e inbox
- [x] 7.2 Verificar todos los escenarios de las specs `perfil-propio` y `mensajeria-interna` cubiertos por tests
- [x] 7.3 Marcar `[x]` C-20 en CHANGES.md
