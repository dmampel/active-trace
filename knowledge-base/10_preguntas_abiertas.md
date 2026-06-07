# 10 — Preguntas Abiertas y Decisiones de Producto Pendientes

> **Propósito**: registrar las decisiones de diseño de producto que aún no están cerradas, ordenadas por impacto sobre el modelo de dominio. Cada ítem es una pregunta genuina que el equipo de producto debe resolver antes de (o durante) la implementación. Las decisiones ya cerradas aparecen en los archivos correspondientes de la KB y en [`docs/ARQUITECTURA.md`](../docs/ARQUITECTURA.md); no se repiten acá. Este archivo es un tablero vivo: cuando una pregunta se cierra, se documenta la resolución en el archivo temático correspondiente y se retira de acá.

---

## Prioridad ALTA — bloqueantes para el modelo de dominio

~~### PA-01 — ¿Cómo se organiza el catálogo de materias y cuál es la fuente de verdad?~~ **CERRADA**

**Resolución** (2026-06-07): el sistema usa **dos entidades separadas**:
- `Materia` — catálogo del plan de estudios (código corto, ej.: `PROG_I`). Fuente de verdad curricular.
- `InstanciaDictado` — oferta concreta de una materia en una cohorte y período (ej.: "Programación – Python" en MAR-2026). Las calificaciones, padrón y encuentros se asocian a la instancia, no a la materia directamente.

Documentado en [04_modelo_de_datos.md](04_modelo_de_datos.md) E3 y E3b.

---

~~### PA-07 — ¿Las cohortes pertenecen a una carrera o son transversales?~~ **CERRADA**

**Resolución** (2026-06-07): una cohorte pertenece a **exactamente una carrera** (`Cohorte.carrera_id` NOT NULL). No hay cohortes transversales. Un alumno puede estar en distintas cohortes si cursa materias de carreras diferentes.

Documentado en [04_modelo_de_datos.md](04_modelo_de_datos.md) E2.

---

### PA-22 — ¿Cuántas claves de Plus existen y cómo se mapean a materias?

