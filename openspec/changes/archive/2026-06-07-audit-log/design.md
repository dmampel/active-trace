## Context

C-01→C-04 están archivados: tenemos foundation, modelos base con tenant isolation, JWT auth con `get_current_user`, y RBAC fino. Con la identidad del actor resuelta desde el JWT y los roles disponibles por dependency injection, podemos registrar acciones significativas con atribución correcta.

El `AuditLog` (E-AUD) es el registro de trazabilidad central de la plataforma. Toda acción con impacto en datos debe quedar registrada con quién, qué, cuándo, desde dónde, y cuántas filas afectó. No puede modificarse ni borrarse — nunca.

## Goals / Non-Goals

**Goals:**
- Modelo `AuditLog` append-only con protección doble (app + DB trigger).
- Helper `audit_action(...)` invocable desde cualquier servicio sin boilerplate.
- Soporte de impersonación: JWT extendido con `impersonado_id`, endpoints para iniciar/finalizar sesión, atribución siempre al actor real.
- Migración `003_audit_log` con tabla y trigger de protección.
- Tests que cubran: append-only enforced, atribución bajo impersonación, registro con código + filas, aislamiento por tenant.

**Non-Goals:**
- API de consulta del audit log (diferida a C-19 panel-auditoria-metricas).
- Captura automática de todas las requests HTTP (demasiado ruido; solo acciones significativas).
- Políticas de retención o archivado (sin límite de retención por decisión de producto).
- Auditoría de accesos de solo lectura (solo escrituras/acciones críticas).

## Decisions

### D-1: Protección append-only en dos capas

**Opción elegida**: restricción en repositorio + trigger PostgreSQL.

- **Capa app**: `AuditLogRepository` override de `update()` y `delete()` para lanzar `NotImplementedError` con mensaje claro. Esto bloquea el path normal de código.
- **Capa DB**: trigger `BEFORE UPDATE OR DELETE ON audit_log` que hace `RAISE EXCEPTION`. Esto garantiza inmutabilidad incluso con SQL directo o herramientas externas.

**Alternativa descartada**: solo capa app — insuficiente para un requisito de compliance; no protege contra acceso directo a DB.

**Alternativa descartada**: PostgreSQL row-level security — más complejo de configurar y no aporta ventaja sobre el trigger para este caso.

### D-2: Helper de auditoría como función async, no decorator

**Opción elegida**: `record_audit(db, current_user, action, detail, rows_affected, materia_id, request)` — función async llamada explícitamente desde el servicio.

**Por qué no decorator**: los decorators en async FastAPI tienen friction con la inyección de dependencias (no tienen acceso a `db`, `current_user`, ni `request` del contexto de FastAPI). Una función explícita es más testeable y más clara sobre cuándo y qué se audita.

**Convención de uso**: el servicio llama `await record_audit(...)` justo antes de hacer `return`. El router inyecta `db`, `current_user` y `request`, y los pasa al servicio.

### D-3: Impersonación via JWT extendido

**Opción elegida**: el endpoint `POST /auth/impersonate` emite un nuevo JWT de corta duración (TTL 60 min) con claim adicional `impersonado_id`. `get_current_user` lee este claim y lo expone en `CurrentUser.impersonado_id`.

**Por qué JWT y no session store**: mantiene el diseño stateless existente. El claim viaja en el token y `get_current_user` lo resuelve sin consultar DB adicional.

**Restricción de seguridad**: el token de impersonación no puede usarse para obtener otro token de impersonación (no nested impersonation). `get_current_user` verifica que si hay `impersonado_id`, el actor NO puede llamar `POST /auth/impersonate` de nuevo.

**Atribución**: `actor_id = sub del JWT (usuario real)`, `impersonado_id = claim del JWT`. El `record_audit` siempre usa `actor_id` como el actor real.

### D-4: Catálogo de códigos como constantes Python

Los códigos de acción (`CALIFICACIONES_IMPORTAR`, etc.) viven en `app/core/audit.py` como constantes de módulo, no en DB. El catálogo es código — no configuración runtime.

**Racional**: la KB lo define como "administrable y mantenido en documentación técnica". En la práctica, para este MVP, las constantes en código versionado son más seguras y fáciles de auditar.

## Risks / Trade-offs

- **Escritura en el path crítico** → el INSERT de audit log ocurre sincrónicamente en la request. Si la DB está lenta, el endpoint sufre. *Mitigación*: el INSERT es un single-row, índice por `tenant_id + fecha_hora`. Para volúmenes altos futuros, considerar escritura async via worker (diferido a C-12).
- **Campos nullable** → `materia_id`, `impersonado_id` y `filas_afectadas` son nullable. Acciones que no aplican a una materia o no tienen impersonación dejan esos campos en NULL — esto es correcto y esperado.
- **`impersonado_id` en JWT** → si el token con impersonación se filtra, el receptor puede operar como otro usuario hasta que expire (máx 60 min). *Mitigación*: TTL corto + endpoint `POST /auth/impersonate/end` que el actor real puede llamar para invalidar el token activo (revocación vía refresh token del actor real).

## Migration Plan

1. `alembic revision --autogenerate -m "003_audit_log"` — generar migración.
2. Agregar manualmente el trigger de protección en la migración (Alembic no lo detecta automáticamente).
3. En tests: la migración se aplica via `async_engine` con `run_sync(target_metadata.create_all)` igual que C-02/C-03 — el trigger se define en `op.execute()` dentro de `upgrade()`.
4. No hay rollback peligroso: `downgrade()` hace `DROP TABLE audit_log CASCADE` (tabla nueva, sin dependencias aún).

## Open Questions

- Ninguna bloqueante para C-05. La semántica completa de impersonación (qué roles pueden impersonar a cuáles) es configurable por tenant en el futuro pero el permiso `impersonacion:usar` es suficiente para este change.
