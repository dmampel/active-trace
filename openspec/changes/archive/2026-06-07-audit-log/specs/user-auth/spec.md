## ADDED Requirements

### Requirement: Iniciar sesión de impersonación
El sistema SHALL permitir que un usuario con permiso `impersonacion:usar` inicie una sesión de impersonación sobre otro usuario del mismo tenant. El sistema SHALL emitir un JWT de corta duración (TTL 60 min) con el `sub` del actor real y un claim adicional `impersonado_id`. El sistema SHALL registrar la acción en el audit log con código `IMPERSONACION_INICIAR`.

#### Scenario: Impersonación exitosa
- **WHEN** un usuario autenticado con permiso `impersonacion:usar` llama `POST /auth/impersonate` con `{"target_user_id": "<uuid>"}`
- **THEN** el sistema responde 200 con un `impersonate_token` JWT de 60 min, el audit log registra `IMPERSONACION_INICIAR`, y el JWT contiene `impersonado_id=target_user_id`

#### Scenario: Impersonación sin permiso
- **WHEN** un usuario sin permiso `impersonacion:usar` llama `POST /auth/impersonate`
- **THEN** el sistema responde 403

#### Scenario: Impersonación a usuario de otro tenant
- **WHEN** el actor intenta impersonar un `target_user_id` que pertenece a otro tenant
- **THEN** el sistema responde 404 (no revelar existencia de usuario cross-tenant)

#### Scenario: Impersonación anidada rechazada
- **WHEN** el actor ya tiene un token con `impersonado_id` activo e intenta llamar `POST /auth/impersonate`
- **THEN** el sistema responde 400 con error "No se puede impersonar desde una sesión de impersonación activa"

---

### Requirement: Finalizar sesión de impersonación
El sistema SHALL proveer un endpoint para que el actor real finalice la sesión de impersonación. El sistema SHALL registrar la acción en el audit log con código `IMPERSONACION_FINALIZAR`.

#### Scenario: Fin de impersonación exitoso
- **WHEN** el actor real llama `POST /auth/impersonate/end` con un token que tiene `impersonado_id`
- **THEN** el sistema responde 200, el audit log registra `IMPERSONACION_FINALIZAR`, y el `impersonate_token` queda descartado

#### Scenario: Fin de impersonación sin sesión activa
- **WHEN** un usuario sin sesión de impersonación llama `POST /auth/impersonate/end`
- **THEN** el sistema responde 400 con error "No hay sesión de impersonación activa"

---

### Requirement: `get_current_user` expone impersonado_id
La dependency `get_current_user` SHALL leer el claim `impersonado_id` del JWT (si presente) y exponerlo en el objeto `CurrentUser`. El `actor_id` del `CurrentUser` SHALL siempre ser el `sub` del JWT (usuario real), nunca el `impersonado_id`.

#### Scenario: Token con impersonado_id
- **WHEN** el JWT contiene el claim `impersonado_id`
- **THEN** `get_current_user` retorna `CurrentUser(id=sub, tenant_id=..., impersonado_id=impersonado_id)`

#### Scenario: Token normal sin impersonado_id
- **WHEN** el JWT no contiene el claim `impersonado_id`
- **THEN** `get_current_user` retorna `CurrentUser(id=sub, tenant_id=..., impersonado_id=None)`
