## Why

El sistema necesita calcular, visualizar y cerrar las liquidaciones de honorarios docentes, incluyendo la gestión separada de docentes que facturan. Sin este módulo, el equipo de finanzas no puede operar el ciclo de pago de manera trazable e inmutable dentro de la plataforma.

## What Changes

- **Nuevo**: modelos `SalarioBase` y `SalarioPlus` con vigencia temporal para la grilla salarial del tenant.
- **Nuevo**: modelo `Liquidacion` por (cohorte × período × docente), con separación NEXO / factura / general y cierre inmutable.
- **Nuevo**: modelo `Factura` para docentes monotributistas con flujo propio de gestión.
- **Nuevo**: cálculo automático de liquidación: `Total = Base(rol vigente) + Σ(Plus(clave_activa, rol))` donde cada clave activa cuenta una sola vez (RN-33, RN-34).
- **Nuevo**: API `POST /liquidaciones/calcular` (calcula período), `GET /liquidaciones`, `POST /liquidaciones/{id}/cerrar` (cierre inmutable, RN-22).
- **Nuevo**: API CRUD `\api\liquidaciones\salarios` para ABM de grilla (FINANZAS con `liquidaciones:configurar-salarios`).
- **Nuevo**: API CRUD `\api\facturas` para ABM y cambio de estado de facturas.
- **Nuevo**: vista segmentada (general / NEXO / factura) con KPIs `Total sin factura` y `Total con factura` (RN-36, RN-37, RN-38).
- **Nuevo**: evento de auditoría `LIQUIDACION_CERRAR` con payload completo.
- **Nuevo**: guards `liquidaciones:ver`, `liquidaciones:calcular`, `liquidaciones:cerrar`, `liquidaciones:configurar-salarios`, `liquidaciones:exportar`.

## Capabilities

### New Capabilities

- `liquidaciones-y-honorarios`: Gestión del ciclo completo de liquidaciones de honorarios docentes — grilla salarial con vigencia, cálculo automático Base+Plus, cierre inmutable por (cohorte × período), separación contable factura/no-factura, KPIs, historial y gestión de facturas de docentes monotributistas.

### Modified Capabilities

_(ninguna — las entidades de usuario y asignación ya existen y no cambian sus contratos)_

## Impact

- **Nuevas tablas**: `salario_base`, `salario_plus`, `liquidacion`, `factura` — migración `0NN_liquidaciones_honorarios`.
- **Modelos relacionados**: `Usuario` (campo `facturador`, `cbu`, `banco`), `Asignacion` (para derivar comisiones activas y clave Plus), `Cohorte` (dimensión de la liquidación).
- **RBAC**: nuevos permisos `liquidaciones:*` asignados al rol FINANZAS.
- **Audit log**: evento `LIQUIDACION_CERRAR` integrado al worker de auditoría existente.
- **Sin cambios de contrato** en módulos ya implementados (C-01–C-17).
