# C-24 `frontend-finanzas-y-admin` — Design

## Estructura de directorios

```
frontend/src/features/
├── liquidaciones/
│   ├── components/
│   │   ├── TablaLiquidacion.tsx         — tabla segmentada (general / NEXO / factura)
│   │   ├── KpisLiquidacion.tsx          — KPIs "Total sin factura" / "Total con factura"
│   │   └── GrillaSalarialForm.tsx       — formulario inline para salario base y plus
│   ├── hooks/
│   │   └── useLiquidaciones.ts          — hooks de TanStack Query para todos los endpoints
│   ├── pages/
│   │   ├── LiquidacionesPage.tsx + .test.tsx
│   │   ├── GrillaSalarialPage.tsx + .test.tsx
│   │   ├── FacturasPage.tsx + .test.tsx
│   │   └── HistorialLiquidacionesPage.tsx + .test.tsx
│   ├── services/
│   │   └── liquidacionesApi.ts          — axios wrappers sobre /api/liquidaciones/* y /api/facturas/*
│   └── types/
│       └── index.ts
│
└── admin/
    ├── components/
    │   ├── GraficoAccionesDia.tsx       — gráfico de acciones por día (nativo con SVG o simple tabla)
    │   └── TablaUsuarios.tsx            — tabla con acciones CRUD inline
    ├── hooks/
    │   └── useAdmin.ts                  — hooks para estructura académica, usuarios y auditoría
    ├── pages/
    │   ├── CarrerasPage.tsx + .test.tsx
    │   ├── CohorteAdminPage.tsx + .test.tsx
    │   ├── MateriasPage.tsx + .test.tsx
    │   ├── UsuariosAdminPage.tsx + .test.tsx
    │   ├── AuditoriaPage.tsx + .test.tsx  — panel F9.1 (interacciones)
    │   └── LogAuditoriaPage.tsx + .test.tsx — log completo F9.2
    ├── services/
    │   └── adminApi.ts                  — axios wrappers sobre /api/admin/* y /api/auditoria/*
    └── types/
        └── index.ts
```

## Router — rutas a agregar en `router.tsx`

| Ruta | Componente | Permiso |
|------|-----------|---------|
| `/liquidaciones` | `LiquidacionesPage` | `liquidaciones:ver` |
| `/liquidaciones/grilla-salarial` | `GrillaSalarialPage` | `liquidaciones:configurar-salarios` |
| `/liquidaciones/facturas` | `FacturasPage` | `liquidaciones:ver` |
| `/liquidaciones/historial` | `HistorialLiquidacionesPage` | `liquidaciones:ver` |
| `/admin/carreras` | `CarrerasPage` | `estructura:gestionar` |
| `/admin/cohortes` | `CohorteAdminPage` | `estructura:gestionar` |
| `/admin/materias` | `MateriasPage` | `estructura:gestionar` |
| `/admin/usuarios` | `UsuariosAdminPage` | `usuarios:gestionar` |
| `/admin/auditoria` | `AuditoriaPage` | `auditoria:ver` |
| `/admin/auditoria/log` | `LogAuditoriaPage` | `auditoria:ver` |

## Contratos de API (endpoints del backend)

### Liquidaciones
- `GET /api/liquidaciones?periodo=YYYY-MM` → `Liquidacion[]`
- `POST /api/liquidaciones/cerrar` `{periodo}` → `{ok: true}`
- `GET /api/liquidaciones/historial` → `Liquidacion[]`
- `GET /api/salarios/base` → `SalarioBase[]`
- `POST /api/salarios/base` `{rol, monto, desde, hasta}`
- `DELETE /api/salarios/base/:id`
- `GET /api/salarios/plus` → `SalarioPlus[]`
- `POST /api/salarios/plus` `{clave, rol, descripcion, monto, desde, hasta}`
- `DELETE /api/salarios/plus/:id`
- `GET /api/facturas?docente=&estado=&desde=&hasta=` → `Factura[]`
- `POST /api/facturas` (multipart)
- `PATCH /api/facturas/:id/estado` `{estado: 'abonada'|'pendiente'}`

