## ADDED Requirements

### Requirement: Acceso restringido por permiso auditoria:ver
El sistema SHALL exponer todos los endpoints de auditoría bajo el guard `auditoria:ver` con política fail-closed: sin el permiso explícito en los permisos efectivos del usuario, la respuesta SHALL ser 403. El permiso `auditoria:ver` SHALL estar asignado a los roles ADMIN, COORDINADOR y FINANZAS. La identidad, los roles y el `tenant_id` del usuario SHALL derivarse siempre del JWT verificado, nunca de la URL, el body o headers.

#### Scenario: Usuario sin permiso recibe 403
- **WHEN** un usuario sin `auditoria:ver` (por ejemplo un PROFESOR) invoca cualquier endpoint `/api/v1/auditoria/*`
- **THEN** el sistema responde 403 sin devolver datos de auditoría

#### Scenario: Usuario con permiso accede
- **WHEN** un usuario con `auditoria:ver` invoca un endpoint de auditoría
- **THEN** el sistema responde 200 con los datos scopeados a su tenant y a su scope de rol

#### Scenario: Identidad tomada de la sesión, no de la petición
- **WHEN** la petición incluye un `tenant_id` o `usuario_id` en query/body distinto al del JWT
- **THEN** el sistema ignora ese valor y resuelve el scope con el `tenant_id` e identidad del JWT

### Requirement: Aislamiento multi-tenant en toda lectura de auditoría
Todas las consultas de auditoría SHALL filtrar por el `tenant_id` de la sesión. Ningún registro de `AuditLog`, `Comunicacion` ni agregación de otro tenant SHALL ser visible.

#### Scenario: No se filtran registros de otro tenant
- **WHEN** existen registros de auditoría del tenant A y del tenant B, y un ADMIN del tenant A consulta cualquier endpoint
- **THEN** el resultado contiene únicamente registros del tenant A

### Requirement: Scope (propio) del COORDINADOR
Un usuario cuyo rol de acceso es COORDINADOR (y no ADMIN) SHALL ver únicamente auditoría de las materias que coordina, determinadas por sus asignaciones COORDINADOR vigentes. ADMIN y FINANZAS SHALL ver toda la auditoría del tenant. El scope SHALL aplicarse en todos los endpoints: log completo, acciones por día, estado de comunicaciones, interacciones por docente×materia y log de últimas acciones.

#### Scenario: Coordinador ve solo sus materias
- **WHEN** un COORDINADOR (no ADMIN) con asignación vigente sobre la materia M1 consulta el log completo sin filtro de materia
- **THEN** el resultado incluye registros de M1 y excluye registros de materias que no coordina

#### Scenario: Coordinador sin materias coordinadas no ve registros con materia
- **WHEN** un COORDINADOR sin asignaciones COORDINADOR vigentes consulta endpoints scopeados por materia
- **THEN** el resultado no incluye registros asociados a materias ajenas

#### Scenario: ADMIN ve todo el tenant
- **WHEN** un ADMIN consulta el log completo sin filtro de materia
- **THEN** el resultado incluye registros de todas las materias del tenant

#### Scenario: Coordinador que filtra por una materia ajena no obtiene datos
- **WHEN** un COORDINADOR filtra explícitamente por una materia que no coordina
- **THEN** el resultado es vacío (el filtro nunca amplía su scope)

### Requirement: Log completo de auditoría con filtros
El sistema SHALL exponer un endpoint de lectura del log completo de `AuditLog` que devuelve los campos registrados por cada acción: fecha y hora, identificador de usuario (actor), materia, código de acción, cantidad de registros afectados, IP de origen y agente de usuario. El endpoint SHALL aceptar filtros opcionales por rango de fechas (desde/hasta), materia, usuario y código de acción (estado), combinables. Los resultados SHALL ordenarse por fecha y hora descendente y SHALL ser paginados.

#### Scenario: Filtro por rango de fechas
- **WHEN** se consulta el log con `fecha_desde` y `fecha_hasta`
- **THEN** el resultado contiene solo registros con `fecha_hora` dentro del rango inclusivo

