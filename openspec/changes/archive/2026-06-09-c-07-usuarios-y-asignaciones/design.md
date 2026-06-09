## Context

El sistema ya tiene tres piezas de identidad/autorización implementadas:

- **`user`** (C-03 auth): tabla de identidad de login — `id` (UUID, PK), `tenant_id`, `email`, `password_hash`, `totp_*`, `is_active`. Unicidad `(tenant_id, email)`.
- **`user_rol`** (C-04 RBAC): vincula `user` ↔ `rol` con vigencia `desde`/`hasta`, pero **sin contexto académico**. Es el rol "global de tenant" del usuario. La resolución de permisos efectivos (`get_effective_permissions`) ya filtra por vigencia sobre esta tabla.
- **`rol` / `permiso` / `rol_permiso`** (C-04): catálogo administrable. El permiso `usuarios:gestionar` ya está en el seed (rol ADMIN); el patrón `equipos:asignar` proviene de la matriz canónica de la KB.

La KB (04_modelo_de_datos E4/E5) define `Usuario` como el perfil completo de la persona y `Asignacion` como el vínculo Usuario↔Rol↔**contexto académico** (materia/carrera/cohorte/comisiones) con vigencia y jerarquía (`responsable_id`). Hoy falta: (a) el perfil PII de la persona, (b) la asignación contextual.

Cifrado disponible: `AES256GCMCipher` en `backend/app/core/security.py` (formato `base64url(nonce[12] + ct+tag)`). Patrón de capas estricto: Routers → Services → Repositories → Models. Repos filtran por `tenant_id` por defecto. Soft delete vía `SoftDeleteMixin`. Pydantic `extra='forbid'`. ≤500 LOC/archivo. Strict TDD, DB real (no mocks).

**Governance: CRÍTICO** (PII + modificación de la resolución RBAC). Diseño aprobado antes de implementar.

## Goals / Non-Goals

**Goals:**

- Que cada persona del tenant tenga UN perfil con su PII de negocio, con DNI/CUIL/CBU/alias_cbu/email cifrados en reposo (AES-256-GCM) y nunca expuestos en claro en logs ni en respuestas sin permiso de gestión.
- Modelar `Asignacion` (rol contextual con vigencia y jerarquía) y su CRUD permisado y auditado.
- Que los permisos efectivos respeten la vigencia de las asignaciones (vencida = no autoriza), conservando el histórico (soft delete, append-only de facto).
- ABM de usuarios para ADMIN (`usuarios:gestionar`) y CRUD de asignaciones para COORDINADOR/ADMIN (`equipos:asignar`).

**Non-Goals:**

- Lógica de equipos docentes (asignación masiva, clonado entre períodos, export) — eso es C-08.
- Cálculo de CUIL a partir del DNI (PA-18, abierta) — `cuil` se carga manual.
- Semántica operativa del rol NEXO (PA-25, abierta) — el enum incluye NEXO pero no se codifican permisos especiales acá.
- Frontend de gestión de usuarios/asignaciones (C-24).

## Decisions

### D1 — Extender la tabla `user` con la PII (NO crear tabla `usuario` paralela)

La identidad de login (`user`) y el perfil de la persona (`Usuario` de la KB) son **la misma entidad de dominio**: una persona, un `id` (UUID), un `email` único por tenant. Crear una tabla `usuario` separada con relación 1:1 a `user` duplicaría la identidad, obligaría a joins en cada lookup y abriría la puerta a inconsistencias (dos `tenant_id`, dos `email`).

**Decisión**: agregar las columnas de negocio a `User` (`backend/app/models/user.py`): `nombre`, `apellidos`, `dni_enc`, `cuil_enc`, `cbu_enc`, `alias_cbu_enc`, `banco`, `regional`, `legajo`, `legajo_profesional`, `facturador` (bool), `estado` (enum reutiliza `EstadoEntidad` Activa/Inactiva). El `email` existente se trata como PII; se evalúa cifrarlo (ver D3). Sufijo `_enc` marca columnas cifradas para que ningún serializer las exponga por accidente.

- **Alternativa descartada**: tabla `usuario` 1:1 → más joins, riesgo de divergencia de identidad, contradice "identidad por UUID interno único".
- **Trade-off**: la tabla `user` crece y mezcla concern de auth con perfil. Se mitiga con sufijo `_enc`, schemas de respuesta que omiten PII por defecto, y mantener ≤500 LOC.

### D2 — `Asignacion` es contextual y coexiste con `user_rol` (rol global)

`user_rol` (C-04) = rol **global de tenant** (ej.: ADMIN, FINANZAS) sin contexto. `Asignacion` (C-07) = rol **dentro de un contexto académico** (PROFESOR de tal materia/cohorte). Son dos planos distintos y ambos deben acotar permisos por vigencia.

