## ADDED Requirements

### Requirement: Catálogo administrable de roles y permisos

El sistema SHALL mantener un catálogo de roles (`Rol`) y permisos (`Permiso`) almacenados como datos en la base de datos, no hardcodeados en el código. La matriz rol × permiso (`RolPermiso`) DEBE ser administrable sin desplegar nueva versión.

Los roles canónicos del dominio son: ALUMNO, TUTOR, PROFESOR, COORDINADOR, NEXO, ADMIN, FINANZAS.

Los permisos siguen el patrón `modulo:accion` (e.g., `calificaciones:importar`, `auditoria:ver`).

#### Scenario: Rol existe en el catálogo
- **WHEN** el sistema arranca por primera vez con la migración 003 aplicada
- **THEN** existen exactamente 7 roles en la tabla `rol`: ALUMNO, TUTOR, PROFESOR, COORDINADOR, NEXO, ADMIN, FINANZAS

#### Scenario: Permisos del catálogo base
- **WHEN** la migración 003 fue aplicada
- **THEN** existen en la tabla `permiso` todos los permisos de la matriz canónica definida en `03_actores_y_roles.md §3.3`

#### Scenario: Matriz rol × permiso seed
- **WHEN** la migración 003 fue aplicada
- **THEN** la tabla `rol_permiso` tiene las asociaciones canónicas de la KB (ALUMNO → `avisos:confirmar`, ADMIN → `estructura:gestionar`, etc.)

---

### Requirement: Asignación de roles a usuarios con vigencia

El sistema SHALL permitir asignar uno o más roles a un usuario dentro de un tenant, con fecha de inicio (`desde`) obligatoria y fecha de fin (`hasta`) opcional. Una asignación es vigente si la fecha actual está comprendida dentro del rango.

#### Scenario: Usuario sin asignación vigente no tiene permisos
- **WHEN** un usuario existe pero no tiene ninguna asignación vigente en `user_rol`
- **THEN** `get_effective_permissions(user_id, tenant_id)` retorna un conjunto vacío

#### Scenario: Usuario con rol ADMIN obtiene permisos de ADMIN
- **WHEN** un usuario tiene una asignación vigente con rol ADMIN
- **THEN** `get_effective_permissions` incluye `estructura:gestionar`, `usuarios:gestionar`, `tenant:configurar`, entre otros

#### Scenario: Asignación vencida no otorga permisos
- **WHEN** un usuario tiene una asignación con `hasta` en el pasado
- **THEN** ese rol no contribuye a los permisos efectivos

#### Scenario: Usuario con múltiples roles obtiene unión de permisos
- **WHEN** un usuario tiene asignaciones vigentes con roles PROFESOR y COORDINADOR
- **THEN** `get_effective_permissions` incluye la unión de los permisos de ambos roles

---

### Requirement: Guard declarativo require_permission

El sistema SHALL proveer una dependency factory `require_permission(permission: str)` que protege endpoints FastAPI. Fail-closed: si el usuario autenticado no tiene el permiso declarado → 403. Si no está autenticado → 401.

#### Scenario: Usuario con permiso accede al endpoint
- **WHEN** un usuario con rol ADMIN hace una request a un endpoint protegido con `require_permission("estructura:gestionar")`
- **THEN** la request es procesada (HTTP 2xx)

#### Scenario: Usuario sin permiso recibe 403
- **WHEN** un usuario con rol ALUMNO hace una request a un endpoint protegido con `require_permission("calificaciones:importar")`
- **THEN** la response es HTTP 403 Forbidden

#### Scenario: Request sin token recibe 401
- **WHEN** una request llega a un endpoint protegido con `require_permission(...)` sin header Authorization
- **THEN** la response es HTTP 401 Unauthorized

#### Scenario: Fail-closed — permiso no declarado en catálogo
- **WHEN** el endpoint declara un permiso que no existe en la tabla `permiso`
- **THEN** la response es HTTP 403 Forbidden (no se concede acceso por defecto)

---

### Requirement: Resolución server-side de permisos efectivos

El sistema SHALL resolver los permisos efectivos de un usuario consultando la DB en cada request protegida. Los permisos NO se almacenan en el JWT ni en sesión del cliente.

La resolución aplica solo asignaciones vigentes (`desde <= hoy <= hasta OR hasta IS NULL`) y acotadas al `tenant_id` del usuario autenticado. Esto incluye **dos planos** de asignación de rol:

1. **Rol global de tenant** (`user_rol`): roles del usuario sin contexto académico.
2. **Asignación contextual** (`asignacion`): roles del usuario dentro de un contexto académico (materia/carrera/cohorte/comisiones).

En ambos planos, una asignación cuya vigencia esté vencida (`hasta` en el pasado) NO contribuye a los permisos efectivos, aunque el registro se conserve en el histórico (no se borra).

#### Scenario: Revocación de rol es efectiva en la siguiente request
- **WHEN** se elimina una asignación vigente de un usuario con rol PROFESOR
- **THEN** la siguiente request del usuario a un endpoint `require_permission("calificaciones:importar")` recibe 403

#### Scenario: Permisos acotados por tenant
- **WHEN** el usuario pertenece al tenant A y tiene rol ADMIN en tenant A
- **THEN** el guard no le concede permisos en endpoints de otros tenants

#### Scenario: Asignación contextual vencida no otorga permisos
- **WHEN** un usuario tiene una `asignacion` con rol PROFESOR cuyo `hasta` está en el pasado
- **THEN** esa asignación no contribuye a los permisos efectivos del usuario, pero el registro permanece en el histórico

#### Scenario: Asignación contextual vigente otorga permisos del rol
- **WHEN** un usuario tiene una `asignacion` vigente con rol PROFESOR en una materia
- **THEN** los permisos del rol PROFESOR se incluyen en sus permisos efectivos mientras la asignación esté vigente

---

### Requirement: Claim `roles` en JWT poblado con roles vigentes

El sistema SHALL incluir en el claim `roles` del access token la lista de nombres de roles vigentes del usuario al momento del login o refresh. Este claim es informativo (para la UI y logs) — la autorización siempre se resuelve desde la DB.

#### Scenario: Login retorna JWT con roles del usuario
- **WHEN** un usuario con rol COORDINADOR hace login exitoso
- **THEN** el access token decodificado tiene `roles: ["COORDINADOR"]`

#### Scenario: Usuario con múltiples roles vigentes
- **WHEN** un usuario tiene asignaciones vigentes con PROFESOR y TUTOR
- **THEN** el access token tiene `roles: ["PROFESOR", "TUTOR"]`

#### Scenario: Usuario sin asignaciones vigentes
- **WHEN** un usuario no tiene asignaciones vigentes
- **THEN** el access token tiene `roles: []`
