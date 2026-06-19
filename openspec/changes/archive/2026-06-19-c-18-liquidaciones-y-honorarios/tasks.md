## 1. Migración y modelos base

- [x] 1.1 Crear migración `018_liquidaciones_honorarios`: tablas `salario_base`, `salario_plus`, `liquidacion`, `factura` + columna `plus_key TEXT NULL` en `instancia_dictado`
- [x] 1.2 Modelo `SalarioBase` (SQLAlchemy): `id`, `tenant_id`, `rol`, `monto`, `desde`, `hasta`; constraint unicidad de vigencia por rol
- [x] 1.3 Modelo `SalarioPlus` (SQLAlchemy): `id`, `tenant_id`, `grupo` (clave Plus), `rol`, `descripcion`, `monto`, `desde`, `hasta`
- [x] 1.4 Modelo `Liquidacion` (SQLAlchemy): `id`, `tenant_id`, `cohorte_id`, `periodo`, `usuario_id`, `rol`, `comisiones`, `monto_base`, `monto_plus`, `total`, `es_nexo`, `excluido_por_factura`, `estado` (Abierta/Cerrada), timestamps
- [x] 1.5 Modelo `Factura` (SQLAlchemy): `id`, `tenant_id`, `usuario_id`, `periodo`, `detalle`, `referencia_archivo`, `tamano_kb`, `estado` (Pendiente/Abonada), `cargada_at`, `abonada_at`
- [x] 1.6 Agregar `plus_key: str | None` al modelo `InstanciaDictado` existente

## 2. Schemas Pydantic

- [x] 2.1 `SalarioBaseCreate`, `SalarioBaseResponse` con `extra='forbid'`
- [x] 2.2 `SalarioBaseUpdate` (solo `monto`, `hasta`)
- [x] 2.3 `SalarioPlusCreate`, `SalarioPlusResponse` con `extra='forbid'`
- [x] 2.4 `LiquidacionResponse`, `LiquidacionDetalle` (con `comisiones_detalle` y `claves_activas`)
- [x] 2.5 `LiquidacionCalcularRequest` (`cohorte_id`, `periodo`)
- [x] 2.6 `LiquidacionVistaPeriodo` (response segmentado: `general`, `nexo`, `facturantes`, KPIs)
- [x] 2.7 `FacturaCreate`, `FacturaResponse`, `FacturaPatchRequest` con `extra='forbid'`
- [x] 2.8 `LiquidacionCalcularResponse` (lista de liquidaciones creadas/actualizadas + `omitidos`)

## 3. Repositorios

- [x] 3.1 `SalarioBaseRepository`: `create`, `list_by_tenant`, `get_vigente_para_periodo(rol, periodo)`, `check_solapamiento`
- [x] 3.2 `SalarioPlusRepository`: `create`, `list_by_tenant`, `get_vigentes_para_periodo(periodo)` → dict `{(grupo, rol): monto}`
- [x] 3.3 `LiquidacionRepository`: `create_or_update`, `list_by_periodo`, `get_by_id`, `cerrar`, `list_historial`
- [x] 3.4 `FacturaRepository`: `create`, `get_by_id`, `list_with_filters`, `update_estado`

## 4. Lógica de cálculo (LiquidacionService)

- [x] 4.1 `calcular_periodo(cohorte_id, periodo, tenant_id)`: obtiene docentes activos de la cohorte vía `AsignacionRepository`, filtra sin CBU/banco → lista `omitidos`
- [x] 4.2 Para cada docente activo: derivar `rol`, obtener `SalarioBase` vigente → `monto_base`
- [x] 4.3 Derivar `claves_activas`: consulta `InstanciaDictado.plus_key` de las instancias asignadas al docente en el período; `DISTINCT` de claves no-NULL
- [x] 4.4 Para cada clave activa: buscar `SalarioPlus` vigente para `(clave, rol)` → sumar → `monto_plus`
- [x] 4.5 Determinar `es_nexo` (rol == NEXO) y `excluido_por_factura` (`usuario.facturador == true`)
- [x] 4.6 `total = monto_base + monto_plus`; persistir vía `LiquidacionRepository.create_or_update`
- [x] 4.7 `cerrar_periodo(cohorte_id, periodo)`: verificar que ningún registro esté Cerrado → cambiar todos a Cerrada → registrar `LIQUIDACION_CERRAR` en audit log con snapshot

## 5. Lógica de grilla salarial (SalarioService)

- [x] 5.1 `create_base(data)`: validar solapamiento antes de persistir; retornar 409 si hay solapamiento
- [x] 5.2 `create_plus(data)`: persistir sin validación de solapamiento (plus puede coexistir en distintas claves)
- [x] 5.3 `list_grilla()`: retornar `SalarioBase` + `SalarioPlus` del tenant

## 6. Lógica de facturas (FacturaService)

- [x] 6.1 `create(data)`: verificar que `usuario.facturador == true`; persistir con estado Pendiente
- [x] 6.2 `update_estado(factura_id, estado)`: solo Pendiente → Abonada; registrar `abonada_at`
- [x] 6.3 `list_with_filters(usuario_id, estado, desde, hasta)`: retornar facturas paginadas

## 7. Routers