### Estructura académica (admin)
- `GET /api/estructura/carreras` → `Carrera[]`
- `POST /api/estructura/carreras` `{codigo, nombre}`
- `PATCH /api/estructura/carreras/:id` `{nombre?, activa?}`
- `GET /api/estructura/cohortes` → `Cohorte[]`
- `POST /api/estructura/cohortes` `{nombre, anio_inicio, desde, hasta}`
- `PATCH /api/estructura/cohortes/:id`
- `GET /api/estructura/materias` → `Materia[]`
- `POST /api/estructura/materias` `{codigo, nombre}`
- `PATCH /api/estructura/materias/:id`

### Usuarios
- `GET /api/admin/usuarios?activo=` → `UsuarioResumen[]`
- `POST /api/admin/usuarios` `{nombre, apellido, email, roles, ...}`
- `PATCH /api/admin/usuarios/:id` `{activo?, ...}`

### Auditoría
- `GET /api/auditoria/panel?desde=&hasta=&materia=&usuario=` → `PanelAuditoria`
- `GET /api/auditoria/log?desde=&hasta=&materia=&usuario=&estado=` → `AuditLog[]`

## Tipos TypeScript clave

```typescript
// liquidaciones/types/index.ts
export interface Liquidacion {
  id: string
  docente: { id: string; nombre: string; apellido: string; rol: string }
  periodo: string  // 'YYYY-MM'
  salarioBase: number
  plus: number
  total: number
  esNexo: boolean
  excluidoPorFactura: boolean
  estado: 'abierta' | 'cerrada'
  creadaEn: string
}
export interface SalarioBase { id: string; rol: string; monto: number; desde: string; hasta: string | null }
export interface SalarioPlus { id: string; clave: string; rol: string; descripcion: string; monto: number; desde: string; hasta: string | null }
export interface Factura {
  id: string
  docenteId: string
  docenteNombre: string
  periodo: string
  detalle: string
  estado: 'pendiente' | 'abonada'
  archivoUrl: string | null
  cargadaEn: string
}

// admin/types/index.ts
export interface Carrera { id: string; codigo: string; nombre: string; activa: boolean }
export interface Cohorte { id: string; nombre: string; anioInicio: number; desde: string; hasta: string; activa: boolean }
export interface Materia { id: string; codigo: string; nombre: string; activa: boolean }
export interface UsuarioResumen {
  id: string; nombre: string; apellido: string; email: string
  roles: string[]; activo: boolean; modalidadCobro: 'factura' | 'liquidacion'
}
export interface PanelAuditoria {
  accionesPorDia: { fecha: string; total: number }[]
  estadoComunicaciones: { docenteId: string; nombre: string; pendiente: number; enviado: number; fallido: number }[]
  ultimasAcciones: AuditLogEntry[]
}
export interface AuditLogEntry {
  id: string; fecha: string; usuarioId: string; usuarioNombre: string
  accion: string; materia?: string; filasAfectadas: number; ip: string
}
```

## Decisiones de diseño

1. **Sin gráfico de terceros**: el gráfico de acciones por día se implementa como tabla con barras CSS (no se instala Chart.js ni similar — YAGNI, y evita deps innecesarias para el examen).
2. **Liquidaciones: estado local de período**: el filtro de período vive en `useState` + sync con search-params (igual que filtros de C-23).
3. **Factura upload**: multipart form via `FormData`; el hook usa `onUploadProgress` de Axios para mostrar progreso (igual que importación de calificaciones de C-22).
4. **Cierre de liquidación**: acción destructiva → botón con confirmación inline (no modal propio, se reutiliza un `window.confirm` o un estado local de "confirmar").
5. **Log de auditoría**: paginación simple (solo muestra los primeros N resultados configurables), sin virtual scroll — suficiente para el scope del proyecto.
