## Context

C-10 está en el camino crítico (C-09 padrón → **C-10 calificaciones** → C-11 → C-12). El padrón ya existe (`version_padron`, `entrada_padron`) y expone el patrón de scoping por `materia_id` (UUID indexado, no FK dura) y cifrado de PII en el Service. C-10 agrega la capa de calificaciones encima de ese padrón: dos modelos nuevos, dos flujos de importación desde archivo del LMS, y configuración de umbral por docente.

Restricciones de proyecto (reglas duras de `CLAUDE.md`): Clean Architecture unidireccional (Routers → Services → Repositories → Models), multi-tenancy row-level, RBAC fino fail-closed, identidad siempre desde el JWT, soft delete, Pydantic `extra='forbid'`, una migración por cambio de schema, ≤500 LOC por archivo, Strict TDD con DB real (sin mocks de DB), cobertura ≥80% líneas / ≥90% reglas de negocio. Governance del dominio: **MEDIO** (lógica de dominio + integración LMS) → implementar con checkpoints, surfaceando decisiones no obvias.

## Goals / Non-Goals

**Goals:**
- Persistir calificaciones (`Calificacion`) por alumno × actividad, con nota numérica y/o textual.
- Derivar `aprobado` de forma determinística y testeable mediante una **función pura** de dominio.
- Importar calificaciones desde archivo del LMS detectando columnas numéricas (RN-01) y textuales (RN-02), con vista previa y selección de actividades (F1.1).
- Importar el reporte de finalización y detectar entregas sin corregir, solo escala textual (F1.2 / RN-07, RN-08).
- Configurar umbral por asignación docente sin afectar a otros docentes (F2.1 / RN-03, scope aislado análogo a RN-04).
- Auditar cada importación (`CALIFICACIONES_IMPORTAR`).

**Non-Goals:**
- Cálculo de "alumnos atrasados" y rankings (RN-06, RN-09) → eso es C-11. C-10 solo deja `aprobado` derivable para que C-11 lo consuma.
- Carga manual de notas vía UI (`origen = Manual` queda modelado pero su endpoint de alta manual es posterior).
- Resolver PA-01 (catálogo Materia vs InstanciaDictado) — se documenta como supuesto.
- Integración con Moodle WS para calificaciones (este change es solo archivo; el WS de calificaciones, si aplica, es trabajo futuro).
- Frontend (vive en la fase de UI).

## Decisions

### D1 — Scoping por `materia_id` UUID indexado, NO FK dura (sigue C-09, no el ERD)
El ERD (§4) dice que `Calificacion` referencia `InstanciaDictado` y `UmbralMateria` referencia `Asignacion`+`Materia`. Pero la fundación implementada en C-09 **no** usa `InstanciaDictado`: scopea por `materia_id: UUID` indexado (sin FK) más `EntradaPadron.version_id` (FK). Para mantener consistencia con lo construido:
- `Calificacion.entrada_padron_id` → `ForeignKey("entrada_padron.id", ondelete="CASCADE")`.
- `Calificacion.materia_id` → `UUID(as_uuid=True)` indexado, **sin** FK (mismo patrón que `version_padron.materia_id`).
- `UmbralMateria.asignacion_id` → `ForeignKey("asignacion.id", ...)` (tabla `asignacion`, confirmada en `backend/app/models/asignacion.py`).
- `UmbralMateria.materia_id` → `UUID(as_uuid=True)` indexado, sin FK.

**Alternativa descartada**: FK dura a `materia`/`instancia_dictado`. Se descarta porque la estructura académica (C-06) gestiona su propia tabla de materias por separado y PA-01 sigue abierto; una FK dura acoplaría C-10 a un modelo aún no estabilizado. Se documenta como supuesto en Open Questions.

### D2 — `aprobado` es DERIVADO por una función pura, no una columna de verdad
`aprobado` no es un hecho independiente: depende del umbral vigente, que puede cambiar. Persistirlo como verdad lo dejaría desincronizado al reconfigurar el umbral. Decisión:
- La derivación vive en `backend/app/domain/aprobado.py` como **función pura** `derivar_aprobado(nota_numerica, nota_textual, umbral_pct, nota_maxima, valores_aprobatorios) -> bool` — sin I/O, sin DB, sin sesión.
- Lógica (E7 §216, RN-02, RN-03):
  - Si `nota_numerica` presente → `aprobado = nota_numerica >= (umbral_pct/100) * nota_maxima`. **Precedencia: la numérica gana** cuando coexisten ambas (la escala numérica es la fuente cuantitativa primaria).
  - Si solo `nota_textual` → `aprobado = nota_textual ∈ valores_aprobatorios`.
  - Si ninguna → `False` (sin nota = no aprobado a efectos de seguimiento).
- El Service resuelve el umbral (UmbralMateria de la asignación, o defecto 60 del tenant) y la `nota_maxima`, y llama a la función pura. **`aprobado` no se almacena como columna**; se calcula al leer/proyectar. Esto la hace trivial de testear (Strict TDD, ≥90%).

**Alternativa descartada**: método en el modelo (`Calificacion.aprobado` property). Se descarta porque acopla la regla a SQLAlchemy y al umbral cargado, dificultando el test puro y violando "nada de lógica de negocio fuera del dominio/servicio".

### D3 — Detección de columnas: RN-01 (`(Real)`) y RN-02 (escala textual)
El parser del LMS (en el Service, no en el router ni el repo) clasifica columnas:
- Columna **numérica**: encabezado termina en el sufijo literal `(Real)` (RN-01). Cualquier otra columna NO se procesa como nota numérica.
- Columna **textual**: celdas con valores de la escala cualitativa configurada (`valores_aprobatorios` ∪ valores no aprobatorios) (RN-02).
- La **vista previa** (`preview`) devuelve la lista de actividades detectadas (con su escala detectada: numérica|textual) y los alumnos, **sin persistir**. El usuario luego envía la **selección de actividades**; solo esas se persisten/analizan.

