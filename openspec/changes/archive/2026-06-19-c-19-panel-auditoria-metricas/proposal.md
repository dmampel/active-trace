## Why

El sistema ya escribe `AuditLog` (C-05) de forma append-only en cada acción significativa (RN-23/24), pero hoy NADIE puede leerlo: no existe ningún endpoint de lectura ni panel de supervisión. ADMIN, COORDINADOR y FINANZAS no tienen forma de responder "¿qué hizo cada docente?", "¿qué materias están inactivas?" ni "¿qué comunicaciones fallaron?". C-19 abre esa ventana de lectura sobre el log existente: dashboards de uso (F9.1) y log completo con filtros (F9.2), respetando el scope `(propio)` del coordinador.

## What Changes

- Nueva capacidad de **lectura sobre `AuditLog`** (solo lectura — el log sigue siendo append-only; ningún endpoint de C-19 escribe, actualiza ni borra registros).
- Nuevo permiso RBAC `auditoria:ver`, asignado a **ADMIN**, **COORDINADOR** (con scope `(propio)`) y **FINANZAS**, vía migración Alembic que siembra el permiso y sus `rol_permiso` (mismo patrón que `010_analisis_permiso`).
- Nuevos endpoints bajo `/api/v1/auditoria/*` con guard `auditoria:ver` (fail-closed → 403):
  - **Panel de interacciones (F9.1)**:
    - Acciones por día (serie temporal de volumen de uso).
    - Estado de comunicaciones agrupado por docente (Pendiente / Enviando / Enviado / Error / Cancelado).
    - Interacciones por docente × materia (conteo por código de acción).
    - Log de últimas acciones (límite configurable, por defecto **200**, con cap máximo para evitar abuso).
  - **Log completo (F9.2)**: listado paginado con filtros por rango de fechas, materia, usuario y estado.
- **Scope `(propio)` del COORDINADOR**: un coordinador solo ve auditoría de las materias que coordina (asignaciones COORDINADOR vigentes). ADMIN y FINANZAS ven todo el tenant. Todo filtrado siempre por `tenant_id` de la sesión.
- Identidad, roles y tenant SIEMPRE desde el JWT verificado; nunca de URL/body/header.

## Capabilities

### New Capabilities
- `panel-auditoria`: lectura y agregación del log de auditoría — dashboards de uso (acciones por día, estado de comunicaciones por docente, interacciones por docente×materia, log de últimas acciones con límite configurable) y log completo con filtros (fechas, materia, usuario, estado), con scope `(propio)` para COORDINADOR y permiso `auditoria:ver`.

### Modified Capabilities
<!-- Ninguna. C-19 no modifica requisitos de capacidades existentes: solo lee el AuditLog escrito por C-05 y reutiliza el RBAC de C-04. El nuevo permiso se siembra, no cambia el contrato del módulo RBAC. -->

## Impact

- **Código nuevo (backend)**:
  - `app/api/v1/routers/auditoria.py` — router de solo lectura con guard `auditoria:ver`.
  - `app/services/auditoria_service.py` — orquesta repositorio + resuelve scope `(propio)` del coordinador.
  - `app/repositories/auditoria_repository.py` — queries de agregación y filtro sobre `AuditLog` (nuevo; el `audit_log_repository.py` actual es append-only de escritura).
  - `app/schemas/auditoria.py` — DTOs Pydantic v2 (`extra='forbid'`) de request/response.
  - `app/core/config.py` — parámetro de límite máximo/por-defecto del log de últimas acciones.
  - Migración Alembic `019_auditoria_permiso` (down_revision `b2c3d4e5f6a7`) que siembra `auditoria:ver` → ADMIN, COORDINADOR, FINANZAS. **Sin cambios de tablas** (C-19 solo lee `AuditLog` existente).
- **Datos leídos**: `audit_log` (modelo de C-05), `comunicacion` (para estado por docente), `asignacion` (para resolver scope `(propio)` del coordinador). Todo scopeado por `tenant_id`.
- **Frontend**: ninguno en este change — el panel ADMIN lo consume C-24 (`frontend-finanzas-y-admin`), que depende de C-19.
- **Dependencias**: C-07 (usuarios y asignaciones) ✓, C-05 (audit-log) ✓. Sin cambios en integraciones externas (Moodle/N8N).
- **Governance**: ALTO (toca el dominio de auditoría). Solo lectura sobre log inmutable; cero superficie de escritura.