**Decisión**: nuevo modelo `Asignacion` en `backend/app/models/asignacion.py`, separado de `user_rol`. Campos: `usuario_id` (FK `user.id`), `rol` (enum `RolDominio`: PROFESOR/TUTOR/COORDINADOR/NEXO/ADMIN/FINANZAS), `materia_id`/`carrera_id`/`cohorte_id` (FK nullables, `ondelete=RESTRICT`), `comisiones` (JSONB lista de texto, default `[]`), `responsable_id` (FK `user.id`, nullable), `desde` (Date, NOT NULL), `hasta` (Date, nullable). `estado_vigencia` **NO se almacena**: se deriva en el service (`Vigente` si `desde <= hoy AND (hasta IS NULL OR hoy <= hasta)`).

- **Alternativa descartada**: reutilizar/extender `user_rol` con columnas de contexto → rompería la resolución RBAC ya probada de C-04 y mezclaría dos semánticas (global vs contextual).
- **Trade-off**: dos tablas de "rol del usuario". Se documenta claramente: `user_rol` = global, `asignacion` = contextual.

### D3 — Cifrado de PII: columnas `_enc`, cifrado/descifrado SOLO en el Service

DNI, CUIL, CBU, alias_cbu son `[cifrado]` en la KB. El `email` es PII pero también es **selector de login y clave de unicidad** `(tenant_id, email)` — cifrarlo con AES-GCM (nonce aleatorio) rompería la unicidad y el lookup por email.

**Decisión**:
- `dni`, `cuil`, `cbu`, `alias_cbu` → columnas `*_enc` (String), cifradas con `AES256GCMCipher`. El cifrado/descifrado ocurre **solo en el Service** (nunca en el Repository ni en el Model). La clave se obtiene de `core/config` (misma usada por 2FA).
- `email` → se mantiene en claro a nivel columna para preservar unicidad y login (decisión heredada de C-03; el email ya vivía así). Se trata como PII en logs y respuestas: no se loguea, y solo se devuelve a quien tiene `usuarios:gestionar`. Se registra como open question si producto exige cifrarlo (requeriría hash determinístico para unicidad).
- Ninguna columna `_enc` aparece en logs ni en los DTO de respuesta estándar. Solo el DTO de detalle administrativo (`usuarios:gestionar`) descifra y expone PII.

- **Alternativa descartada**: cifrar email con AES-GCM → rompe unicidad y login por email.
- **Trade-off**: email PII en claro en DB. Mitigación: control de acceso a nivel de respuesta + no loguear. Riesgo aceptado y heredado de C-03.

### D4 — Resolución RBAC acotada por vigencia de asignaciones contextuales

C-04 ya filtra `user_rol` por vigencia. C-07 agrega que las asignaciones **contextuales** también deben respetar vigencia: una `Asignacion` vencida no otorga el permiso del rol en ese contexto.

**Decisión**: el spec `rbac` se MODIFICA en su requirement de "Resolución server-side de permisos efectivos" para incluir explícitamente que las asignaciones contextuales vencidas no contribuyen. La implementación concreta del cómputo contextual fino (permiso `(propio)` por materia) se profundiza en los módulos que lo consumen (C-08+); acá se establece la regla base: vencida ⇒ no autoriza, y se conserva en histórico.

### D5 — Soft delete = histórico append-only para asignaciones

Una asignación vencida **se conserva** (KB §5: rotación de docentes entre cuatrimestres sin perder histórico). Eliminar una asignación = `deleted_at` (soft delete, `SoftDeleteMixin`). Vencer una asignación = setear `hasta` en el pasado (no se borra). Nunca hard delete.

### D6 — Migración 006 única (usuario + asignacion en un solo cambio de schema)

Una migración Alembic por cambio de schema. `006` agrega: columnas PII a `user`, tabla `asignacion`, enum `roldominio`. Las columnas nuevas en `user` son nullables o con default para no romper filas existentes (seed de C-03).

### D9 — Semántica y permisos del rol NEXO (PA-25 RESUELTA)

El NEXO es un **enlace institucional/administrativo** asignado a nivel Cohorte o Carrera. La KB menciona "tratamiento contable propio" — esto significa que el NEXO es un **sujeto de pago** (cobra por su función), NO que gestiona dinero. Son planos distintos y no deben mezclarse.

**Decisión — dos planos separados**:

| Plano | Change | Resolución |
|-------|--------|------------|
| RBAC / permisos (acá) | C-07 | `atrasados:ver`, `calificaciones:ver` sobre su población (cohorte/carrera). Sin permisos de escritura académica ni financiera. Sin `equipos:asignar`. |
| Sujeto de cálculo | C-18 | Tiene fórmula de pago propia (monto fijo por cohorte, porcentaje u otra). NO opera la grilla salarial. `liquidaciones:read_own` para ver su propio recibo — a definir en C-18. |

La gestión financiera (grilla salarial, cerrar liquidaciones, aprobar pagos) es **exclusivamente** del rol FINANZAS. Darle permisos de escritura sobre honorarios a un NEXO sería una violación de separación de intereses.

**Scope de "su población"**: los datos que el NEXO puede ver están acotados a su `Asignacion` contextual (`carrera_id`/`cohorte_id`). Los repositories de C-09/C-10/C-11 deberán respetar ese scope al filtrar.

