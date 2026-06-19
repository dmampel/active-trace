# CHANGES — Secuencia de Implementación

> Índice canónico de todos los changes del proyecto **activia-trace**.
> Cada change es atómico: un agente puede implementarlo en una sesión (~4-6 horas).
> **Leer este archivo antes de ejecutar cualquier `/opsx:propose`.**

---

## Cómo usar este documento

1. **Identificá el change** que vas a implementar por su código `C-NN` (respetá el orden de dependencias).
2. **Leé la KB** indicada en la sección **"Leer antes"** de ese change — son tu contrato de dominio.
3. **Proponé el change**: `/opsx:propose C-NN-<nombre>` para generar proposal, design, specs y tasks.
4. **Implementá y archivá**: aplicá las tasks, verificá contra los specs, y `/opsx:archive` al cerrar.
5. **Marcá el checkbox** del change (`[ ]` → `[x]`) en este archivo cuando quede en producción.

---

## Árbol de dependencias

```
[x] **C-01**: `foundation-setup` (infra, Docker, FastAPI skel, DB inicial, OTel)
└── [x] C-02 core-models-y-tenancy (Tenant, mixins, repo base con scope tenant, Alembic)
    └── [x] C-03 auth-jwt-2fa (login, refresh rotation, recuperación, sesión)
        └── [x] C-04 rbac-permisos-finos (roles, permisos modulo:accion, matriz, guard)
            ├── [x] C-05 audit-log (E-AUD append-only, middleware, impersonación)
            ├── [x] C-06 estructura-academica (Carrera, Cohorte, Materia, ABM)
            │   ├── [x] C-07 usuarios-y-asignaciones (Usuario PII cifrada, Asignacion, vigencia)
            │   │   ├── [x] C-08 equipos-docentes (mis-equipos, masiva, clonar, exportar)
            │   │   ├── [x] C-09 padron-ingesta-moodle (VersionPadron, import xlsx/csv, Moodle WS)
            │   │   │   └── [x] C-10 calificaciones-y-umbral (Calificacion, UmbralMateria, import)
            │   │   │       └── [x] C-11 analisis-atrasados-reportes (atrasados, ranking, notas finales)
            │   │   │           └── [x] C-12 comunicaciones-cola-worker (Comunicacion, worker, preview, aprobación)
            │   │   ├── [x] C-13 encuentros-y-guardias (Slot, Instancia, Guardia, export aula)
            │   │   ├── [x] C-14 evaluaciones-y-coloquios (Evaluacion, Reserva, Resultado, FechaAcademica)
            │   │   ├── [x] C-15 avisos-y-acknowledgment (Aviso, ack, scope, vigencia)
            │   │   ├── [x] C-16 tareas-internas (Tarea, ComentarioTarea, workflow)
            │   │   ├── [x] C-17 programas-y-fechas-academicas (ProgramaMateria, FechaAcademica)
            │   │   └── [x] C-18 liquidaciones-y-honorarios (SalarioBase/Plus, Liquidacion, Factura)
            │   ├── [x] C-19 panel-auditoria-metricas (dashboards de uso, F9.1)
            │   ├── [x] C-20 perfil-y-mensajeria-interna (perfil propio, inbox interno)
            │   └── C-21 frontend-shell-y-auth (SPA shell, login, guard, cliente HTTP)
            │       ├── C-22 frontend-academico-docente (importación, atrasados, comunicaciones)
            │       ├── C-23 frontend-coordinacion (equipos, avisos, tareas, monitores)
            │       └── C-24 frontend-finanzas-y-admin (liquidaciones, facturas, estructura, auditoría)
```

### Paralelismo por fase

```
GATE 0: (inicio) — sin dependencias
  → C-01 foundation-setup                         [Agente A]

GATE 1: C-01 ✓                                     ← cimiento listo
  → C-02 core-models-y-tenancy                     [Agente A]

GATE 2: C-02 ✓
  → C-03 auth-jwt-2fa                              [Agente A]

GATE 3: C-03 ✓
  → C-04 rbac-permisos-finos                       [Agente A]

GATE 4: C-04 ✓                                     ← PRIMER FORK (seguridad lista)
  → C-05 audit-log                                 [Agente B]
  → C-06 estructura-academica                      [Agente A]
  → C-21 frontend-shell-y-auth                     [Agente C]

GATE 5: C-06 ✓                                     ← FORK ANCHO (entidades raíz listas)
  → C-07 usuarios-y-asignaciones                   [Agente A]
  → C-15 avisos-y-acknowledgment                   [Agente B — si C-05 ✓]
  → C-17 programas-y-fechas-academicas             [Agente B]

GATE 6: C-07 ✓                                     ← FORK ANCHO (usuarios + asignaciones listos)
  → C-08 equipos-docentes                          [Agente A]
  → C-09 padron-ingesta-moodle                     [Agente B]
  → C-13 encuentros-y-guardias                     [Agente A]
  → C-14 evaluaciones-y-coloquios                  [Agente B]
  → C-16 tareas-internas                           [Agente C]
  → C-18 liquidaciones-y-honorarios                [Agente C]
  → C-19 panel-auditoria-metricas                  [Agente C — si C-05 ✓]
  → C-20 perfil-y-mensajeria-interna               [Agente C]

GATE 7: C-09 ✓
  → C-10 calificaciones-y-umbral                   [Agente B]

GATE 8: C-10 ✓
  → C-11 analisis-atrasados-reportes               [Agente B]

GATE 9: C-11 ✓                                     ← flujo central del PROFESOR completo
  → C-12 comunicaciones-cola-worker                [Agente B]

GATE 10: C-21 ✓ + backend de cada dominio ✓       ← capa de presentación
  → C-22 frontend-academico-docente                [Agente C — si C-12 ✓]
  → C-23 frontend-coordinacion                     [Agente C — si C-08, C-15, C-16 ✓]
  → C-24 frontend-finanzas-y-admin                 [Agente C — si C-18, C-19 ✓]
```

