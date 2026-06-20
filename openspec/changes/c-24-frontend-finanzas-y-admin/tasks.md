## 1. Rutas y estructura de features

- [x] 1.1 Crear directorios `frontend/src/features/liquidaciones/` y `admin/` con subcarpetas `components/`, `hooks/`, `services/`, `types/`, `pages/`
- [x] 1.2 Crear tipos TypeScript: `Liquidacion`, `SalarioBase`, `SalarioPlus`, `Factura` en `liquidaciones/types/index.ts`
- [x] 1.3 Crear tipos TypeScript: `Carrera`, `Cohorte`, `Materia`, `UsuarioResumen`, `PanelAuditoria`, `AuditLogEntry` en `admin/types/index.ts`
- [x] 1.4 Registrar rutas lazy-load en `router.tsx`: `/liquidaciones`, `/liquidaciones/grilla-salarial`, `/liquidaciones/facturas`, `/liquidaciones/historial`, `/admin/carreras`, `/admin/cohortes`, `/admin/materias`, `/admin/usuarios`, `/admin/auditoria`, `/admin/auditoria/log`
- [x] 1.5 Agregar entradas en `menuItems.ts` para roles FINANZAS y ADMIN

## 2. Feature: liquidaciones (F10.1–F10.6, FL-08)

- [x] 2.1 Crear `liquidaciones/services/liquidacionesApi.ts` con wrappers axios para todos los endpoints de `/api/liquidaciones/*`, `/api/salarios/*` y `/api/facturas/*`
- [x] 2.2 Escribir tests para `LiquidacionesPage`: KPIs cabecera, segmentos general/NEXO/factura, botón cerrar período deshabilitado si ya cerrada
- [x] 2.3 Implementar `useLiquidaciones` hook (query con filtro período, identidad del tenant desde JWT)
- [x] 2.4 Implementar `LiquidacionesPage`: selector de período, KPIs "Total sin factura"/"Total con factura", tabla segmentada en tres secciones, botón exportar, botón cerrar liquidación con confirmación inline
- [x] 2.5 Implementar `useCerrarLiquidacion` hook (mutación POST, invalida cache)
- [x] 2.6 Escribir tests para `GrillaSalarialPage`: lista salarios base, lista plus, agregar salario base OK, eliminar plus muestra confirmación
- [x] 2.7 Implementar `useGrillaSalarial` hook (queries + mutaciones para salarios base y plus)
- [x] 2.8 Implementar `GrillaSalarialPage`: dos tablas (salario base / plus) con formulario de alta inline por tabla; eliminar con confirmación
- [x] 2.9 Escribir tests para `FacturasPage`: lista facturas, filtros estado/docente, marcar abonada
- [x] 2.10 Implementar `useFacturas` hook (query con filtros sincronizados con search-params URL) + `useMarcarFacturaAbonada` (mutación PATCH)
- [x] 2.11 Implementar `FacturasPage`: tabla con columnas docente/período/detalle/estado/acciones, filtros, botón marcar abonada
- [x] 2.12 Escribir tests para `HistorialLiquidacionesPage`: lista liquidaciones cerradas, read-only sin botón de cierre
- [x] 2.13 Implementar `HistorialLiquidacionesPage`: tabla de liquidaciones cerradas por período, solo lectura

## 3. Feature: estructura académica (F5.1–F5.2, FL-12)

- [x] 3.1 Crear `admin/services/adminApi.ts` con wrappers para `/api/estructura/*`, `/api/admin/usuarios/*` y `/api/auditoria/*`
- [x] 3.2 Escribir tests para `CarrerasPage`: lista carreras, crear carrera OK, activar/desactivar carrera
- [x] 3.3 Implementar `useCarreras` hook (query + mutaciones crear/editar)
- [x] 3.4 Implementar `CarrerasPage`: tabla con formulario de alta inline, toggle activa/inactiva
- [x] 3.5 Escribir tests para `CohorteAdminPage`: lista cohortes, crear cohorte con validación fechas
- [x] 3.6 Implementar `useCohortes` hook (query + mutaciones)
- [x] 3.7 Implementar `CohorteAdminPage`: tabla + formulario de alta con campos nombre/año/vigencia
- [x] 3.8 Escribir tests para `MateriasPage`: lista materias, crear materia, toggle activa
- [x] 3.9 Implementar `useMaterias` hook (query + mutaciones)
- [x] 3.10 Implementar `MateriasPage`: tabla con formulario inline

## 4. Feature: usuarios admin (F4.1)

- [x] 4.1 Escribir tests para `UsuariosAdminPage`: lista usuarios con filtro activo/inactivo, crear usuario, desactivar usuario
- [x] 4.2 Implementar `useUsuariosAdmin` hook (query con filtro activo + mutaciones crear/editar)
- [x] 4.3 Implementar `UsuariosAdminPage`: tabla con columnas nombre/email/roles/estado/cobro, formulario de alta en modal/inline, toggle activo

## 5. Feature: auditoría y métricas (F9.1–F9.2, FL-11)

- [x] 5.1 Escribir tests para `AuditoriaPage`: filtros fecha/materia/usuario, tabla de acciones por día, estado de comunicaciones por docente, últimas acciones
- [x] 5.2 Implementar `usePanelAuditoria` hook (query con filtros sincronizados a search-params)
- [x] 5.3 Implementar `AuditoriaPage`: panel con tres sub-secciones (acciones/día como tabla con barras CSS, estado de comms, últimas acciones)
- [x] 5.4 Escribir tests para `LogAuditoriaPage`: filtros completos, tabla con columnas fecha/usuario/acción/materia/filas/ip
- [x] 5.5 Implementar `useLogAuditoria` hook (query con filtros: desde/hasta/materia/usuario/estado)
- [x] 5.6 Implementar `LogAuditoriaPage`: tabla completa con todos los campos del log, filtros en header

## 6. Cierre

- [x] 6.1 Ejecutar suite completa: `cd frontend && npm test` — todos los tests deben pasar
- [x] 6.2 Verificar typecheck: `npm run typecheck`
- [x] 6.3 Archivar el change: `/opsx:archive c-24-frontend-finanzas-y-admin`
