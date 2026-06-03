## MODIFIED Requirements

### Requirement: JWT access token contiene roles vigentes del usuario

El access token SHALL incluir en el claim `roles` la lista de nombres de roles vigentes del usuario (asignaciones activas en `user_rol` al momento del login o refresh). Antes de C-04, este claim siempre era `[]`.

El claim `roles` es informativo — NO es la fuente de autorización. La autorización se resuelve siempre desde la DB via `require_permission`.

#### Scenario: Login sin 2FA emite token con roles vigentes
- **WHEN** un usuario con asignación vigente de rol COORDINADOR hace login exitoso (sin 2FA)
- **THEN** el access token decodificado contiene `roles: ["COORDINADOR"]`

#### Scenario: Refresh rota y emite token con roles actualizados
- **WHEN** un usuario rota su refresh token
- **THEN** el nuevo access token contiene los roles vigentes al momento del refresh (no los del login original)

#### Scenario: Usuario sin asignaciones vigentes tiene roles vacíos
- **WHEN** un usuario autenticado no tiene ninguna asignación vigente en `user_rol`
- **THEN** el access token tiene `roles: []` y el guard `require_permission` retorna 403 para cualquier endpoint protegido