### Camino crítico (10 changes — mínimo irreducible)

La cadena lineal más corta para tener el flujo de mayor valor (importar → analizar → comunicar) operando en producción multi-tenant:

```
C-01 → C-02 → C-03 → C-04 → C-06 → C-07 → C-09 → C-10 → C-11 → C-12*
```

`C-12*` (comunicaciones-cola-worker) es el último change indispensable del flujo central. El frontend mínimo (`C-21` + `C-22*`) corre en paralelo sobre la rama del Agente C y converge en GATE 10.

### Plan óptimo con 3 agentes

| Paso | Agente A (Backend Core) | Agente B (Backend Aux) | Agente C (Frontend / Soporte) |
|------|--------------------------|-------------------------|--------------------------------|
| 1 | C-01 foundation-setup | — | — |
| 2 | C-02 core-models-y-tenancy | — | — |
| 3 | C-03 auth-jwt-2fa | — | — |
| 4 | C-04 rbac-permisos-finos | — | — |
| 5 | C-06 estructura-academica | C-05 audit-log | C-21 frontend-shell-y-auth |
| 6 | C-07 usuarios-y-asignaciones | C-17 programas-y-fechas | C-15 avisos-y-acknowledgment |
| 7 | C-08 equipos-docentes | C-09 padron-ingesta-moodle | C-20 perfil-y-mensajeria |
| 8 | C-13 encuentros-y-guardias | C-10 calificaciones-y-umbral | C-16 tareas-internas |
| 9 | C-14 evaluaciones-y-coloquios | C-11 analisis-atrasados-reportes | C-18 liquidaciones-y-honorarios |
| 10 | C-19 panel-auditoria-metricas | C-12 comunicaciones-cola-worker | C-22 frontend-academico-docente |
| 11 | — | C-23 frontend-coordinacion | C-24 frontend-finanzas-y-admin |

> Los 3 agentes convergen alrededor del paso 10-11. El Agente A queda libre antes y puede tomar `C-19` o adelantar refactors.

---

## FASE 0 — Cimiento e Infraestructura

### [x] [C-01] `foundation-setup`
- **Estado**: `[x]` completado
- **Scope**:
  - Estructura de directorios Clean Architecture: `routers/`, `services/`, `repositories/`, `models/`, `schemas/`, `core/`, `integrations/`, `workers/`. Límite ≤500 LOC/archivo.
  - Esqueleto FastAPI con `app/main.py`, health-check `GET /health`, configuración Pydantic v2 Settings desde `.env`.
  - `docker-compose.yml` (api, postgres, worker) + `Dockerfile` multi-stage. Convención Easypanel.
  - Conexión SQLAlchemy 2.0 **async** + sesión por request (dependency injection).
  - OpenTelemetry + logging estructurado JSON base.
  - `pyproject.toml` con deps (FastAPI, SQLAlchemy, Alembic, asyncpg, Pydantic v2, argon2-cffi, python-jose, pytest, httpx).
  - Tests: smoke de `/health`, arranque de la app, conexión a DB de test.
- **Dependencias**: ninguna
- **Governance**: BAJO
- **Leer antes**:
  - `knowledge-base/08_arquitectura_propuesta.md` §2 (patrón por capas), §6 (persistencia)
  - `docs/ARQUITECTURA.md` (stack, estructura de directorios, variables de entorno)

---

## FASE 1 — Seguridad y Modelos Core (cimiento crítico)

> Cadena estrictamente secuencial. Es el corazón multi-tenant del sistema: nada se construye sin esto.

