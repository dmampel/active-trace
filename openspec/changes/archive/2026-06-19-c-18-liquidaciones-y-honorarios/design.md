## Context

C-18 implementa el módulo de liquidaciones y honorarios sobre la base ya provista por C-01–C-17. Las entidades de `Usuario` (con `facturador`, `cbu`, `banco`), `Asignacion` (comisiones activas) y `Cohorte` ya existen. El módulo de liquidaciones es de governance **CRÍTICO**: calcula y congela importes de pago reales; un error en el cálculo o en el cierre afecta directamente a los docentes.

Las preguntas abiertas PA-22 y PA-23 que bloqueaban este change ya fueron cerradas:
- Claves de Plus: texto libre configurable por ADMIN del tenant (no catálogo fijo).
- Mapeo materia→clave: exactamente una clave por `InstanciaDictado` (FK nullable en la instancia).
- Acumulación: Plus se aplica UNA SOLA VEZ por clave activa, sin importar cuántas comisiones del docente caen en esa clave.

## Goals / Non-Goals

**Goals:**
- Implementar la grilla salarial (`SalarioBase`, `SalarioPlus`) con vigencia temporal.
- Cálculo automático de liquidaciones por (cohorte × período × docente).
- Flujo de cierre inmutable (RN-22): liquidación Abierta → Cerrada, sin reversión.
- Vista segmentada: general / NEXO / facturantes, con KPIs contables.
- ABM de facturas de docentes monotributistas con estado Pendiente/Abonada.
- Audit trail de `LIQUIDACION_CERRAR` con payload completo.
- Guards RBAC `liquidaciones:*` exclusivos del rol FINANZAS.

**Non-Goals:**
- Integración con sistemas de pago externos o bancos.
- Cálculo de aportes patronales, impuestos o retenciones.
- Notificaciones automáticas a docentes al cerrar la liquidación.
- Frontend (C-24).

## Decisions

### D1 — Clave Plus en `InstanciaDictado`, no en `Materia`

**Decisión**: el mapeo materia→clave de Plus vive como campo `plus_key: text | NULL` en `InstanciaDictado`, no en `Materia`.

**Rationale**: la misma materia puede tener distintas claves en diferentes cohortes/períodos (cambio curricular). `InstanciaDictado` ya es la unidad de oferta concreta, por lo que la configuración de Plus al nivel de instancia es correcta semánticamente y no requiere una tabla de mapeo adicional.

**Alternativa descartada**: tabla separada `MateriaPlusConfig` — introduce join innecesario y complejidad sin beneficio real, dado que el mapeo es 1:1 por instancia.

---

### D2 — Cálculo lazy (on-demand), no materialización incremental

**Decisión**: el cálculo de la liquidación se ejecuta on-demand al llamar `POST /liquidaciones/calcular`. Los registros `Liquidacion` se crean o actualizan para el período dado si el estado es `Abierta`. Una vez `Cerrada`, el endpoint rechaza nuevos cálculos para ese período.

**Rationale**: los períodos liquidados son relativamente pequeños (decenas de docentes por cohorte); el cálculo completo tarda millisegundos. Evita complejidad de eventos de dominio o triggers de recalculo incremental.

**Alternativa descartada**: job periódico de recálculo — innecesario para el volumen actual; introduce opacidad sobre cuándo se ejecutó el último cálculo.

---

### D3 — Inmutabilidad por campo de estado (no tabla separada)

**Decisión**: la inmutabilidad de una liquidación cerrada se garantiza a nivel de servicio: `LiquidacionService.cerrar()` cambia `estado = Cerrada` y los endpoints de escritura verifican el estado antes de operar. No se usa una tabla de auditoría separada ni triggers de BD para este fin.

**Rationale**: la regla de negocio (RN-22) es de dominio, no de base de datos. Testeable unitariamente, sin acoplar la lógica a triggers específicos de PostgreSQL. El audit log (`LIQUIDACION_CERRAR`) captura el snapshot completo.

---

### D4 — `claves_activas` derivadas de `Asignacion` + `InstanciaDictado.plus_key`

**Decisión**: al calcular el Plus, el servicio consulta las `Asignacion` activas del docente en el período, obtiene las `InstanciaDictado` asociadas, extrae sus `plus_key` distintas (filtrando `NULL`), y suma un registro `SalarioPlus` por cada clave activa en el período.

**Rationale**: implementa RN-33/RN-34 sin lógica ambigua. La deduplicación (`DISTINCT plus_key`) es trivial en SQL y asegura "una vez por clave activa".

---

### D5 — Factura como entidad propia sin relación con Liquidacion

**Decisión**: `Factura` es una entidad independiente (no FK a `Liquidacion`). La exclusión del facturante de la liquidación se maneja con `excluido_por_factura = true` en `Liquidacion` (si se genera el registro) o simplemente no incluyendo al docente en el cálculo general.

**Rationale**: los docentes facturantes no tienen liquidación en el sentido Base+Plus (RN-35). Forzar un FK crearía un registro `Liquidacion` vacío solo para vincular la factura, lo cual es semánticamente incorrecto.

---

### D6 — Migración 018 agrega `plus_key` a `instancia_dictado`

**Decisión**: la migración `018_liquidaciones_honorarios` crea las cuatro tablas nuevas **y** agrega la columna `plus_key TEXT NULL` a la tabla `instancia_dictado` existente. Es una ALTER TABLE no destructiva (nullable).

**Rationale**: la columna es necesaria para el cálculo de Plus (D4). Agregarla en la misma migración mantiene atomicidad del cambio de schema.

## Risks / Trade-offs

- **[Riesgo] Cierre sin datos bancarios**: un docente sin CBU/banco no debería ser incluido en una liquidación procesable (RN-26). Mitigación: `LiquidacionService.calcular()` excluye docentes sin datos bancarios y los reporta en el response como `omitidos`.
- **[Riesgo] Solapamiento de vigencias en grilla salarial**: si FINANZAS crea dos registros `SalarioBase` con rangos solapados para el mismo rol, el cálculo es ambiguo. Mitigación: el servicio rechaza el alta si existe un registro vigente solapado para el mismo rol en el período.
- **[Riesgo] `plus_key` null en instancias**: si una instancia no tiene `plus_key` asignada, el docente no recibe Plus para esa comisión. Mitigación: el cálculo ignora instancias con `plus_key = NULL` sin error (comportamiento esperado por diseño); el endpoint de cálculo devuelve qué claves se computaron por docente.
- **[Trade-off] Cálculo on-demand vs. snapshot pre-calculado**: elegimos on-demand por simplicidad. Si el volumen crece a miles de docentes por cohorte, habrá que mover a un job async. Mitigación futura: extraer el cálculo a un worker y retornar un job ID.

## Migration Plan

1. `docker start activia-test` (DB de test en puerto 5433).
2. `alembic upgrade head` aplica la migración `018_liquidaciones_honorarios`:
   - Crea `salario_base`, `salario_plus`, `liquidacion`, `factura`.
   - Agrega `plus_key TEXT NULL` a `instancia_dictado`.
3. Sin datos existentes que migrar — las nuevas tablas parten vacías.
4. Rollback: `alembic downgrade -1` elimina las cuatro tablas y la columna.

## Open Questions

_(ninguna — PA-22 y PA-23 cerradas en sesión anterior)_
