## ADDED Requirements

### Requirement: Grilla salarial con vigencia temporal
El sistema SHALL mantener una grilla salarial compuesta por `SalarioBase` (importe fijo por rol) y `SalarioPlus` (incremento adicional por clave × rol), ambas con fechas de vigencia `desde`/`hasta`. Para calcular la liquidación de un período, el sistema MUST tomar los valores cuya vigencia contenga el período (RN-31, RN-32).

#### Scenario: Alta de salario base nuevo
- **WHEN** FINANZAS crea un `SalarioBase` para rol PROFESOR con `desde=2026-03-01` y `hasta=NULL`
- **THEN** el sistema persiste el registro y lo retorna con estado 201

#### Scenario: Solapamiento de vigencias rechazado
- **WHEN** FINANZAS intenta crear un `SalarioBase` para rol PROFESOR cuyo rango solapa con otro vigente para el mismo rol
- **THEN** el sistema retorna 409 con mensaje indicando el solapamiento

#### Scenario: Selección del salario vigente al período
- **WHEN** el sistema calcula la liquidación del período 2026-03
- **THEN** usa el `SalarioBase` cuyo `desde <= 2026-03-31` y (`hasta IS NULL` OR `hasta >= 2026-03-01`)

#### Scenario: Alta de Plus sin solapamiento
- **WHEN** FINANZAS crea un `SalarioPlus` para clave `"PROG"` y rol PROFESOR con vigencia 2026-01-01–NULL
- **THEN** el sistema persiste el registro y lo retorna con estado 201

---

### Requirement: Cálculo de liquidación por período
El sistema SHALL calcular la liquidación de honorarios para todos los docentes activos de una cohorte en un período dado. El cálculo MUST aplicar la fórmula `Total = Base(rol vigente) + Σ(Plus(clave_activa, rol))`, donde cada clave activa cuenta una sola vez (RN-33, RN-34). Docentes sin datos bancarios completos (CBU + banco) MUST ser excluidos y reportados en la respuesta.

#### Scenario: Cálculo con base y plus
- **WHEN** FINANZAS ejecuta `POST /liquidaciones/calcular` para cohorte X, período 2026-03
- **THEN** el sistema crea registros `Liquidacion` (estado Abierta) con `monto_base`, `monto_plus` y `total` correctos para cada docente activo con datos bancarios

#### Scenario: Clave Plus activa cuenta una sola vez
- **WHEN** un docente tiene 3 comisiones activas de instancias con `plus_key = "PROG"` en el período
- **THEN** su `monto_plus` incluye el Plus de `"PROG"` una sola vez (no multiplicado por 3)

#### Scenario: Docente con múltiples claves activas distintas
- **WHEN** un docente tiene comisiones activas en instancias con `plus_key = "PROG"` y `plus_key = "BD"`
- **THEN** su `monto_plus` suma el Plus de `"PROG"` + el Plus de `"BD"`

#### Scenario: Instancias sin plus_key no generan plus
- **WHEN** todas las comisiones activas de un docente tienen `plus_key = NULL`
- **THEN** su `monto_plus = 0` y `total = monto_base`

#### Scenario: Docente sin datos bancarios omitido
- **WHEN** un docente activo no tiene CBU registrado
- **THEN** no se genera `Liquidacion` para ese docente y aparece en la lista `omitidos` del response

#### Scenario: Recálculo posible mientras la liquidación está abierta
- **WHEN** FINANZAS ejecuta `POST /liquidaciones/calcular` para un período ya calculado con estado Abierta
- **THEN** el sistema actualiza los registros existentes con los valores actualizados

---

### Requirement: Cierre inmutable de liquidación
El sistema SHALL permitir cerrar una liquidación (cohorte × período), cambiando su estado a `Cerrada` e impidiendo cualquier modificación posterior (RN-22). El cierre MUST generar un evento de auditoría `LIQUIDACION_CERRAR` con el snapshot completo.

#### Scenario: Cierre exitoso
- **WHEN** FINANZAS ejecuta `POST /liquidaciones/{id}/cerrar` sobre una liquidación Abierta
- **THEN** el estado cambia a Cerrada, retorna 200 y se registra `LIQUIDACION_CERRAR` en el audit log