### [x] [C-02] `core-models-y-tenancy`
- **Estado**: `[x]` completado
- **Scope**:
  - Modelo `Tenant` raíz. Mixin base con `id` (UUID), `tenant_id`, `created_at`, `updated_at`, `deleted_at` (soft delete).
  - **Repository genérico** con scope de tenant SIEMPRE activo: todo query filtra por `tenant_id` por defecto (ADR-002 row-level). Un query sin scope debe fallar en review.
  - Utilidad de cifrado AES-256 para atributos `[cifrado]` (DNI, CUIL, CBU, email PII): helper de cifrado/descifrado en reposo, nunca en logs.
  - Setup Alembic (`Migración 001: tenant`) + convención de migración por cambio de schema.
  - Soft delete transversal (nunca borrado físico).
  - Tests: aislamiento multi-tenant (un tenant no ve datos de otro), soft delete, cifrado round-trip, mixin timestamps.
- **Dependencias**: `C-01`
- **Governance**: CRITICO
- **Leer antes**:
  - `knowledge-base/04_modelo_de_datos.md` §Supuestos base, §Convenciones
  - `knowledge-base/08_arquitectura_propuesta.md` §4 (multi-tenancy), §6 (persistencia, soft delete)
  - `docs/ARQUITECTURA.md` §6, §8 (tenant isolation, AES-256, ADR-002)

### [x] [C-03] `auth-jwt-2fa`
- **Estado**: `[x]` completado
- **Scope**:
  - `POST /api/auth/login` — email + password (Argon2id), JWT access 15min + refresh token con **rotación** (refresh usado se invalida). Claims mínimos: `user_id`, `tenant_id`, `roles`, `exp`.
  - `POST /api/auth/refresh` — rota refresh, emite nuevo par. `POST /api/auth/logout` — revoca sesión.
  - **2FA TOTP opcional** por usuario: enrolar, verificar, gate entre validación de credenciales y emisión de sesión.
  - Recuperación: `POST /api/auth/forgot` (token de un solo uso por email, expiración corta) + `POST /api/auth/reset`.
  - Rate limiting 5/60s por IP+email en login. Regla de oro: identidad/tenant SOLO del JWT verificado.
  - Dependency `get_current_user` que resuelve identidad + tenant desde el token verificado.
  - Tests: login OK/KO, refresh rotation (reuso invalida), 2FA flow, recuperación token único, rate limit, identidad inmutable por parámetro.
- **Dependencias**: `C-02`
- **Governance**: CRITICO
- **Leer antes**:
  - `knowledge-base/07_flujos_principales.md` FL-01 (autenticación), §regla de oro
  - `knowledge-base/03_actores_y_roles.md` §1, §6 (acceso anónimo)
  - `knowledge-base/08_arquitectura_propuesta.md` §3.1, §3.3 (auth, identidad)
  - `docs/ARQUITECTURA.md` §5.1 (ADR-001 auth propio)

### [x] [C-04] `rbac-permisos-finos`
- **Estado**: `[x]` completado
- **Scope**:
  - Catálogo administrable: tablas `Rol`, `Permiso` (`modulo:accion`), matriz `RolPermiso` (datos, NO hardcode).
  - Roles del dominio seed: ALUMNO, TUTOR, PROFESOR, COORDINADOR, NEXO, ADMIN, FINANZAS.
  - Resolución de permisos efectivos server-side por request (unión de roles, acotada por tenant y vigencia de asignación).
  - Dependency/guard `require_permission("modulo:accion")` que declara el permiso por endpoint; sin él → 403.
  - `Migración 002: rol, permiso, rol_permiso` + seed de la matriz base de `03_actores_y_roles.md` §3.3.
  - Tests: usuario sin permiso → 403, unión de roles, permiso `(propio)` vs global, catálogo administrable.
- **Dependencias**: `C-03`
- **Governance**: CRITICO
- **Leer antes**:
  - `knowledge-base/03_actores_y_roles.md` §2 (roles), §3 (RBAC, matriz §3.3), §5 (vigencia)
  - `knowledge-base/08_arquitectura_propuesta.md` §3.2 (RBAC permisos finos)

### [x] [C-05] `audit-log`
- **Estado**: `[x]` completo — 2026-06-07
- **Scope**:
  - Modelo `AuditLog` (E-AUD) **append-only**: sin update ni delete a nivel app y DB. Campos: actor, impersonado, materia, accion, detalle JSON, filas_afectadas, ip, user_agent, fecha_hora.
  - Helper/decorator de auditoría para registrar acciones significativas con código estandarizado (`CALIFICACIONES_IMPORTAR`, `PADRON_CARGAR`, etc.).
  - **Impersonación**: permiso `impersonacion:usar`, sesión distinguible, acciones atribuidas al actor real; registra `IMPERSONACION_INICIAR` / `IMPERSONACION_FINALIZAR`.
  - `Migración 003: audit_log`.
  - Tests: append-only (update/delete rechazados), atribución bajo impersonación, registro de acción con código + filas afectadas.
- **Dependencias**: `C-04`
- **Governance**: CRITICO
- **Leer antes**:
  - `knowledge-base/04_modelo_de_datos.md` §E-AUD, §Códigos de acción
  - `knowledge-base/03_actores_y_roles.md` §4 (impersonación)
  - `knowledge-base/08_arquitectura_propuesta.md` §3.4 (audit append-only), §3.5 (impersonación)

