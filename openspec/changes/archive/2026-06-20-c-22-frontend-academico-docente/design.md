## Context

El shell SPA (C-21) está operativo: React 18 + Vite 5 + TypeScript + Tailwind 3 + TanStack Query + Axios con interceptor JWT. Las rutas protegidas, el `AuthContext`, el `QueryClient` global y el layout principal ya existen.

El backend expone los endpoints de calificaciones (C-10), análisis de atrasados (C-11) y cola de comunicaciones (C-12). C-22 es exclusivamente frontend: consume esas APIs y construye las pantallas para PROFESOR y TUTOR.

## Goals / Non-Goals

**Goals:**
- Wizard completo de importación de calificaciones (upload → preview → selección → umbral → confirmación).
- Detección y export de TPs sin corregir.
- Vistas de análisis: atrasados, ranking, reportes rápidos, notas finales.
- Monitor de seguimiento docente/tutor (F2.8).
- Flujo de comunicación: preview de mensaje → envío → tracking de estado con polling automático.
- Tests de componente e integración con mocks de API para todos los flujos principales.

**Non-Goals:**
- Monitor general de coordinación (F2.7 / F2.9) → C-23.
- Aprobación de comunicaciones (F3.3) → C-23.
- Cualquier cambio en backend, modelos o migraciones.
- Soporte mobile-first / PWA.

## Decisions

### D1 — Estructura de features

Las nuevas features siguen el patrón feature-based ya establecido en C-21:

```
frontend/src/features/
├── importacion/          ← F1.1, F1.2, F1.5
│   ├── components/
│   ├── hooks/
│   ├── services/
│   ├── types/
│   └── pages/
├── analisis/             ← F2.1–F2.6, F2.8
│   ├── components/
│   ├── hooks/
│   ├── services/
│   ├── types/
│   └── pages/
└── comunicacion/         ← F3.1, F3.2
    ├── components/
    ├── hooks/
    ├── services/
    ├── types/
    └── pages/
```

**Alternativa descartada**: módulo único `academico/` con sub-carpetas. Se descartó porque mezcla responsabilidades muy distintas (upload de archivos vs. análisis vs. mensajería) que evolucionarán a ritmos diferentes.

### D2 — Rutas bajo `/comision/:comisionId`

Todas las páginas académicas se anidan bajo `/comision/:comisionId/` en el router existente. El `comisionId` se resuelve desde los params de React Router y se propaga a los hooks vía contexto o parámetro explícito.

```
/comision/:comisionId/importar          → ImportarCalificacionesPage
/comision/:comisionId/analisis          → AnalisisPage (tabs: atrasados / ranking / reportes / notas)
/comision/:comisionId/comunicacion      → ComunicacionPage
/comision/:comisionId/monitor           → MonitorDocentePage
```

### D3 — Upload multipart con Axios + progreso

El wizard de importación usa `FormData` + `Content-Type: multipart/form-data` via el cliente Axios centralizado. El progreso del upload se expone con `onUploadProgress` de Axios y se muestra como barra de progreso en el wizard. No se usan librerías de upload adicionales.

### D4 — Tracking en tiempo real via polling con TanStack Query

El estado de la cola de comunicaciones se actualiza via `refetchInterval` de TanStack Query (cada 3 s mientras haya mensajes en estado Pendiente o Enviando). Cuando todos los mensajes llegan a estado final (OK / Fallido / Cancelado), el polling se detiene automáticamente con `refetchIntervalInBackground: false` y una condición sobre los datos.

**Alternativa descartada**: WebSockets. Se descartó porque la cola de mensajes ya existe en el backend como modelo REST y el volumen de mensajes por sesión no justifica la complejidad operativa de WebSockets.

### D5 — Wizard de importación como estado local (no servidor)

Los pasos del wizard (upload → preview actividades → selección → umbral → confirmación) viven en estado local React (`useState` / `useReducer`). Solo el paso de confirmación dispara una mutación al backend. El preview de actividades se obtiene de la respuesta al upload (endpoint que parsea el archivo sin persistir).

### D6 — Preview de comunicación como modal

La previsualización del mensaje (F3.1) se implementa como modal que renderiza el asunto y cuerpo interpolado del primer destinatario seleccionado. No abre una nueva ruta; es un componente `PreviewComunicacionModal` montado sobre la página de comunicación.

## Risks / Trade-offs

- **[Risk] Tamaño de archivos LMS grandes** → El backend ya limita el tamaño; el frontend muestra error del 413 como mensaje de usuario. Mitigation: manejar el error HTTP en el hook de upload y mostrar feedback claro.
- **[Risk] Polling agresivo bajo red lenta** → `refetchInterval: 3000` puede acumular requests si el usuario tiene latencia alta. Mitigation: usar `staleTime` generoso y cancelar el intervalo en unmount (TanStack Query lo hace automáticamente).
- **[Risk] Estado de wizard perdido al navegar** → Si el usuario navega fuera del wizard a mitad de proceso, el estado local se pierde. Mitigation: confirmar salida con un `beforeunload` / `Prompt` de React Router si hay datos no confirmados.

## Migration Plan

No hay migración de datos ni backend. El deploy es incremental: las nuevas rutas se agregan al router existente; si un usuario no tiene el permiso `calificaciones:importar`, la ruta le muestra un 403 gestionado por el guard ya existente (C-21).
