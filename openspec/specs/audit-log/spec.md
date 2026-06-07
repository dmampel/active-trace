# Audit Log Specification

## Purpose
Define el log de auditoría append-only de activia-trace (E-AUD): modelo inmutable, helper de registro, soporte de impersonación, y aislamiento multi-tenant. Toda acción significativa del sistema queda registrada con quién, qué, cuándo, desde dónde y cuántas filas afectó.

## Requirements

### Requirement: Registro append-only de acciones significativas
El sistema SHALL mantener un log de auditoría donde cada registro es inmutable. El sistema SHALL rechazar cualquier intento de UPDATE o DELETE sobre `AuditLog` tanto a nivel de aplicación como a nivel de base de datos.

#### Scenario: Registro de acción con todos los campos
- **WHEN** un servicio llama `record_audit(db, current_user, action="CALIFICACIONES_IMPORTAR", detail={"archivo": "padron.xlsx"}, rows_affected=42, materia_id=uuid, request=request)`
- **THEN** se crea un registro en `audit_log` con `actor_id=current_user.id`, `tenant_id=current_user.tenant_id`, `accion="CALIFICACIONES_IMPORTAR"`, `filas_afectadas=42`, `ip` e `user_agent` extraídos del request, y `impersonado_id=None`

#### Scenario: Registro de acción sin materia
- **WHEN** un servicio llama `record_audit(...)` con `materia_id=None`
- **THEN** el campo `materia_id` queda NULL en el registro; el resto se graba normalmente

#### Scenario: Intento de UPDATE rechazado a nivel app
- **WHEN** se llama al método `update()` de `AuditLogRepository` con cualquier argumento
- **THEN** el sistema lanza `NotImplementedError` con mensaje "AuditLog es append-only — no se permite UPDATE"

#### Scenario: Intento de DELETE rechazado a nivel app
- **WHEN** se llama al método `delete()` de `AuditLogRepository` con cualquier argumento
- **THEN** el sistema lanza `NotImplementedError` con mensaje "AuditLog es append-only — no se permite DELETE"

#### Scenario: Intento de UPDATE rechazado a nivel DB
- **WHEN** se ejecuta un `UPDATE audit_log SET ...` directamente en la base de datos
- **THEN** el trigger lanza una excepción y la operación es abortada

#### Scenario: Intento de DELETE rechazado a nivel DB
- **WHEN** se ejecuta un `DELETE FROM audit_log WHERE ...` directamente en la base de datos
- **THEN** el trigger lanza una excepción y la operación es abortada

---

### Requirement: Aislamiento multi-tenant del log
El sistema SHALL garantizar que los registros de auditoría de un tenant NO sean accesibles desde otro tenant. Cada registro SHALL tener `tenant_id` correspondiente al tenant del actor.

#### Scenario: Registro queda en el tenant correcto
- **WHEN** un usuario del tenant A realiza una acción auditada
- **THEN** el registro de `audit_log` tiene `tenant_id = A`

#### Scenario: Sin cross-tenant reads
- **WHEN** `AuditLogRepository` consulta registros con `tenant_id = A`
- **THEN** solo retorna registros con `tenant_id = A`, nunca de otro tenant

---

### Requirement: Registro de inicio de impersonación
El sistema SHALL registrar con código `IMPERSONACION_INICIAR` cuando un actor real inicia una sesión de impersonación sobre otro usuario.

#### Scenario: Audit log al iniciar impersonación
- **WHEN** el actor real llama `POST /auth/impersonate` exitosamente
- **THEN** se crea un registro con `accion="IMPERSONACION_INICIAR"`, `actor_id=real_user.id`, `impersonado_id=target_user.id`, y `detalle={"target_user_id": str(target_user.id)}`

---

### Requirement: Registro de fin de impersonación
El sistema SHALL registrar con código `IMPERSONACION_FINALIZAR` cuando se termina una sesión de impersonación.

#### Scenario: Audit log al finalizar impersonación
- **WHEN** el actor real llama `POST /auth/impersonate/end` con token de impersonación activo
- **THEN** se crea un registro con `accion="IMPERSONACION_FINALIZAR"`, `actor_id=real_user.id`, `impersonado_id=target_user.id`

---

### Requirement: Atribución correcta bajo impersonación
Cuando hay una sesión de impersonación activa, el sistema SHALL atribuir las acciones auditadas al actor real (quien impersona), NO al usuario impersonado.

#### Scenario: Acción bajo impersonación atribuida al actor real
- **WHEN** el actor real A está impersonando al usuario B, y se registra una acción auditada
- **THEN** el registro de `audit_log` tiene `actor_id=A.id` e `impersonado_id=B.id`

#### Scenario: Acción sin impersonación no tiene impersonado_id
- **WHEN** un usuario actúa en una sesión normal (sin impersonación)
- **THEN** el campo `impersonado_id` del registro de audit log es NULL