---

## FASE 2 — Entidades Raíz del Dominio Académico

### [x][C-06] `estructura-academica` ✅
- **Estado**: `[x]` completo — archivado 2026-06-07
- **Scope**:
  - Modelos: `Carrera`, `Cohorte`, `Materia`, `InstanciaDictado` (dos niveles de materia — PA-01 cerrada).
  - ABM `/api/v1/estructura/carreras|cohortes|materias|instancias` con permisos granulares `estructura:leer|crear|editar|eliminar`.
  - Reglas: unicidad `(tenant_id, codigo)` en Carrera/Materia; `(tenant_id, carrera_id, nombre)` en Cohorte; `(tenant_id, materia_id, cohorte_id, periodo)` en InstanciaDictado; cohorte pertenece a una sola carrera (PA-07 cerrada).
  - `Migración 005: carrera, cohorte, materia, instancia_dictado` + permisos granulares en rol_permiso.
  - Tests: 21 tests (modelos, repos, endpoints), 117 tests totales GREEN.
- **Dependencias**: `C-04`, `C-05`
- **Governance**: MEDIO
- **Leer antes**:
  - `knowledge-base/04_modelo_de_datos.md` §E1–E3b (Carrera, Cohorte, Materia, InstanciaDictado)
  - `knowledge-base/06_funcionalidades.md` Épica 5 (F5.1, F5.2)
  - `docs/ARQUITECTURA.md` §10 (ADR-006 Materia + Dictado)

---

## FASE 3 — Identidad, Asignaciones y Estructura Documental

### [x] [C-07] `usuarios-y-asignaciones`
- **Estado**: `[x]` completado
- **Scope**:
  - Modelo `Usuario` con PII **cifrada** (`email`, `dni`, `cuil`, `cbu`, `alias_cbu`); legajo como atributo de negocio opcional (no PK, no credencial).
  - Modelo `Asignacion` (Usuario ↔ Rol ↔ contexto: materia/carrera/cohorte/comisiones), `responsable_id` (jerarquía), vigencia `desde/hasta`, `estado_vigencia` derivado.
  - ABM usuarios `/api/admin/usuarios` (guard gestión de usuarios, ADMIN); CRUD asignaciones `/api/asignaciones` (`equipos:asignar`).
  - Unicidad `(tenant_id, email)`. Asignación vencida no otorga permisos pero se conserva (histórico).
  - `Migración 005: usuario, asignacion`.
  - Tests: PII cifrada no expuesta en logs/respuestas, unicidad email por tenant, vigencia (vencida no autoriza), multi-rol, jerarquía responsable.
- **Dependencias**: `C-06`
- **Governance**: CRITICO
- **Leer antes**:
  - `knowledge-base/04_modelo_de_datos.md` §E4 Usuario, §E5 Asignación
  - `knowledge-base/03_actores_y_roles.md` §5 (vigencia temporal)
  - `knowledge-base/06_funcionalidades.md` F4.1, F4.3
  - `docs/ARQUITECTURA.md` §5, §6 (PII cifrada AES-256)

### [x] [C-17] `programas-y-fechas-academicas`
- **Estado**: `[x]` completo
- **Scope**:
  - Modelos: `ProgramaMateria` (documento por materia × carrera × cohorte, `referencia_archivo` al almacenamiento), `FechaAcademica` (parciales/TP/coloquios por materia × cohorte × número).
  - `/api/programas` (upload + asociar, `estructura:gestionar`) y `/api/fechas-academicas` (CRUD, listado tabular + calendario).
  - Salida: generación de fragmento de contenido listo para el aula virtual del LMS (F5.4).
  - `Migración 0NN: programa_materia, fecha_academica`.
  - Tests: CRUD, asociación materia×carrera×cohorte, referencia de archivo opaca, aislamiento tenant.
- **Dependencias**: `C-06`
- **Governance**: BAJO
- **Leer antes**:
  - `knowledge-base/04_modelo_de_datos.md` §E15 FechaAcademica, §E16 ProgramaMateria
  - `knowledge-base/06_funcionalidades.md` F5.3, F5.4

---

## FASE 4 — Módulos de Dominio (gran fork paralelo)

> Todos dependen de `C-07` (usuarios + asignaciones). Se pueden repartir entre los 3 agentes en paralelo.

### [x] [C-08] `equipos-docentes`
- **Estado**: `[x]` completo
- **Scope**:
  - Vistas/endpoints sobre `Asignacion`: mis-equipos del docente (F4.2), gestión de asignaciones (F4.3).
  - Asignación masiva (F4.4): bloque docentes × materia × carrera × cohorte × rol con vigencia.
  - Clonar equipo entre períodos (F4.5, RN-12): duplica asignaciones vigentes con fechas del nuevo período.
  - Modificar vigencia general del equipo (F4.6); exportar equipo a archivo (F4.7).
  - `/api/equipos/*` con guard `equipos:asignar` (COORDINADOR, ADMIN). Genera audit (`ASIGNACION_MODIFICAR`).
  - Tests: clonado entre cohortes, asignación masiva, modificación de vigencia en bloque, export.
