## Context

C-07 (usuarios-y-asignaciones) ya implementó el modelo `Usuario` con PII cifrada AES-256, multi-tenancy row-level y el ABM administrativo (`usuario-management`, permiso `usuarios:gestionar`). C-03/C-04 proveen JWT, RBAC fino fail-closed y logout. C-12 implementó `ComunicacionDocente` para los emails salientes a alumnos.

C-20 agrega dos capacidades de **autoservicio del usuario final**:
1. **Perfil propio** (F11.1): edición de los propios datos sin pasar por administración.
2. **Mensajería interna** (F3.4/F11.2/FL-10): inbox entre usuarios registrados, explícitamente **paralelo** a las comunicaciones a alumnos.

El cierre de sesión (F11.3) ya está cubierto por el logout de C-03 y no requiere código nuevo en este change.

Governance del dominio: **BAJO** (autoservicio, CRUDs sin lógica crítica). La única zona sensible es la PII del perfil, que reusa el cifrado ya existente de C-07.

## Goals / Non-Goals

**Goals:**
- Que el usuario del JWT lea y edite su propio perfil sobre el modelo `Usuario` existente, con `cuil` de solo lectura.
- Un inbox interno con hilos, lectura/marcado y respuesta, aislado por usuario y por tenant.
- Reusar cifrado PII, multi-tenancy, soft delete y RBAC ya existentes.

**Non-Goals:**
- NO se modifica el ABM administrativo de `usuario-management` ni las comunicaciones a alumnos (`ComunicacionDocente`).
- NO se implementa logout nuevo (reusa C-03).
- NO hay notificaciones push/email del inbox; el inbox es in-app.
- NO hay adjuntos ni mensajería grupal (multi-destinatario) en este change — un hilo tiene exactamente dos participantes (autor + destinatario).

## Decisions

**1. Perfil sobre el modelo `Usuario` existente, sin tabla nueva.**
El perfil es una vista de autoservicio del `Usuario` ya existente. Se agregan endpoints `/api/v1/perfil` que resuelven el id desde el JWT y reutilizan el repository de usuarios filtrado por tenant. Alternativa descartada: tabla `Perfil` separada → duplicaría PII y rompería la fuente única de verdad.

**2. `cuil` de solo lectura por schema, no por lógica imperativa.**
El schema Pydantic de actualización de perfil (`PerfilUpdate`) NO declara el campo `cuil`; con `extra='forbid'` cualquier intento de enviarlo retorna 422 automáticamente. El `cuil` sí se descifra y devuelve en `GET /api/v1/perfil`. `modalidad_cobro` (factura/liquidación) se mapea al booleano `facturador` del modelo existente. Alternativa descartada: validación manual en el service → más frágil y duplica lo que el schema ya garantiza.

**3. Dos tablas nuevas para mensajería: `hilo_mensaje` + `mensaje_interno`.**
Separar la conversación (hilo) de los mensajes permite ordenar cronológicamente, marcar leído por mensaje y responder dentro del hilo. Un hilo tiene `creado_por` y los mensajes llevan `autor_id`/`destinatario_id`. Alternativa descartada: una sola tabla `mensaje` con `parent_id` autorreferencial → complica el listado de bandeja y el aislamiento.

**4. Mensajería 100% independiente de `ComunicacionDocente`.**
FL-10 marca el inbox como paralelo a los emails a alumnos. No se reutiliza ni se acopla a `ComunicacionDocente` (que tiene cola Pend→Send→OK/Fail y destinatarios externos). El inbox es in-app, sin cola ni worker.

**5. Nuevos permisos RBAC fail-closed: `perfil:editar` e `inbox:usar`.**
El perfil NO usa `usuarios:gestionar` (eso es administración de terceros). Cada endpoint declara `require_permission(...)`. Identidad SIEMPRE desde el JWT verificado, nunca desde URL/body/header.

**6. Una sola migración Alembic** para las dos tablas nuevas (regla: una migración por cambio de schema; aquí el cambio de schema es el conjunto cohesivo de mensajería).

**7. Aislamiento de hilos: acceso a hilo ajeno → 404, no 403.**
Para no filtrar la existencia de hilos de otros usuarios, el acceso a un hilo donde no se participa devuelve 404 (recurso inexistente para ese usuario), no 403.

## Risks / Trade-offs

- **[Filtrado de PII en logs del perfil]** → reusar el patrón de cifrado/serialización de C-07; tests que verifican que `dni`/`cbu`/`alias_cbu` no aparecen en claro en logs.
- **[Cambio de email que rompe unicidad `(tenant_id, email)`]** → validar unicidad en el service antes de persistir; retornar 409. Cubierto por escenario de spec.
- **[Confusión inbox interno vs. comunicaciones a alumnos]** → namespaces y modelos separados (`/api/v1/inbox` vs `/api/v1/comunicaciones`), documentado en design y proposal.
- **[Fuga de hilos entre tenants/usuarios]** → repositories filtran por `tenant_id` por defecto y por participación; tests de aislamiento por usuario y por tenant (escenarios de spec).

## Migration Plan

1. Crear modelos `HiloMensaje` y `MensajeInterno` (SQLAlchemy 2.0 async), con `tenant_id`, FKs a `Usuario`, `leido`, timestamps y `deleted_at`.
2. Generar una migración Alembic única para ambas tablas.
3. Agregar permisos `perfil:editar` e `inbox:usar` al catálogo RBAC (seed/migración de permisos según patrón de C-04).
4. Implementar repositories (filtrados por tenant), services, schemas (`extra='forbid'`) y routers de perfil e inbox.
5. Sin rollback de datos destructivo: las tablas son nuevas; el rollback de la migración las elimina. El perfil no altera el schema de `Usuario`.

## Open Questions

- Ninguna bloqueante. El alcance de mensajería se acota deliberadamente a hilos de dos participantes (sin grupos ni adjuntos); si en el futuro se requiere multi-destinatario, será un change separado.
