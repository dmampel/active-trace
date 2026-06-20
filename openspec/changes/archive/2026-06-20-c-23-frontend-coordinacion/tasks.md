## 1. Rutas y estructura de features

- [x] 1.1 Crear directorios de features: `frontend/src/features/equipos/`, `avisos/`, `tareas/`, `coordinacion/` con subcarpetas `components/`, `hooks/`, `services/`, `types/`, `pages/`
- [x] 1.2 Registrar rutas protegidas en `AppRouter.tsx` con lazy-load: `/equipos`, `/equipos/masiva`, `/equipos/clonar`, `/avisos`, `/avisos/nuevo`, `/avisos/:id/editar`, `/avisos/:id/confirmaciones`, `/tareas`, `/coordinacion/tareas`, `/coordinacion/monitores`, `/coordinacion/monitores/seguimiento`, `/coordinacion/encuentros`, `/coordinacion/coloquios`, `/coordinacion/coloquios/:convocatoriaId`, `/coordinacion/comunicaciones/aprobacion`
- [x] 1.3 Crear tipos TypeScript compartidos: `Asignacion`, `Equipo`, `Aviso`, `Tarea`, `ComentarioTarea`, `Encuentro`, `Guardia`, `Convocatoria`, `ReservaColoquio` en `features/*/types/`

## 2. Feature: mis equipos y asignaciones (F4.2–F4.3)

- [x] 2.1 Escribir tests para `EquiposPage`: estado vacío, tabs (resumen / actividad / comunicaciones), filtros por estado/materia/rol, cambio de tab lazy-load
- [x] 2.2 Implementar `useEquiposDocente` hook (query scoped al usuario autenticado vía JWT; identidad NUNCA desde URL)
- [x] 2.3 Implementar `EquiposPage` con tabs de mis asignaciones, monitoreo y comunicaciones del equipo
- [x] 2.4 Implementar `useAsignacionesTenant` hook (query con params de filtro sincronizados con search-params URL)
- [x] 2.5 Implementar `AsignacionesAdminPage` (tabla con filtros por materia/carrera/cohorte/rol/docente, paginación)
- [x] 2.6 Escribir tests para `AsignacionesAdminPage`: filtros individuales, múltiples filtros simultáneos, limpiar filtros

## 3. Feature: alta masiva y operaciones de equipo (F4.4–F4.7)

- [x] 3.1 Escribir tests para `AsignacionMasivaPage`: validación campos obligatorios, selección múltiple de docentes, error 400 muestra detalle por fila
- [x] 3.2 Implementar `useAsignacionMasiva` hook (mutación POST que retorna array de resultados por docente)
- [x] 3.3 Implementar `AsignacionMasivaPage`: selector múltiple de docentes, campos materia/carrera/cohorte/rol/vigencia, tabla de resultados post-envío
- [x] 3.4 Escribir tests para `ClonarEquipoPage`: stepper 3 pasos, validación selección origen, error 409 en paso 3 mantiene origen
- [x] 3.5 Implementar `useClonarEquipo` hook (mutación POST con manejo explícito de 409)
- [x] 3.6 Implementar `ClonarEquipoPage` con stepper (selección origen → selección destino → confirmación + resumen)
- [x] 3.7 Implementar `useModificarVigenciaEquipo` hook + formulario inline de modificación de vigencia con validación fecha-hasta ≥ fecha-desde
- [x] 3.8 Implementar botón "Exportar equipo" en `AsignacionesAdminPage`: descarga CSV con filtros activos aplicados

## 4. Feature: avisos del sistema (F3.5, FL-09)

- [x] 4.1 Escribir tests para `AvisosPage`: lista de avisos activos, aviso fuera de vigencia no aparece, botón nuevo aviso
- [x] 4.2 Implementar `useAvisos` hook (query con parámetros de estado/vigencia)
- [x] 4.3 Implementar `AvisosPage`: tabla de avisos con columnas título/alcance/severidad/vigencia/estado, acciones editar/desactivar
- [x] 4.4 Escribir tests para `NuevoAvisoPage` / `EditarAvisoPage`: scope "materia" muestra selector materia, scope "cohorte" muestra ambos selectores, validación Zod condicional
- [x] 4.5 Implementar schema Zod para aviso con `.superRefine()` para validación condicional según scope
- [x] 4.6 Implementar `NuevoAvisoPage` con React Hook Form + Zod: campos scope/roles/severidad/título/cuerpo/vigencia/orden/require_ack
- [x] 4.7 Implementar `EditarAvisoPage` reutilizando el mismo formulario con datos precargados
- [x] 4.8 Escribir tests para `ConfirmacionesAvisoPage`: lista de usuarios que confirmaron, aviso sin ack redirige
- [x] 4.9 Implementar `ConfirmacionesAvisoPage`: lista de confirmaciones con usuario y fecha/hora; estado vacío si nadie confirmó aún