- **Dependencias**: `C-07`
- **Governance**: ALTO
- **Leer antes**:
  - `knowledge-base/06_funcionalidades.md` Épica 4 (F4.2–F4.7)
  - `knowledge-base/07_flujos_principales.md` FL-03 (setup cuatrimestre)
  - `knowledge-base/04_modelo_de_datos.md` §E5 Asignación

### [x] [C-09] `padron-ingesta-moodle`
- **Estado**: `[x]` completado
- **Scope**:
  - Modelos `VersionPadron` + `EntradaPadron` (versionado: una versión activa por materia×cohorte; activar nueva desactiva la anterior).
  - Import de padrón: archivo `.xlsx`/`.csv` (fallback manual) con vista previa (F1.3, F1.4).
  - Integración **Moodle Web Services** (`integrations/moodle_ws.py`): sync de usuarios/actividades, sync nocturna + on-demand; errores mapean a `502` con reintento.
  - Vaciar datos de materia (F1.5, RN-04). Audit `PADRON_CARGAR`.
  - `Migración 0NN: version_padron, entrada_padron`.
  - Tests: versionado (activar desactiva anterior), import xlsx/csv, entrada sin usuario_id (alumno sin cuenta), aislamiento tenant, mock Moodle WS + fallback 502.
- **Dependencias**: `C-07`
- **Governance**: MEDIO
- **Leer antes**:
  - `knowledge-base/04_modelo_de_datos.md` §E6 Padrón (versionado)
  - `knowledge-base/06_funcionalidades.md` F1.3, F1.4, F1.5
  - `knowledge-base/08_arquitectura_propuesta.md` §5.1 (Moodle WS, fallback manual)

### [x] [C-10] `calificaciones-y-umbral`
- **Estado**: `[x]` completado — archivado 2026-06-17
- **Scope**:
  - Modelos `Calificacion` (numérica/textual, `aprobado` derivado, origen Importado/Manual) y `UmbralMateria` (umbral_pct por asignación, valores aprobatorios).
  - Importar calificaciones desde archivo del LMS (F1.1): detecta columnas de actividades numéricas (RN-01) y textuales (RN-02), vista previa, selección de actividades.
  - Importar reporte de finalización (F1.2): detecta TPs entregados sin nota.
  - Configurar umbral por materia (F2.1, RN-03, defecto 60%). Audit `CALIFICACIONES_IMPORTAR`.
  - `Migración 0NN: calificacion, umbral_materia`.
  - Tests: derivación `aprobado` (numérica vs umbral, textual vs conjunto), import + preview, selección de actividades, umbral por asignación (no afecta otros docentes).
- **Dependencias**: `C-09`
- **Governance**: MEDIO
- **Leer antes**:
  - `knowledge-base/04_modelo_de_datos.md` §E7 Calificación, §E8 Umbral
  - `knowledge-base/06_funcionalidades.md` F1.1, F1.2, F2.1
  - `knowledge-base/07_flujos_principales.md` FL-02 (pasos 3–5)

### [x] [C-11] `analisis-atrasados-reportes`
- **Estado**: `[x]` completado
- **Scope**:
  - Cómputo de **alumnos atrasados** (actividades faltantes o nota < umbral, RN-06) (F2.2).
  - Ranking de actividades aprobadas (F2.3, RN-09); reportes rápidos por materia (F2.4); notas finales agrupadas (F2.5).
  - Exportar TPs sin corregir (F2.6, RN-07/08). Monitores: general (F2.7), seguimiento tutor/profesor (F2.8), coordinación/admin con rango de fechas (F2.9).
  - `/api/analisis/*` con guards `atrasados:ver`. Lógica de cálculo en Services (sin SQL en Services).
  - Tests: definición de atrasado contra umbral, ranking (solo ≥1 aprobada), notas finales agrupadas, filtros del monitor, export.
- **Dependencias**: `C-10`
- **Governance**: MEDIO
- **Leer antes**:
  - `knowledge-base/06_funcionalidades.md` Épica 2 (F2.2–F2.9)
  - `knowledge-base/07_flujos_principales.md` FL-02 (pasos 5–6)
  - `knowledge-base/04_modelo_de_datos.md` §E7, §E8

