## Why

El shell SPA (C-21) está operativo con autenticación funcional, pero el PROFESOR no tiene ninguna pantalla para trabajar: no puede importar calificaciones, analizar atrasados ni enviar comunicaciones. C-22 construye el módulo académico-docente completo sobre el shell existente, consumiendo los endpoints de backend ya construidos en C-10, C-11 y C-12.

## What Changes

- **Wizard de importación de calificaciones** (F1.1): subir archivo LMS, preview de actividades detectadas, selección de actividades a incluir, configuración de umbral.
- **Importación de reporte de finalización** (F1.2): detectar trabajos sin corregir; tabla exportable.
- **Vaciar datos de comisión** (F1.5): acción destructiva con confirmación.
- **Configuración de umbral de aprobación** (F2.1): input persistido por materia, default 60%.
- **Vista de alumnos atrasados** (F2.2): tabla filtrable con columnas de alumno, actividades faltantes y nota.
- **Ranking de actividades aprobadas** (F2.3): tabla ordenada por cant. de actividades aprobadas.
- **Reportes rápidos** (F2.4): panel de métricas clave de la comisión; estado vacío cuando no hay datos.
- **Notas finales agrupadas** (F2.5): tabla con nota final por alumno, exportable.
- **Exportar TPs sin corregir** (F2.6): descarga desde la tabla de finalización.
- **Monitor de seguimiento del docente/tutor** (F2.8): vista filtrable de alumnos asignados al usuario; filtros por alumno, correo, comisión, regional, actividad y mínimo cumplido.
- **Preview de comunicación** (F3.1): modal con asunto y cuerpo personalizado antes del envío.
- **Envío y tracking en tiempo real** (F3.2): cola de estados Pendiente → Enviando → OK/Fallido/Cancelado, con polling/refresh automático.

## Capabilities

### New Capabilities

- `importacion-academica-ui`: Wizard de importación de calificaciones y finalización de actividades (F1.1, F1.2, F1.5) — frontend completo incluyendo upload, preview de actividades, selección y confirmación.
- `analisis-academico-ui`: Vistas de análisis post-importación: umbral (F2.1), tabla de atrasados (F2.2), ranking (F2.3), reportes rápidos (F2.4), notas finales (F2.5), TPs sin corregir (F2.6), monitor docente/tutor (F2.8).
- `comunicacion-saliente-ui`: Flujo de comunicación a atrasados: preview de mensaje (F3.1), envío masivo y tracking de estado en tiempo real (F3.2).

### Modified Capabilities

_(ninguna — este change no altera requerimientos existentes de backend)_

## Impact

- **Frontend** (`frontend/src/features/`): nuevas features `importacion/`, `analisis/`, `comunicacion/` con componentes, hooks, services y páginas.
- **Rutas protegidas**: nuevas rutas bajo `/comision/:comisionId/` en el shell de C-21.
- **APIs consumidas**: `POST /api/calificaciones/import`, `GET /api/analisis/atrasados`, `GET /api/analisis/ranking`, `GET /api/comunicaciones/`, `POST /api/comunicaciones/enviar` (todas ya existentes desde C-10/C-11/C-12).
- **No hay cambios en backend, modelos ni migraciones**.
- **Dependencias**: C-21 (shell + auth), C-12 (cola de comunicaciones), C-10/C-11 (endpoints de calificaciones y análisis).