**Acumulación de roles**: soportada por el RBAC existente — un usuario puede tener una `Asignacion` como NEXO de la Carrera X y otra como COORDINADOR de la Cohorte Y simultáneamente.

- **Permisos seed en C-07**: `atrasados:ver` y `calificaciones:ver` se asocian al rol NEXO en el catálogo. `liquidaciones:read_own` queda pendiente para C-18.

### D8 — Desactivación de usuario = cierre en cascada de asignaciones vigentes (PA-19 RESUELTA)

Al desactivar un usuario (`estado=Inactiva`), el sistema **cierra automáticamente** todas sus asignaciones vigentes estableciendo `hasta = fecha_baja`. Decisión de producto: mantiene la consistencia del histórico y evita comprobaciones repetitivas de `is_active` en las consultas de asignaciones.

**Decisión**: implementado en `usuario_service.py` como operación atómica dentro de la misma transacción que el cambio de estado. Para cada asignación con `hasta IS NULL OR hasta >= fecha_baja`:
1. Se setea `hasta = fecha_baja`.
2. Se registra auditoría `ASIGNACION_MODIFICAR` (C-05).
3. Se emite una alerta/evento al `responsable_id` de la asignación para advertir sobre la vacancia generada. Si `responsable_id` es null, se omite sin error.

El histórico se conserva (soft delete / append-only no aplica acá — las asignaciones no se borran, se cierran con `hasta`).

- **Alternativa descartada**: no-cascada (decisión provisional anterior) → obliga a cada módulo consumidor a filtrar también por `estado` del usuario, duplicando lógica.
- **Trade-off**: la desactivación de un usuario ahora tiene efectos secundarios sobre `asignacion`. Debe documentarse en la API y en auditoría.

### D7 — Endpoints y permisos

- `/api/v1/usuarios` → guard `usuarios:gestionar` (ADMIN). POST/GET/GET{id}/PATCH/DELETE. El detalle (`GET /{id}`) descifra PII; el listado NO expone PII.
- `/api/v1/asignaciones` → guard `equipos:asignar` (COORDINADOR, ADMIN). POST/GET (filtros usuario/materia/cohorte/rol/vigencia)/PATCH/DELETE. Mutaciones generan audit `ASIGNACION_MODIFICAR` (C-05).
- Identidad/tenant SIEMPRE desde `get_current_user` (JWT). `usuario_id`, `materia_id`, etc. del body se validan contra el tenant de la sesión.

## Risks / Trade-offs

- **[Mezclar auth y perfil en `user`]** → mitigado con sufijo `_enc`, schemas que omiten PII por defecto, límite 500 LOC; si crece, extraer un `UserProfileMixin`.
- **[Email PII en claro en DB]** → riesgo heredado de C-03; mitigación por control de acceso en respuestas + no loguear. Si producto exige cifrarlo, requiere hash determinístico para unicidad (cambio futuro).
- **[Dos tablas de rol del usuario: `user_rol` global vs `asignacion` contextual]** → riesgo de confusión. Mitigación: documentación explícita y nombres claros; la resolución RBAC consulta ambos planos.
- **[Desactivación en cascada de asignaciones]** → RESUELTA (D8). Desactivar usuario cierra en cascada con `hasta = fecha_baja` + auditoría + alerta a `responsable_id`. Riesgo: la desactivación tiene efectos secundarios observables. Mitigación: operación atómica en el service, auditoría de cada cierre, documentado en API.
- **[Fuga de PII por serialización accidental]** → mitigado: las columnas son `*_enc`, los DTO de respuesta estándar no las incluyen, y hay un test que verifica que un GET de listado NO trae DNI/CBU en claro.
- **[`comisiones` como JSONB lista de texto]** → es un placeholder hasta que C-06/C-08 formalice la entidad Comisión; aceptado por la KB (E5 `comisiones: lista<texto>`).

## Migration Plan

1. Migración Alembic `006`: enum `roldominio`; columnas PII en `user` (nullables/default); tabla `asignacion` (con índices `tenant_id`, `usuario_id`, FKs RESTRICT, soft delete).
2. Seed/verificación: confirmar que `usuarios:gestionar` y `equipos:asignar` existen en el catálogo de permisos (vienen de C-04); si `equipos:asignar` falta en el seed, agregarlo y asociarlo a COORDINADOR y ADMIN.
3. Rollback: `downgrade` revierte tabla `asignacion`, columnas PII y el enum. Sin pérdida de datos de `user` previos (columnas nuevas eran nullables).

## Open Questions

- ~~**PA-19**~~ **RESUELTA** (D8): cierre en cascada con `hasta = fecha_baja` + alerta a `responsable_id`.
- ~~**PA-25**~~ **RESUELTA** (D9): ver tabla de decisión abajo.
- ¿Producto exige cifrar `email` en reposo? Hoy en claro por unicidad/login (D3). Si sí → hash determinístico + columna cifrada separada.
- `comisiones` como `lista<texto>` (JSONB) vs entidad Comisión formal — diferido a C-08.
