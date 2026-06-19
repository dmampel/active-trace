## Why

La plataforma no tiene mecanismo para publicar avisos institucionales dirigidos a segmentos específicos de usuarios. Coordinadores y admins necesitan anunciar novedades con ventana de visibilidad controlada, segmentación por audiencia (alcance global / por materia / por cohorte / por rol), niveles de severidad y seguimiento de confirmación de lectura obligatoria.

## What Changes

- Nuevo modelo `Aviso`: título, cuerpo enriquecido, alcance (Global | PorMateria | PorCohorte | PorRol), `materia_id`, `cohorte_id`, `rol_destino`, severidad (Info | Advertencia | Crítico), `inicio_en`, `fin_en`, `orden`, `activo`, `requiere_ack`.
- Nuevo modelo `AcknowledgmentAviso`: `aviso_id`, `usuario_id`, `confirmado_at`. Los contadores de vistas y confirmaciones se derivan de esta tabla; no hay campos denormalizados.
- ABM de avisos (`POST /api/avisos/`, `GET /api/avisos/`, `GET /api/avisos/{id}`, `PATCH /api/avisos/{id}`, `DELETE /api/avisos/{id}`) protegidos con `avisos:publicar` (COORDINADOR / ADMIN).
- Endpoint de visualización para destinatarios (`GET /api/avisos/mis-avisos`) filtrado por rol/alcance/cohorte del usuario autenticado y ventana de vigencia activa.
- Endpoint de confirmación de lectura (`POST /api/avisos/{id}/ack`) disponible para cualquier usuario autenticado que sea destinatario del aviso.
- Migración Alembic `015: aviso, acknowledgment_aviso`.
- Tests: filtrado por scope, ventana de vigencia (fuera de rango no se muestra), ack (deja de aparecer + contadores), orden de prioridad.

## Capabilities

### New Capabilities
- `avisos-y-acknowledgment`: Gestión completa de avisos institucionales segmentados con ventana de vigencia y confirmación de lectura (acknowledgment).

### Modified Capabilities

(ninguna — este change no altera requerimientos de specs existentes)

## Impact

- **Nuevas tablas**: `aviso`, `acknowledgment_aviso`.
- **Nuevos módulos backend**: `models/aviso.py`, `schemas/aviso.py`, `repositories/aviso_repository.py`, `services/aviso_service.py`, `routers/avisos.py`.
- **Migración**: `backend/alembic/versions/…_015_avisos_acknowledgment.py`.
- **Dependencias**: C-06 (estructura-academica) para FKs a `Materia` y `Cohorte`; C-04 (rbac) para el guard `avisos:publicar`.
- **APIs afectadas**: ninguna existente se modifica; se agregan rutas nuevas bajo `/api/avisos`.