- [x] 7.1 `POST /liquidaciones/calcular` — guard `liquidaciones:calcular`; delega a `LiquidacionService.calcular_periodo`
- [x] 7.2 `GET /liquidaciones` — guard `liquidaciones:ver`; filtros: `cohorte_id`, `periodo`, `estado`; retorna `LiquidacionVistaPeriodo`
- [x] 7.3 `GET /liquidaciones/{id}` — guard `liquidaciones:ver`; retorna `LiquidacionDetalle`
- [x] 7.4 `POST /liquidaciones/{id}/cerrar` — guard `liquidaciones:cerrar`; delega a `LiquidacionService.cerrar_periodo`
- [x] 7.5 `GET /liquidaciones/salarios` — guard `liquidaciones:ver`; retorna grilla completa
- [x] 7.6 `POST /liquidaciones/salarios/base` — guard `liquidaciones:configurar-salarios`
- [x] 7.7 `PATCH /liquidaciones/salarios/base/{id}` — guard `liquidaciones:configurar-salarios`
- [x] 7.8 `POST /liquidaciones/salarios/plus` — guard `liquidaciones:configurar-salarios`
- [x] 7.9 `PATCH /liquidaciones/salarios/plus/{id}` — guard `liquidaciones:configurar-salarios`
- [x] 7.10 `POST /facturas` — guard `liquidaciones:calcular`
- [x] 7.11 `GET /facturas` — guard `liquidaciones:ver`; filtros: `usuario_id`, `estado`, `desde`, `hasta`
- [x] 7.12 `PATCH /facturas/{id}` — guard `liquidaciones:calcular`

## 8. RBAC

- [x] 8.1 Registrar permisos `liquidaciones:ver`, `liquidaciones:calcular`, `liquidaciones:cerrar`, `liquidaciones:configurar-salarios`, `liquidaciones:exportar` en la matriz de permisos
- [x] 8.2 Asignar los cinco permisos al rol FINANZAS en los seeds/fixtures del tenant

## 9. Auditoría

- [x] 9.1 Registrar `LIQUIDACION_CERRAR` en `AuditLogRepository` al cerrar: incluir `cohorte_id`, `periodo`, snapshot JSON de todas las liquidaciones del período (docente, rol, total, estado)

## 10. Tests — Grilla salarial

- [x] 10.1 Test: alta de `SalarioBase` exitosa
- [x] 10.2 Test: alta de `SalarioBase` rechazada por solapamiento de vigencia (mismo rol)
- [x] 10.3 Test: `get_vigente_para_periodo` retorna el registro correcto según fecha
- [x] 10.4 Test: `get_vigente_para_periodo` retorna `None` si no hay registro vigente
- [x] 10.5 Test: alta de `SalarioPlus` exitosa
- [x] 10.6 Test: lista de grilla salarial del tenant

## 11. Tests — Cálculo de liquidación

- [x] 11.1 Test: cálculo con docente que tiene base + plus de una clave activa
- [x] 11.2 Test: cálculo con docente con 3 comisiones de la misma clave → Plus contado una sola vez
- [x] 11.3 Test: cálculo con docente con múltiples claves activas distintas → suma de todos los plus
- [x] 11.4 Test: cálculo con docente con instancias sin `plus_key` → `monto_plus = 0`
- [x] 11.5 Test: docente sin CBU omitido del cálculo y aparece en `omitidos`
- [x] 11.6 Test: docente `facturador=true` marcado con `excluido_por_factura=True`
- [x] 11.7 Test: docente NEXO marcado con `es_nexo=True`
- [x] 11.8 Test: recálculo de período Abierto actualiza registros existentes
- [x] 11.9 Test: intento de cálculo sobre período Cerrado retorna 409

## 12. Tests — Cierre de liquidación

- [x] 12.1 Test: cierre exitoso de liquidación Abierta → estado Cerrada
- [x] 12.2 Test: cierre genera evento `LIQUIDACION_CERRAR` en audit log con snapshot correcto
- [x] 12.3 Test: cierre rechazado si ya está Cerrada (409)

## 13. Tests — Vista segmentada y KPIs

- [x] 13.1 Test: vista retorna tres segmentos (`general`, `nexo`, `facturantes`) bien clasificados
- [x] 13.2 Test: KPI `total_sin_factura` incluye general + nexo, excluye facturantes
- [x] 13.3 Test: KPI `total_con_factura` incluye suma de montos de docentes facturantes
- [x] 13.4 Test: historial retorna solo liquidaciones Cerradas de la cohorte, ordenadas por período desc

## 14. Tests — Facturas

- [x] 14.1 Test: carga de factura para docente facturante → estado Pendiente
- [x] 14.2 Test: intento de carga para docente no-facturante → 422 o 403
- [x] 14.3 Test: cambio de estado Pendiente → Abonada; `abonada_at` registrado
- [x] 14.4 Test: filtros de listado por `usuario_id` y `estado`

## 15. Tests — RBAC y multi-tenancy

- [x] 15.1 Test: PROFESOR recibe 403 al intentar `GET /liquidaciones` (aislamiento por tenant_id)
- [x] 15.2 Test: FINANZAS puede calcular, cerrar y administrar grilla (cubierto en 11.x y 12.x)
- [x] 15.3 Test: liquidaciones de tenant A no visibles para FINANZAS de tenant B
- [x] 15.4 Test: facturas de tenant A no visibles para FINANZAS de tenant B
