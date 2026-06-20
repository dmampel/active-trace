# C-24 `frontend-finanzas-y-admin` — Propuesta

## Contexto

Con C-23 cerrado, la SPA tiene cubiertos los flujos de PROFESOR y COORDINADOR. Este change implementa los dos módulos finales del frontend:

1. **FINANZAS** — Liquidaciones de honorarios: vista segmentada (general / NEXO / factura), cierre de período, historial, grilla salarial, ABM de facturas.
2. **ADMIN** — Estructura académica (carreras, cohortes, materias, instancias), gestión de usuarios del tenant, panel de auditoría e interacciones, y log completo.

Ambos módulos consumen endpoints del backend ya implementados: `C-06` (estructura académica), `C-07` (usuarios), `C-18` (liquidaciones), `C-19` (auditoría).

## Valor

- **FINANZAS** puede cerrar períodos, supervisar facturas y obtener KPIs contables desde la SPA.
- **ADMIN** puede configurar toda la estructura académica, gestionar usuarios y supervisar la actividad del sistema, completando el ciclo de administración del tenant.

## Dependencias satisfechas

- `C-21` ✅ (shell + auth + guard)
- `C-18` ✅ (backend liquidaciones)
- `C-19` ✅ (backend auditoría)
- `C-06` ✅ (backend estructura académica)
- `C-07` ✅ (backend usuarios)

## Flujos de dominio cubiertos

- **FL-08** — Liquidación de honorarios (selección período → cálculo → vista → cierre → historial)
- **FL-11** — Auditoría de actividad por docente
- **FL-12** — Configuración inicial: estructura académica, usuarios, grilla salarial

## Módulos frontend a implementar

### Feature `liquidaciones/`
- `LiquidacionesPage` — tabla segmentada por período: general / NEXO / factura + KPIs
- `GrillaSalarialPage` — ABM salario base + plus con vigencia temporal
- `FacturasPage` — listado + ABM de comprobantes de docentes que facturan
- `HistorialLiquidacionesPage` — liquidaciones cerradas (read-only)

### Feature `admin/`
- `CarrerasPage` — ABM carreras
- `CohorteAdminPage` — ABM cohortes
- `MateriasPage` — ABM materias + instancias
- `UsuariosAdminPage` — alta/edición/desactivación de usuarios del tenant
- `AuditoriaPage` — panel de interacciones (gráfico acciones/día, estado comms, log)
- `LogAuditoriaPage` — log completo con filtros (ADMIN only)

## Convenciones (igual que C-22 y C-23)

- Identidad SIEMPRE desde JWT, nunca desde URL/params
- Cada hook usa TanStack Query; filtros sincronizados con search-params URL
- Strict TDD: test que falla → implementación mínima → refactor
- Lazy-load de páginas desde `router.tsx`
- Guards por permiso en cada ruta