### D4 — Cruce reporte de finalización (F1.2 / RN-07, RN-08)
El servicio cruza el reporte de finalización (entregado por alumno × actividad) con las calificaciones ya importadas. Una entrada cuenta como "posible trabajo sin corregir" si: actividad **finalizada** por el alumno **y sin** calificación registrada. RN-08: solo se incluyen actividades de **escala textual**; las de escala numérica se excluyen (ausencia de nota numérica = no entregado, no pendiente de corrección).

### D5 — Umbral scope-isolated por asignación docente (RN-03 + RN-04 análogo)
`UmbralMateria` se ancla a `asignacion_id` (la asignación docente del usuario en esa materia), no a la materia global. Configurar el umbral de un docente no toca el de otro. Al derivar `aprobado`, el Service busca el `UmbralMateria` de la asignación vigente del docente; si no existe, usa el defecto del tenant (60%). Único parcial: a lo sumo un `UmbralMateria` por `(tenant, asignacion, materia)`.

### D6 — RBAC y auditoría siguiendo el patrón de padrón
- Permisos nuevos `calificaciones:importar` (PROFESOR, COORDINADOR) y `calificaciones:leer` (PROFESOR, TUTOR, COORDINADOR, ADMIN), sembrados en la migración 009 con el mismo patrón INSERT que `008_padron_tables`. Importar y configurar umbral usan `calificaciones:importar` (FL-02 pasos 3–4); las lecturas usan `calificaciones:leer`.
- Endpoints declaran `Depends(require_permission(...))`, fail-closed (sin permiso → 403). Identidad (tenant_id, user_id, roles) **siempre** desde el `CurrentUser` del JWT, nunca de la URL/body.
- Scope tenant: `materia_id` fuera del tenant del JWT → 404 (no revelar existencia en otro tenant), igual que padrón.
- Auditoría: tras cada importación exitosa, el Service registra `AuditLog` con `accion="CALIFICACIONES_IMPORTAR"`, `materia_id`, `filas_afectadas`, IP y user agent del request.

### D7 — Migración única 009
Una sola migración `009_calificaciones_tables` (down_revision `a8b9c0d1e2f3` = 008): crea `calificacion` y `umbral_materia` con índices por `tenant_id`/`materia_id`/`entrada_padron_id`/`asignacion_id`, y siembra/revoca los permisos. `aprobado` NO es columna (D2).

## Risks / Trade-offs

- **[PA-01 sin resolver — `materia_id` sin FK]** → Mitigación: indexar `materia_id` y documentar el supuesto; cuando PA-01 se cierre, una migración futura puede promover a FK. El scoping por tenant + materia ya protege la integridad lógica.
- **[`aprobado` recalculado en cada lectura podría ser costoso]** → Mitigación: la derivación es O(1) por fila y pura; si C-11 necesita performance, puede materializar en proyección/caché sin tocar la fuente de verdad.
- **[Heterogeneidad de exports del LMS]** → Mitigación: RN-01 fija el contrato de detección numérica (sufijo `(Real)`); la escala textual es configuración (`valores_aprobatorios`). Columnas no reconocidas se ignoran sin error (igual que padrón ignora columnas extra).
- **[Precedencia numérica vs textual ambigua si el LMS exporta ambas]** → Mitigación: D2 fija "numérica gana" y se cubre con test explícito de precedencia.
- **[Cruce de finalización sin calificaciones previas]** → Mitigación: si no hay calificaciones importadas, todas las textuales finalizadas figuran como "sin corregir"; comportamiento correcto y testeado.

## Migration Plan

1. Crear modelos `Calificacion` + `UmbralMateria` + enum `OrigenCalificacion` (TDD: modelos + invariantes).
2. Escribir migración `009_calificaciones_tables` (up: tablas + índices + permisos; down: drop + revoke). Una sola migración.
3. Implementar la función pura `derivar_aprobado` (TDD primero, ≥90%).
4. Repositorios (filtro tenant por defecto), servicios (parser/preview/persistencia/cruce/audit/umbral), schemas (`extra='forbid'`), router (RBAC).
5. Registrar el router en `app/main.py` y los modelos donde se importan para Alembic autogenerate/metadata.
6. **Rollback**: `alembic downgrade -1` ejecuta el `downgrade()` (drop de tablas + DELETE de permisos). Soft delete en datos; sin hard delete de calificaciones en operación normal.

## Open Questions

- **PA-01 (ALTA)** — Catálogo Materia vs InstanciaDictado. C-10 sigue la convención C-09 (`materia_id` UUID indexado, sin FK) como supuesto. Si PA-01 se resuelve a favor de `InstanciaDictado`, habrá que migrar `materia_id` → FK / `instancia_dictado_id`.
- **`nota_maxima` por actividad** — RN-03 calcula el umbral como % de la "nota máxima posible". ¿La nota máxima es por actividad (del export del LMS), o global (ej. 10)? Supuesto inicial: el export del LMS provee la escala/máximo por actividad; si no, se asume 10 como default del tenant. Confirmar con negocio.
- **Conjunto de valores no-aprobatorios** — RN-02 lista "No satisfactorio"/"No alcanzado" como no aprobados, pero la lista completa es configuración. C-10 trata cualquier valor textual fuera de `valores_aprobatorios` como no aprobado.
