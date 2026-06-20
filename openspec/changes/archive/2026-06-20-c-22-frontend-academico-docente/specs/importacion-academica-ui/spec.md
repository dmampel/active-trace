## ADDED Requirements

### Requirement: Wizard de importación de calificaciones en 4 pasos
El sistema SHALL proveer un wizard en `/comision/:comisionId/importar` que guíe al PROFESOR a través de los pasos: (1) subir archivo, (2) preview y selección de actividades, (3) configurar umbral, (4) confirmar. El wizard SHALL ser accesible solo para usuarios con permiso `calificaciones:importar`. Cada paso SHALL mostrar el número de paso actual y el total.

#### Scenario: Acceso sin permiso redirige a 403
- **WHEN** un usuario sin permiso `calificaciones:importar` navega a `/comision/:comisionId/importar`
- **THEN** el sistema muestra la pantalla de error 403 sin renderizar el wizard

#### Scenario: Paso 1 — subir archivo válido avanza al paso 2
- **WHEN** el usuario selecciona un archivo de hoja de cálculo válido y hace clic en "Continuar"
- **THEN** el sistema sube el archivo al endpoint de preview, muestra un indicador de progreso durante el upload y avanza al paso 2 al recibir la respuesta exitosa

#### Scenario: Paso 1 — archivo demasiado grande muestra error
- **WHEN** el backend responde con HTTP 413
- **THEN** el wizard permanece en el paso 1 y muestra el mensaje "El archivo supera el tamaño máximo permitido"

#### Scenario: Paso 2 — lista de actividades detectadas se muestra con checkboxes
- **WHEN** el paso 2 se renderiza con la respuesta del backend
- **THEN** cada actividad detectada aparece como fila con un checkbox, nombre y tipo; todas las actividades están seleccionadas por defecto

#### Scenario: Paso 2 — deseleccionar todas bloquea el botón Continuar
- **WHEN** el usuario deselecciona todas las actividades
- **THEN** el botón "Continuar" queda deshabilitado y muestra el tooltip "Seleccioná al menos una actividad"

#### Scenario: Paso 3 — umbral por defecto es 60
- **WHEN** el paso 3 se renderiza por primera vez para una comisión sin umbral previo
- **THEN** el campo de umbral muestra el valor 60 pre-completado

#### Scenario: Paso 3 — umbral fuera de rango 1-100 bloquea avance
- **WHEN** el usuario ingresa un valor menor a 1 o mayor a 100
- **THEN** el campo muestra error de validación y el botón "Continuar" queda deshabilitado

#### Scenario: Paso 4 — confirmar dispara la mutación y navega a análisis
- **WHEN** el usuario hace clic en "Confirmar importación" en el paso 4
- **THEN** el sistema envía las actividades seleccionadas y el umbral al backend; al recibir 200, navega a `/comision/:comisionId/analisis` e invalida el cache de TanStack Query para la comisión

#### Scenario: Navegar fuera del wizard con datos cargados pide confirmación
- **WHEN** el usuario intentó salir del wizard estando en el paso 2, 3 o 4
- **THEN** aparece un diálogo de confirmación preguntando si desea abandonar; si cancela, permanece en el wizard

### Requirement: Importar reporte de finalización de actividades
El sistema SHALL proveer, en la página de análisis, una sección para subir el reporte de finalización de actividades del LMS. El upload SHALL disparar la detección de entregas potencialmente sin corregir y mostrar la tabla resultante.

#### Scenario: Upload de reporte muestra tabla de TPs sin corregir
- **WHEN** el usuario sube un archivo de finalización válido
- **THEN** la tabla "Posibles entregas sin corregir" se renderiza con columnas alumno, actividad y estado del LMS

#### Scenario: Tabla vacía muestra estado informativo
- **WHEN** el backend devuelve lista vacía de TPs sin corregir
- **THEN** se muestra el mensaje "No se detectaron entregas sin corregir" en lugar de una tabla vacía

### Requirement: Vaciar datos de una comisión
El sistema SHALL proveer un botón "Vaciar datos de la comisión" en la página de análisis, accesible solo con permiso `calificaciones:importar`. La acción SHALL requerir confirmación explícita del usuario antes de ejecutarse.

#### Scenario: Vaciar datos sin confirmación no ejecuta la acción
- **WHEN** el usuario hace clic en "Vaciar datos" pero cancela el diálogo de confirmación
- **THEN** no se envía ningún request al backend

#### Scenario: Vaciar datos confirmado limpia el estado de la comisión
- **WHEN** el usuario confirma el vaciado
- **THEN** el sistema envía la request de vaciado; al recibir 200, invalida el cache de la comisión y muestra el estado vacío de la página de análisis