## 5. Feature: workflow de tareas (F8.1–F8.3, FL-05)

- [x] 5.1 Escribir tests para `MisTareasPage`: lista ordenada por estado/fecha, agregar comentario, cambiar estado
- [x] 5.2 Implementar `useMisTareas` hook (query scoped al usuario autenticado, identidad desde JWT)
- [x] 5.3 Implementar `MisTareasPage`: lista de tareas asignadas con hilo de comentarios expandible por tarea
- [x] 5.4 Implementar `useAgregarComentario` hook (mutación POST que invalida cache de la tarea)
- [x] 5.5 Implementar `useCambiarEstadoTarea` hook (mutación PATCH con optimistic update)
- [x] 5.6 Escribir tests para `AdminTareasPage`: filtros por estado/docente/materia, cambio de estado, agregar observación
- [x] 5.7 Implementar `useAdminTareas` hook (query con filtros sincronizados con search-params URL)
- [x] 5.8 Implementar `AdminTareasPage` (COORDINADOR): tabla con filtros, acciones cambio de estado + comentario en línea

## 6. Feature: monitores transversales (F2.7, F2.9)

- [x] 6.1 Escribir tests para `MonitorGeneralPage`: filtros materia/regional/comisión/estado, exportar, limpiar filtros
- [x] 6.2 Implementar `useMonitorGeneral` hook (query con filtros; paginación; identidad del tenant desde JWT)
- [x] 6.3 Implementar `MonitorGeneralPage`: tabla de alumnos del tenant con filtros y botón exportar CSV
- [x] 6.4 Escribir tests para `MonitorSeguimientoPage`: hereda filtros de F2.8, filtro de rango de fechas opcional
- [x] 6.5 Implementar `MonitorSeguimientoPage` extendiendo el monitor estándar con pickers de fecha inicio/fin

## 7. Feature: encuentros y guardias admin (F6.5–F6.6)

- [x] 7.1 Escribir tests para `EncuentrosAdminPage`: lista todos los encuentros del tenant, filtros materia/docente/estado
- [x] 7.2 Implementar `useEncuentrosAdmin` hook (query tenant-wide con filtros)
- [x] 7.3 Implementar `EncuentrosAdminPage`: tabla con columnas materia/docente/fecha/estado/grabación; filtros
- [x] 7.4 Escribir tests para sección guardias: tabla de guardias, filtros, botón exportar
- [x] 7.5 Implementar sección de guardias dentro de `EncuentrosAdminPage` (tab o sección inferior): tabla + export CSV

## 8. Feature: coloquios (F7.1–F7.5)

- [x] 8.1 Escribir tests para `ColoquiosPage`: KPIs de cabecera, lista de convocatorias con métricas, crear convocatoria
- [x] 8.2 Implementar `useColoquiosMetricas` hook (query de métricas globales)
- [x] 8.3 Implementar `ColoquiosPage`: panel KPIs + tabla de convocatorias activas con métricas por fila
- [x] 8.4 Implementar `useCrearConvocatoria` hook + formulario modal: materia, instancia, días/cupos
- [x] 8.5 Escribir tests para `ColoquioDetallePage`: tabs (Agenda / Reservas / Registro académico), importar padrón, estado vacío de notas
- [x] 8.6 Implementar `useImportarPadronColoquio` hook (mutación multipart)
- [x] 8.7 Implementar `ColoquioDetallePage` con tabs: agenda de reservas activas, importar padrón, registro académico de notas

## 9. Feature: aprobación de comunicaciones (F3.3)

- [x] 9.1 Escribir tests para `AprobacionComunicacionesPage`: lista mensajes pendientes, aprobar lote, cancelar individual, estado vacío sin polling
- [x] 9.2 Implementar `useAprobacionComunicaciones` hook (query con `refetchInterval: 5000` condicional a mensajes pendientes)
- [x] 9.3 Implementar `AprobacionComunicacionesPage`: tabla con asunto/destinatario/emisor; acciones aprobar individual, cancelar individual, aprobar todo el lote
- [x] 9.4 Implementar lógica de detención del polling cuando no hay mensajes pendientes

## 10. Integración y navegación

- [x] 10.1 Agregar entradas de navegación para los roles COORDINADOR y ADMIN en el sidebar del shell (C-21)
- [x] 10.2 Verificar guards de rutas: acceso sin permiso muestra 403 manejado por el guard existente

## 11. Cierre

- [x] 11.1 Ejecutar suite completa de tests frontend: `cd frontend && npm test` — todos los tests deben pasar
- [x] 11.2 Verificar typecheck sin errores: `npm run typecheck`
- [x] 11.3 Archivar el change: `/opsx:archive c-23-frontend-coordinacion`