### [x] [C-12] `comunicaciones-cola-worker`
- **Estado**: `[x]` completado
- **Scope**:
  - Modelo `Comunicacion` (destinatario `[cifrado]`, lote_id, estado: Pendiente → Enviando → Enviado/Error/Cancelado, RN-15).
  - **Worker asíncrono** de despacho (`workers/`): consume cola, transiciona estados. Plantillas con variables de sustitución.
  - Preview obligatorio antes de encolar (F3.1, RN-16). Envío masivo con cola (F3.2). Aprobación humana configurable por tenant (F3.3, RN-17): guard `comunicacion:aprobar`, lote o individual.
  - `/api/comunicaciones/*` (`comunicacion:enviar`). Audit `COMUNICACION_ENVIAR`.
  - `Migración 0NN: comunicacion`.
  - Tests: máquina de estados (transiciones válidas/ inválidas), preview, aprobación lote/individual, cancelación, destinatario cifrado, worker procesa Pendiente→Enviado.
- **Dependencias**: `C-11`
- **Governance**: ALTO
- **Leer antes**:
  - `knowledge-base/04_modelo_de_datos.md` §E21 Comunicación
  - `knowledge-base/06_funcionalidades.md` Épica 3 (F3.1–F3.3)
  - `knowledge-base/07_flujos_principales.md` FL-02 (7–8), FL-04 (aprobación)
  - `knowledge-base/08_arquitectura_propuesta.md` §5.2 (worker de cola)

### [x] [C-13] `encuentros-y-guardias`
- **Estado**: `[x]` completado
- **Scope**:
  - Modelos `SlotEncuentro`, `InstanciaEncuentro`, `Guardia`.
  - Crear encuentro recurrente (F6.1, RN-13): genera todas las instancias del slot. Encuentro único (F6.2). Editar instancia (F6.3: estado, meet_url, video_url, comentario).
  - Generar bloque HTML para el aula virtual (F6.4); vista admin de encuentros (F6.5).
  - Registro de guardias (F6.6): tutor registra, coordinación consulta global + export.
  - `/api/encuentros/*`, `/api/guardias/*` con guards `encuentros:gestionar`.
  - `Migración 0NN: slot_encuentro, instancia_encuentro, guardia`.
  - Tests: generación de instancias recurrentes (cant_semanas), encuentro único, edición de estado, registro de guardia, export.
- **Dependencias**: `C-07`
- **Governance**: MEDIO
- **Leer antes**:
  - `knowledge-base/04_modelo_de_datos.md` §E9, §E10, §E11
  - `knowledge-base/06_funcionalidades.md` Épica 6 (F6.1–F6.6)
  - `knowledge-base/07_flujos_principales.md` FL-06 (encuentros recurrentes)

### [x] [C-14] `evaluaciones-y-coloquios`
- **Estado**: `[x]` completado — archivado 2026-06-18
- **Scope**:
  - Modelos `Evaluacion`, `ReservaEvaluacion`, `ResultadoEvaluacion`.
  - Crear convocatoria de coloquio (F7.3): materia, instancia, días y cupos. Importar alumnos a convocatoria (F7.2). Listado de convocatorias (F7.4). Panel de métricas (F7.1). Admin global (F7.5).
  - Reserva de turno por ALUMNO (F7, FL-07): día disponible con cupo; estado Activa/Cancelada.
  - `/api/coloquios/*` (COORDINADOR/ADMIN gestión; ALUMNO reserva).
  - `Migración 0NN: evaluacion, reserva_evaluacion, resultado_evaluacion`.
  - Tests: creación de turnos con cupo, reserva resta cupo, sin cupo rechaza, métricas (convocados/reservas/libres), resultado consolidado.
- **Dependencias**: `C-07`
- **Governance**: MEDIO
- **Leer antes**:
  - `knowledge-base/04_modelo_de_datos.md` §E14 Evaluación (Reserva, Resultado)
  - `knowledge-base/06_funcionalidades.md` Épica 7 (F7.1–F7.5)
  - `knowledge-base/07_flujos_principales.md` FL-07 (coloquio)

### [x] [C-15] `avisos-y-acknowledgment`
- **Estado**: `[x]` completado — archivado 2026-06-18
- **Scope**:
  - Modelos `Aviso` (alcance Global/PorMateria/PorCohorte/PorRol, severidad, vigencia inicio/fin, orden, requiere_ack) y `AcknowledgmentAviso`.
  - ABM avisos (F3.5): `avisos:publicar` (COORDINADOR/ADMIN). Visualización por destinatario según rol/alcance/cohorte (RN-18/19/20).
  - Confirmación de lectura por ALUMNO/cualquier rol; contadores derivados de `AcknowledgmentAviso` (no denormalizados).
  - `/api/avisos/*`. `Migración 0NN: aviso, acknowledgment_aviso`.
  - Tests: filtrado por scope (rol/cohorte/materia), ventana de vigencia (fuera de rango no se muestra), ack (deja de mostrarse + cuenta), orden de prioridad.
- **Dependencias**: `C-06`
- **Governance**: MEDIO
- **Leer antes**:
  - `knowledge-base/04_modelo_de_datos.md` §E13 Aviso, Acknowledgment
  - `knowledge-base/06_funcionalidades.md` F3.5
  - `knowledge-base/07_flujos_principales.md` FL-09 (publicación de aviso)