El modelo de liquidación define un **Plus** por combinación `(clave, rol)`, donde la clave agrupa familias de materias (ej.: `PROG` para materias de Programación). Ver [RN-31](05_reglas_de_negocio.md#rn-31) a [RN-38](05_reglas_de_negocio.md#rn-38).

**Preguntas abiertas**:

- ¿Cuáles son todas las claves de Plus que existen en el dominio (ej.: `PROG`, `BD`, `ING`, `MAT`, etc.)?
- ¿Qué materia cae en qué clave? ¿Hay materias sin clave asignada?
- ¿Ese mapeo es configurable por tenant o está fijo para toda la plataforma?
- ¿Lo define el ADMIN del tenant o viene preconfigurado desde la institución?

---

### PA-23 — ¿Cómo se calcula el Plus cuando un docente tiene N comisiones de la misma clave?

Si un PROFESOR tiene tres comisiones de materias que caen bajo la clave `PROG`:

**Preguntas abiertas**:

- ¿Se acumula `3 × Plus(PROG, PROFESOR)` o se aplica una sola vez sin importar la cantidad de comisiones?
- ¿Existe un tope de acumulación?
- ¿La lógica cambia según el rol (TUTOR vs. PROFESOR vs. COORDINADOR)?

**Impacto**: es la regla de negocio central del módulo de liquidaciones. Sin ella no se puede implementar el cálculo.

---

### PA-25 — ¿Cuál es la semántica precisa del rol NEXO?

El rol NEXO existe en el dominio, tiene tratamiento contable propio y aparece en el catálogo de roles, pero su función operativa no está completamente especificada.

**Preguntas abiertas**:

- ¿Un NEXO está asociado a una regional, a un programa, a un grupo de docentes, o a un grupo de alumnos?
- ¿Tiene acceso a datos de alumnos? ¿A qué granularidad?
- ¿Puede asignar o reasignar docentes a comisiones?
- ¿Su función es principalmente de enlace administrativo o también pedagógico?
- ¿Un usuario puede ser NEXO y COORDINADOR al mismo tiempo?

**Impacto**: define qué permisos incluir en el rol NEXO dentro de la matriz de autorización ([03_actores_y_roles.md](03_actores_y_roles.md)).

---

## Prioridad MEDIA — refinamiento del modelo

### PA-05 — ¿Cómo y desde dónde se crea una guardia?

El módulo de guardias muestra el listado de guardias registradas por docente, pero el flujo de creación no está especificado.

**Preguntas abiertas**:

- ¿Las guardias se crean desde el módulo de encuentros, desde un formulario dedicado, o ambos?
- ¿Quién puede crear una guardia: solo el docente que la cubre, o también el COORDINADOR en su nombre?
- ¿Requiere aprobación posterior?

---

### PA-08 — ¿Cuál es el ciclo de vida de una Tarea?

El módulo de tareas tiene un filtro de estado, pero los valores posibles del ciclo de vida no están definidos.

**Preguntas abiertas**:

- ¿Cuáles son los estados posibles de una tarea? (ej.: `abierta → en progreso → completada → archivada`)
- ¿Las transiciones son libres o tienen reglas (ej.: solo el creador puede cerrarla)?
- ¿Hay notificaciones automáticas al cambiar de estado?

---

### PA-09 — ¿Qué permite la funcionalidad de comunicación por grupos en el módulo de equipos?

Dentro del módulo de equipos docentes existe una funcionalidad de comunicación grupal cuyo alcance no está especificado.

**Preguntas abiertas**:

- ¿Es para enviar mensajes masivos al equipo docente de una comisión?
- ¿O es comunicación entre pares (docentes entre sí)?
- ¿Requiere aprobación previa como las comunicaciones hacia alumnos?

---

### PA-11 — ¿Qué es el "criterio de clasificación" en el monitor general?

El monitor general permite configurar un criterio de clasificación mediante un modal.

**Preguntas abiertas**:

- ¿Qué criterios se pueden configurar? (ej.: por porcentaje de avance, por cantidad de entregas, por calificación promedio)
- ¿La configuración es personal (por usuario) o global (por tenant)?
- ¿Afecta qué alumnos se consideran "atrasados" o es solo una vista?

---

### PA-12 — ¿Qué incluye la vista administrativa de encuentros?

El módulo de encuentros tiene una vista con permisos ampliados respecto a la vista docente estándar.

**Preguntas abiertas**:

- ¿Permite ver y editar los encuentros de todos los docentes de una comisión o de todo el tenant?
- ¿Permite crear encuentros en nombre de otro docente?
- ¿Tiene capacidad de aprobación o solo de consulta?

---

### PA-13 — ¿Qué es el contexto de agrupación de tareas?

El módulo de tareas permite filtrar por un contexto de agrupación cuya semántica no está definida.

**Preguntas abiertas**:

- ¿El contexto de agrupación es una cohorte, una materia, un equipo docente, o algún otro concepto?
- ¿Una tarea puede pertenecer a más de un contexto?

---

### PA-14 — ¿Cómo reserva un alumno una instancia de coloquio?

El sistema muestra reservas activas y cupos disponibles para instancias de evaluación, pero el flujo de reserva del alumno no está especificado.

**Preguntas abiertas**:

- ¿El alumno reserva desde dentro del sistema o desde un canal externo (ej.: Moodle, link público)?
- ¿Hay restricciones para reservar (ej.: cantidad máxima de intentos, estado de regularidad requerido)?
- ¿El alumno puede cancelar su reserva?

---

### PA-15 — ¿El módulo de corrección automática está integrado con las calificaciones?

El sistema contempla la posibilidad de integrar un módulo de corrección automática de actividades.

**Preguntas abiertas**:

- ¿Las calificaciones generadas por el corrector automático se importan al sistema directamente o requieren revisión y aprobación docente?
- ¿El corrector opera sobre entregas ya subidas al sistema o sobre entregas del LMS (Moodle)?
- ¿Cómo se audita una calificación generada automáticamente vs. una ingresada manualmente?

---

### PA-24 — ¿Las facturas se asocian a comisiones o son globales por docente?

En el módulo de facturas existe un campo de detalle con texto libre, pero no está claro si hay una asociación formal con el trabajo realizado.

**Preguntas abiertas**:

- ¿Una factura debe vincularse a una comisión específica, a un período, o puede ser un concepto genérico?
- ¿Cómo se concilia la factura con el cálculo de liquidación?
- ¿El sistema valida que el monto de la factura no supere el total liquidado?

---

## Prioridad BAJA — pulido y definición de detalles

### PA-16 — ¿Cuáles son los niveles de severidad de los avisos y qué efecto tienen?

**Preguntas abiertas**:

- ¿Los valores de severidad son un enumerado fijo (`info`, `advertencia`, `error`) o es configurable?
- ¿La severidad afecta el comportamiento del sistema (ej.: un aviso de error bloquea al alumno hasta que lo confirme)?
- ¿Hay notificaciones adicionales disparadas por severidad?

---

### PA-17 — ¿El tipo de facturación del docente afecta el cálculo de liquidación?

Algunos docentes pueden emitir comprobantes fiscales (ej.: monotributistas), lo cual puede tener implicancias en el cálculo.

**Preguntas abiertas**:

- ¿El tipo de facturación modifica algún concepto del cálculo (ej.: agrega retenciones, modifica la base)?
- ¿O es solo un atributo informativo para el módulo de FINANZAS sin impacto en la fórmula?

---

### PA-18 — ¿El CUIL del docente se calcula automáticamente o se carga manualmente?

**Preguntas abiertas**:

- ¿El sistema calcula el CUIL a partir del DNI aplicando la regla estándar (`prefijo-DNI-dígito verificador`)?
- ¿O el CUIL es un campo de carga manual sin validación automática?
- Si se calcula, ¿qué pasa cuando el CUIL real difiere del calculado (ej.: personas con CUIL de tipo empresa)?

---

### PA-19 — ¿Qué pasa con las asignaciones vigentes cuando se desactiva un docente?

**Preguntas abiertas**:

- ¿Las asignaciones vigentes se cierran automáticamente (se les pone fecha de fin) al desactivar el usuario?
- ¿O quedan en estado inconsistente hasta que el ADMIN las gestione manualmente?
- ¿El sistema emite una alerta al COORDINADOR cuando uno de sus docentes es desactivado?

---

## Decisiones ya cerradas (referencia)

Las siguientes preguntas que existían en versiones anteriores de este documento ya fueron resueltas y su resolución está documentada en los archivos correspondientes:

| Código original | Resolución | Dónde está documentado |
|-----------------|-----------|------------------------|
| PA-02 | El rol TUTOR existe formalmente en el catálogo; ver descripción de capacidades | [03_actores_y_roles.md](03_actores_y_roles.md) |
| PA-04 | Login por email + contraseña; 2FA opcional (TOTP); recuperación por token de un solo uso; alta solo administrativa en MVP | [07_flujos_principales.md](07_flujos_principales.md), [`docs/ARQUITECTURA.md` §5.1](../docs/ARQUITECTURA.md) |
| PA-06 | Fórmula de liquidación: Base (por rol) + Plus (por clave × rol); ver RN-31 a RN-38 | [05_reglas_de_negocio.md](05_reglas_de_negocio.md) |
| PA-21 | Impersonación via parámetro de petición: eliminada. La impersonación legítima requiere permiso explícito, sesión diferenciada y auditoría completa | [03_actores_y_roles.md §4](03_actores_y_roles.md), [`docs/ARQUITECTURA.md`](../docs/ARQUITECTURA.md) |

---

## Cómo cerrar estas preguntas

Para resolver las preguntas pendientes se recomienda:

1. **Una sesión de trabajo con el responsable de producto** — cubre las preguntas de dominio (PA-01, PA-22, PA-23, PA-25 son prioritarias).
2. **Revisión del modelo de datos con el equipo técnico** — para validar las entidades y relaciones de [04_modelo_de_datos.md](04_modelo_de_datos.md).
3. **Sesión de refinamiento con FINANZAS** — para cerrar PA-17, PA-18, PA-24 que afectan el módulo de liquidaciones.
4. **Cuando se cierre una pregunta**: documentar la resolución en el archivo temático correspondiente y moverla a la tabla de "Decisiones ya cerradas" de este archivo.