#### Scenario: Cierre rechazado si ya está cerrada
- **WHEN** FINANZAS intenta cerrar una liquidación ya en estado Cerrada
- **THEN** el sistema retorna 409 con mensaje "liquidacion ya cerrada"

#### Scenario: Recálculo bloqueado para período cerrado
- **WHEN** FINANZAS ejecuta `POST /liquidaciones/calcular` para un período cuya liquidación está Cerrada
- **THEN** el sistema retorna 409 indicando que el período está cerrado

---

### Requirement: Vista segmentada de liquidaciones con KPIs
El sistema SHALL exponer la vista de liquidaciones de un período (cohorte × mes) con tres segmentos diferenciados: docentes generales (PROFESOR, TUTOR, COORDINADOR sin factura), NEXO (por separado pero incluido en el total), y facturantes (excluidos del total de liquidación). MUST calcular KPIs `total_sin_factura` y `total_con_factura` (RN-36, RN-37, RN-38).

#### Scenario: Segmentación correcta en la vista
- **WHEN** FINANZAS consulta `GET /liquidaciones?cohorte_id=X&periodo=2026-03`
- **THEN** la respuesta incluye tres colecciones: `general`, `nexo`, `facturantes`, y KPIs `total_sin_factura` y `total_con_factura`

#### Scenario: NEXO suma al total general
- **WHEN** hay docentes con `es_nexo = true` en la liquidación
- **THEN** su importe aparece en la sección `nexo` Y está incluido en `total_sin_factura`

#### Scenario: Facturante no suma al total de liquidación
- **WHEN** hay docentes con `excluido_por_factura = true`
- **THEN** aparecen en la sección `facturantes` pero NO se incluyen en `total_sin_factura`; su suma aparece en `total_con_factura`

---

### Requirement: Historial de liquidaciones cerradas
El sistema SHALL permitir consultar el historial de liquidaciones cerradas de períodos anteriores para auditoría (F10.3).

#### Scenario: Consulta de historial
- **WHEN** FINANZAS consulta `GET /liquidaciones?estado=Cerrada&cohorte_id=X`
- **THEN** retorna todos los registros cerrados de esa cohorte, ordenados por período descendente

---

### Requirement: Gestión de facturas de docentes monotributistas
El sistema SHALL proveer ABM de facturas presentadas por docentes facturantes, con estados `Pendiente` y `Abonada`, filtros por docente / estado / rango de fechas, y la acción de marcar como abonada (F10.5, RN-35, RN-39).

#### Scenario: Carga de factura
- **WHEN** FINANZAS ejecuta `POST /facturas` con docente, período, detalle y referencia de archivo
- **THEN** se crea la factura con estado Pendiente y retorna 201

#### Scenario: Marcar factura como abonada
- **WHEN** FINANZAS ejecuta `PATCH /facturas/{id}` con `estado=Abonada`
- **THEN** la factura actualiza su estado a Abonada y registra la fecha de pago

#### Scenario: Filtro por docente y estado
- **WHEN** FINANZAS consulta `GET /facturas?usuario_id=X&estado=Pendiente`
- **THEN** retorna solo las facturas pendientes de ese docente

#### Scenario: Docente facturante excluido de liquidación general
- **WHEN** el sistema calcula la liquidación y un docente tiene `facturador = true`
- **THEN** ese docente NO aparece en los segmentos `general` o `nexo` de la liquidación

---

### Requirement: Control de acceso exclusivo para FINANZAS
El sistema SHALL proteger todos los endpoints de liquidaciones y facturas con guards `liquidaciones:ver`, `liquidaciones:calcular`, `liquidaciones:cerrar`, `liquidaciones:configurar-salarios`, `liquidaciones:exportar`. Roles sin estos permisos MUST recibir 403.

#### Scenario: FINANZAS puede calcular y cerrar
- **WHEN** un usuario con rol FINANZAS llama a `POST /liquidaciones/calcular`
- **THEN** el sistema procesa la solicitud sin error de autorización

#### Scenario: PROFESOR no puede acceder a liquidaciones
- **WHEN** un usuario con rol PROFESOR llama a `GET /liquidaciones`
- **THEN** el sistema retorna 403

#### Scenario: Multi-tenancy aplicado en liquidaciones
- **WHEN** FINANZAS del tenant A consulta `/liquidaciones`
- **THEN** solo recibe registros con `tenant_id` del tenant A