### [x] [C-16] `tareas-internas`
- **Estado**: `[x]` completo
- **Scope**:
  - Modelos `Tarea` (asignado_a, asignado_por, estado Pendiente/En progreso/Resuelta/Cancelada, contexto_id) y `ComentarioTarea`.
  - Mis tareas (F8.1); asignar/delegar tarea a otro docente (F8.2); administración global con filtros (F8.3); cambio de estado + comentarios (workflow asincrónico).
  - `/api/tareas/*` con guard `tareas:gestionar`. Módulo de alto uso (cientos simultáneas).
  - `Migración 0NN: tarea, comentario_tarea`.
  - Tests: alta + asignación, delegación con trazabilidad asignador/asignado, transiciones de estado, comentarios en hilo, filtros.
- **Dependencias**: `C-07`
- **Governance**: MEDIO
- **Leer antes**:
  - `knowledge-base/04_modelo_de_datos.md` §E12 Tarea, ComentarioTarea
  - `knowledge-base/06_funcionalidades.md` Épica 8 (F8.1–F8.3)
  - `knowledge-base/07_flujos_principales.md` FL-05 (workflow de tareas)

### [x] [C-18] `liquidaciones-y-honorarios`
- **Estado**: `[x]` completo — archivado 2026-06-19
- **Scope**:
  - Modelos `SalarioBase` (por rol, vigencia), `SalarioPlus` (grupo × rol, vigencia), `Liquidacion` (base + plus = total, es_nexo, excluido_por_factura, estado Abierta/Cerrada), `Factura`.
  - Cálculo de liquidación del período (FL-08, RN-21): base por rol vigente + plus por grupos. Vista (F10.1), cerrar (F10.2, inmutable RN-22), historial (F10.3).
  - Grilla salarial ABM (F10.4, RN-31/32/33). Facturas de docentes que facturan (F10.5, RN-35): excluidos de liquidación general. Separación contable factura vs no-factura + KPIs (F10.6, RN-36/37/38).
  - `/api/liquidaciones/*`, `/api/facturas/*` con guards `liquidaciones:*` (FINANZAS). Audit `LIQUIDACION_CERRAR`.
  - `Migración 0NN: salario_base, salario_plus, liquidacion, factura`.
  - Tests: selección de base vigente por período, suma de plus, total, cierre inmutable, exclusión por factura, segmentación NEXO/factura/general.
- **Dependencias**: `C-07`
- **Governance**: CRITICO
- **Leer antes**:
  - `knowledge-base/04_modelo_de_datos.md` §E17–E20 (Salario, Liquidación, Factura)
  - `knowledge-base/06_funcionalidades.md` Épica 10 (F10.1–F10.6)
  - `knowledge-base/07_flujos_principales.md` FL-08 (liquidación)
  - `knowledge-base/10_preguntas_abiertas.md` PA-22, PA-23 (mapeo y acumulación de Plus — confirmar antes)

### [x] [C-19] `panel-auditoria-metricas`
- **Estado**: `[x]` completo — archivado 2026-06-19
- **Scope**:
  - Panel de interacciones (F9.1): acciones por día, estado de comunicaciones por docente, interacciones por docente×materia, log de últimas acciones (máx configurable, defecto 200).
  - Log completo de auditoría (F9.2, RN-23/24) con filtros: rango de fechas, materia, usuario, estado.
  - `/api/auditoria/*` con guard `auditoria:ver` (ADMIN, COORDINADOR `(propio)`, FINANZAS). Solo lectura sobre `AuditLog`.
  - Tests: agregaciones por día/docente/materia, límite configurable, filtros, scope `(propio)` del coordinador.
- **Dependencias**: `C-07`, `C-05`
- **Governance**: ALTO
- **Leer antes**:
  - `knowledge-base/06_funcionalidades.md` Épica 9 (F9.1, F9.2)
  - `knowledge-base/07_flujos_principales.md` FL-11 (auditoría por docente)
  - `knowledge-base/04_modelo_de_datos.md` §E-AUD

### [C-20] `perfil-y-mensajeria-interna`
- **Estado**: `[x]` completo
- **Scope**:
  - Editar perfil propio (F11.1): nombre, datos fiscales/bancarios, regional, modalidad de cobro; CUIL solo lectura.
  - Bandeja de mensajes interna (F3.4, F11.2, FL-10): hilos recibidos, responder dentro del hilo. Mensajería entre usuarios registrados (paralela a comunicaciones a alumnos).
  - Cierre de sesión explícito (F11.3) — reusa `C-03` logout.
  - `/api/perfil`, `/api/inbox/*`.
  - Tests: edición de campos editables, CUIL no modificable, hilo de mensajes (leer/responder), aislamiento por usuario/tenant.
