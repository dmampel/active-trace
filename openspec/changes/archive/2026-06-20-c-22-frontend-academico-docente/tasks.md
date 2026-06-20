
## 1. Rutas y estructura de features

- [x] 1.1 Crear directorios de features: `frontend/src/features/importacion/`, `analisis/`, `comunicacion/` con subcarpetas `components/`, `hooks/`, `services/`, `types/`, `pages/`
- [x] 1.2 Registrar las rutas protegidas en el router existente: `/comision/:comisionId/importar`, `/comision/:comisionId/analisis`, `/comision/:comisionId/comunicacion`, `/comision/:comisionId/monitor`
- [x] 1.3 Crear tipos TypeScript compartidos para `Comision`, `Alumno`, `Actividad`, `Umbral`, `MensajeEstado` en `features/*/types/`

## 2. Feature: importación de calificaciones (F1.1)

- [x] 2.1 Escribir tests para `ImportarCalificacionesPage`: estado vacío, progreso de upload, avance entre pasos
- [x] 2.2 Implementar `useImportarCalificaciones` hook (mutación multipart con `onUploadProgress` via Axios)
- [x] 2.3 Implementar `ImportarCalificacionesPage` con wizard 4-pasos (upload → preview actividades → umbral → confirmar)
- [x] 2.4 Implementar `SeleccionActividadesStep`: lista de checkboxes con checkbox maestro; deshabilitar "Continuar" si ninguna seleccionada
- [x] 2.5 Implementar `UmbralStep`: input numérico con validación 1–100, default 60
- [x] 2.6 Implementar `ConfirmarImportacionStep`: resumen + botón confirmar que dispara la mutación e invalida cache
- [x] 2.7 Implementar `ConfirmarSalidaWizard`: bloquear navegación con diálogo de confirmación en pasos 2–4
- [x] 2.8 Manejar error HTTP 413 en el hook de upload con mensaje de error en UI

## 3. Feature: reporte de finalización y export (F1.2, F2.6)

- [x] 3.1 Escribir tests para `TablaFinalizacion`: upload, tabla de resultados, estado vacío, botón export deshabilitado
- [x] 3.2 Implementar `useFinalizacionActividades` hook (upload del reporte de finalización)
- [x] 3.3 Implementar `TablaFinalizacion` componente: columnas alumno, actividad, estado; estado vacío "No se detectaron entregas sin corregir"
- [x] 3.4 Implementar botón "Exportar CSV" deshabilitado cuando la tabla está vacía; descarga CSV al hacer clic

## 4. Feature: vaciar datos de comisión (F1.5)

- [x] 4.1 Escribir test para `VaciarDatosButton`: diálogo de confirmación, cancelar no envía request, confirmar envía y limpia cache
- [x] 4.2 Implementar `useVaciarComision` hook (DELETE con invalidación de cache al éxito)
- [x] 4.3 Implementar `VaciarDatosButton` componente con diálogo de confirmación destructivo

## 5. Feature: análisis académico (F2.1–F2.5)

- [x] 5.1 Escribir tests para `AnalisisPage`: estado vacío con CTA, tabs activas con datos, cabecera con umbral
- [x] 5.2 Implementar `AnalisisPage` con tabs (Atrasados / Ranking / Reportes / Notas finales) y estado vacío con CTA al wizard
- [x] 5.3 Escribir tests para `TablaAtrasados`: filtro texto, orden por columna, estado vacío "Todos al día"
- [x] 5.4 Implementar `TablaAtrasados`: columnas nombre/correo/actividades faltantes/nota; búsqueda libre y ordenamiento por columna
- [x] 5.5 Escribir tests para `TablaRanking`: orden descendente por aprobadas, toggle de columna
- [x] 5.6 Implementar `TablaRanking`: excluye alumnos con cero aprobadas, ordenamiento interactivo
- [x] 5.7 Escribir tests para `PanelReportes`: 4 tarjetas de métricas, recalculo tras cambio de umbral
- [x] 5.8 Implementar `PanelReportes`: tarjetas total alumnos, % al día, actividades incluidas, promedio general
- [x] 5.9 Escribir tests para `TablaNotasFinales`: un registro por alumno, descarga CSV
- [x] 5.10 Implementar `TablaNotasFinales` con botón "Exportar CSV"
- [x] 5.11 Implementar editor de umbral inline en cabecera de análisis (solo con permiso `calificaciones:importar`); invalida cache al guardar

## 6. Feature: monitor de seguimiento docente (F2.8)

- [x] 6.1 Escribir tests para `MonitorDocentePage`: lista scoped al usuario, filtros individuales, múltiples filtros simultáneos, limpiar filtros
- [x] 6.2 Implementar `useMonitorDocente` hook (query con params de filtro; identidad extraída del `AuthContext`, no de la URL)
- [x] 6.3 Implementar `MonitorDocentePage` con filtros: alumno (nombre/correo), comisión, regional, actividad, mínimo cumplido
- [x] 6.4 Implementar botón "Limpiar filtros" que resetea todos los controles de filtro

## 7. Feature: comunicación a atrasados (F3.1, F3.2)

- [x] 7.1 Escribir tests para `ComunicacionPage`: checkbox maestro, botón preview deshabilitado sin selección, modal preview, envío exitoso navega a tracking
- [x] 7.2 Implementar `ComunicacionPage` con tabla de atrasados seleccionables y checkbox de cabecera
- [x] 7.3 Implementar `PreviewComunicacionModal`: muestra asunto + cuerpo interpolado del primer destinatario; cerrar no envía
- [x] 7.4 Implementar `useEnviarComunicacion` hook (mutación POST al endpoint de cola)
- [x] 7.5 Manejar error 4xx/5xx en el modal de envío: mantener modal abierto y mostrar mensaje de error
- [x] 7.6 Escribir tests para `TablaTracking`: polling activo con mensajes en tránsito, polling detenido en estado final, badges por estado, estado vacío
- [x] 7.7 Implementar `TablaTracking`: columnas destinatario, estado (badge coloreado), timestamp; `refetchInterval: 3000` mientras haya Pendiente/Enviando
- [x] 7.8 Implementar lógica de detención del polling: `refetchInterval` condicional a `false` cuando todos están en estado final

## 8. Integración y navegación

- [x] 8.1 Agregar link de navegación a las rutas de comisión en el sidebar/layout del shell (C-21) para roles PROFESOR y TUTOR
- [x] 8.2 Verificar que el guard de rutas bloquea acceso a `/importar` sin permiso `calificaciones:importar` y muestra 403

## 9. Cierre

- [x] 9.1 Ejecutar suite completa de tests frontend: `cd frontend && npm test` — todos los tests deben pasar
- [x] 9.2 Verificar typecheck sin errores: `npm run typecheck`
- [ ] 9.3 Archivar el change: `/opsx:archive c-22-frontend-academico-docente`
