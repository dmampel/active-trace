## MODIFIED Requirements

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