- **Dependencias**: `C-07`
- **Governance**: BAJO
- **Leer antes**:
  - `knowledge-base/06_funcionalidades.md` Épica 11 (F11.1–F11.3), F3.4
  - `knowledge-base/07_flujos_principales.md` FL-10 (mensajería interna)
  - `knowledge-base/04_modelo_de_datos.md` §E4 Usuario

---

## FASE 5 — Frontend (SPA por features)

> `C-21` es el shell común. Las features (C-22/23/24) consumen los endpoints ya construidos en backend.

### [C-21] `frontend-shell-y-auth`
- **Estado**: `[ ]` pendiente
- **Scope**:
  - Scaffolding React 18 + TypeScript + Vite. Estructura feature-based. Tailwind, TanStack Query, React Hook Form + Zod, Axios.
  - Cliente HTTP centralizado: interceptor de auth + **refresh transparente** de tokens. Manejo de 401/403.
  - Pantallas de login, 2FA, recuperación de contraseña (consumen `C-03`). Guard de rutas por permiso. Layout/menú adaptado a permisos de la sesión.
  - Logout. Tests: render de login, flujo de auth (mock), guard redirige sin sesión, refresh transparente.
- **Dependencias**: `C-04`
- **Governance**: BAJO
- **Leer antes**:
  - `knowledge-base/08_arquitectura_propuesta.md` §2 (frontend SPA por features)
  - `knowledge-base/07_flujos_principales.md` FL-01 (auth)
  - `docs/ARQUITECTURA.md` (stack frontend, convenciones)

### [C-22] `frontend-academico-docente`
- **Estado**: `[ ]` pendiente
- **Scope**:
  - Feature de gestión de comisión (PROFESOR): importación de calificaciones con preview y selección de actividades, configuración de umbral, vista de atrasados, ranking, notas finales, reportes rápidos.
  - Detección de entregas sin corregir + export. Comunicación a atrasados: preview + envío + tracking de estado en tiempo real.
  - Monitores de seguimiento (tutor/profesor). Consume `C-10`, `C-11`, `C-12`.
  - Tests (componentes/integración con mocks): import flow, tabla de atrasados, preview de comunicación, tracking de estados.
- **Dependencias**: `C-21`, `C-12`
- **Governance**: BAJO
- **Leer antes**:
  - `knowledge-base/06_funcionalidades.md` Épicas 1, 2, 3
  - `knowledge-base/07_flujos_principales.md` FL-02, FL-04

### [C-23] `frontend-coordinacion`
- **Estado**: `[ ]` pendiente
- **Scope**:
  - Features de COORDINADOR/ADMIN: gestión de equipos docentes (mis-equipos, masiva, clonar, vigencia, export), avisos (ABM + scope + ack), tareas internas (workflow), monitores transversales (general F2.7, F2.9), encuentros admin, coloquios.
  - Setup de cuatrimestre (FL-03). Consume `C-08`, `C-13`, `C-14`, `C-15`, `C-16`, `C-17`.
  - Tests: ABM equipos, clonado, publicación de aviso, workflow de tarea, filtros de monitor.
- **Dependencias**: `C-21`, `C-08`, `C-15`, `C-16`
- **Governance**: BAJO
- **Leer antes**:
  - `knowledge-base/06_funcionalidades.md` Épicas 4, 5, 6, 7, 8
  - `knowledge-base/07_flujos_principales.md` FL-03, FL-05, FL-06, FL-09

### [C-24] `frontend-finanzas-y-admin`
- **Estado**: `[ ]` pendiente
- **Scope**:
  - Feature FINANZAS: vista de liquidaciones del período con segmentación (general / NEXO / factura) + KPIs, cerrar liquidación, historial, grilla salarial, gestión de facturas.
  - Feature ADMIN: estructura académica (carreras, cohortes, materias), usuarios del tenant, panel de auditoría y métricas, log completo. Consume `C-06`, `C-07`, `C-18`, `C-19`.
  - Tests: vista de liquidación segmentada, cierre, ABM grilla salarial, panel de auditoría con filtros.
- **Dependencias**: `C-21`, `C-18`, `C-19`
- **Governance**: BAJO
- **Leer antes**:
  - `knowledge-base/06_funcionalidades.md` Épicas 9, 10, 5
  - `knowledge-base/07_flujos_principales.md` FL-08, FL-11, FL-12

---

## Resumen

| Métrica | Valor |
|---------|-------|
| Total de changes | 24 |
| Fases | 6 (FASE 0 a FASE 5) |
| Camino crítico | 10 changes (`C-01 → C-02 → C-03 → C-04 → C-06 → C-07 → C-09 → C-10 → C-11 → C-12`) |
| Gates de paralelismo | 11 (GATE 0 a GATE 10) |
| Changes CRITICO (governance) | 6 (C-02, C-03, C-04, C-05, C-07, C-18) |
| Primer fork | GATE 4 (tras C-04, seguridad lista) |

**Primer change recomendado**: `C-01` (foundation-setup).

Para arrancar: `/opsx:propose C-01-foundation-setup`