#### Scenario: Filtro por materia y usuario combinados
- **WHEN** se consulta el log con `materia_id` y `usuario_id`
- **THEN** el resultado contiene solo registros de ese usuario sobre esa materia

#### Scenario: Filtro por código de acción
- **WHEN** se consulta el log con un código de acción (estado)
- **THEN** el resultado contiene solo registros cuyo `accion` coincide

#### Scenario: Sin filtros devuelve todo el scope paginado
- **WHEN** se consulta el log sin filtros
- **THEN** el resultado devuelve los registros del scope del usuario, ordenados por fecha descendente y paginados

### Requirement: Acciones por día
El sistema SHALL exponer una agregación de cantidad de registros de auditoría agrupados por día (fecha de `fecha_hora`), opcionalmente filtrable por rango de fechas y respetando el scope del usuario. Cada punto de la serie SHALL incluir la fecha y el conteo de acciones.

#### Scenario: Conteo por día
- **WHEN** existen 3 acciones el 2026-06-01 y 2 acciones el 2026-06-02 dentro del scope
- **THEN** la serie devuelve `{2026-06-01: 3, 2026-06-02: 2}`

#### Scenario: Días sin actividad no aparecen o aparecen en cero
- **WHEN** no hubo acciones un día dentro del rango
- **THEN** ese día no aporta un conteo positivo a la serie

### Requirement: Estado de comunicaciones por docente
El sistema SHALL exponer una agregación del estado de las comunicaciones (Pendiente, Enviando, Enviado, Error, Cancelado) agrupado por docente que las envió, respetando el scope del usuario y el aislamiento de tenant.

#### Scenario: Distribución de estados por docente
- **WHEN** el docente D1 tiene 2 comunicaciones Enviado y 1 Error
- **THEN** la agregación para D1 reporta `{Enviado: 2, Error: 1}`

#### Scenario: Solo docentes dentro del scope
- **WHEN** un COORDINADOR consulta el estado de comunicaciones
- **THEN** solo aparecen comunicaciones de las materias que coordina

### Requirement: Interacciones por docente y materia
El sistema SHALL exponer una agregación del conteo de acciones de auditoría agrupado por usuario (docente) y materia, desglosado por código de acción, respetando el scope del usuario.

#### Scenario: Conteo por docente, materia y acción
- **WHEN** el docente D1 ejecutó 5 acciones `CALIFICACIONES_IMPORTAR` sobre la materia M1
- **THEN** la agregación reporta para (D1, M1) un conteo de 5 para `CALIFICACIONES_IMPORTAR`

### Requirement: Log de últimas acciones con límite configurable
El sistema SHALL exponer el listado de las acciones más recientes ordenadas por fecha y hora descendente, con un límite configurable. El límite por defecto SHALL ser 200. El sistema SHALL aplicar un tope máximo: cualquier límite solicitado mayor al máximo configurado SHALL recortarse al máximo. Un límite no positivo SHALL caer al valor por defecto.

#### Scenario: Límite por defecto
- **WHEN** se consulta el log de últimas acciones sin especificar límite
- **THEN** el sistema devuelve a lo sumo 200 registros, los más recientes primero

#### Scenario: Límite personalizado respetado
- **WHEN** se consulta con un límite de 50 dentro del tope máximo
- **THEN** el sistema devuelve a lo sumo 50 registros, los más recientes primero

#### Scenario: Límite por encima del tope se recorta
- **WHEN** se consulta con un límite mayor al máximo configurado
- **THEN** el sistema devuelve a lo sumo el máximo configurado de registros

#### Scenario: Orden descendente por fecha
- **WHEN** se consulta el log de últimas acciones
- **THEN** el primer registro es el de `fecha_hora` más reciente del scope

### Requirement: Auditoría es solo lectura en este módulo
Ningún endpoint de auditoría SHALL crear, modificar ni eliminar registros de `AuditLog`. El acto de consultar el panel de auditoría no SHALL escribir un nuevo registro de auditoría (las lecturas no se auto-auditan en este módulo).

#### Scenario: Consultar el panel no altera el log
- **WHEN** un usuario consulta cualquier endpoint de auditoría
- **THEN** la cantidad de registros en `AuditLog` permanece igual antes y después de la consulta
