## Context

C-11 cierra el análisis de alumnos atrasados; el docente ya puede ver quiénes están en riesgo pero no puede notificarlos desde el sistema. C-12 agrega la capa de comunicación saliente: un modelo persistente de mensajes, una API de preview y encolado, y un worker asíncrono que los despacha por SMTP. El módulo opera sobre la infraestructura ya disponible (PostgreSQL, FastAPI async, Argon2/AES-256 para PII, audit log). ADR-003 (worker propio vs N8N) se resuelve aquí a favor del worker propio con asyncio.

**Constraints heredados:**
- Identidad y tenant exclusivamente desde el JWT (regla dura #8).
- `tenant_id` en cada tabla; repositories scoped por defecto (regla dura #9).
- RBAC `comunicacion:enviar` / `comunicacion:aprobar` (regla dura #10).
- Cifrado AES-256 sobre `destinatario` (regla dura #12).
- Soft delete / audit log (reglas duras #13, #5).

## Goals / Non-Goals

**Goals:**
- Modelo `Comunicacion` con máquina de estados completa (RN-15).
- Worker asíncrono que consume Pendiente → Enviando → Enviado/Error (ejecuta reintento simple en Error).
- Preview sin persistencia (RN-16): asunto + cuerpo renderizado con variables de sustitución.
- Envío individual y masivo con agrupación por `lote_id`.
- Aprobación/rechazo de lote o individual (RN-17) cuando `requiere_aprobacion=True` en tenant.
- Cancelación de mensajes en estado Pendiente.
- Audit `COMUNICACION_ENVIAR` en cada despacho confirmado.
- Resolución de ADR-003: worker propio asyncio.

**Non-Goals:**
- Mensajería interna entre usuarios (F3.4) — queda para C-15/C-20.
- Tablón de avisos (F3.5) — queda para C-15.
- Integración N8N para despacho — descartada por ADR-003.
- Reintentos con backoff exponencial — MVP: reintento único; se puede extender post-MVP.
- Plantillas persistibles en DB — MVP: plantillas inline con sustitución de variables; la gestión de plantillas guardadas es post-MVP.

## Decisions

### ADR-003: Worker propio asyncio vs N8N

**Decisión**: worker propio asyncio (loop de polling sobre DB).

**Rationale**: N8N agrega un servicio externo a operar, versionar y escalar; el volumen de mensajes en MVP no justifica esa complejidad. Un worker asyncio en el mismo proceso Docker, con polling periódico sobre la tabla `comunicacion`, mantiene la arquitectura simple, testeable y observable sin dependencias adicionales.

**Alternativa descartada**: N8N como orquestador externo. Se reincorporará si el volumen de mensajes exige tasas de despacho que un worker asyncio simple no pueda satisfacer.

---

### Modelo de datos: `Comunicacion` como registro histórico append-only

Cada mensaje es un registro independiente (no agregado mutable). El estado transiciona via UPDATE controlado desde el worker y la API. El `lote_id` agrupa mensajes disparados por la misma acción masiva; permite aprobar/cancelar el lote como unidad.

**Columna `destinatario` cifrada**: AES-256 usando el cipher ya implementado en `backend/app/core/cipher.py`. Nunca se expone el email en texto plano en logs ni en respuestas de API — se enmascara (`****@dominio.com`).

---

### Arquitectura del worker

```
┌─────────────────────────────────────────┐
│  FastAPI (API)                          │
│  POST /comunicaciones/preview           │  ← no persiste
│  POST /comunicaciones/enviar            │  ← persiste en estado Pendiente
│  POST /comunicaciones/lotes/{id}/aprobar│  ← Pendiente → aprobado (flag)
│  POST /comunicaciones/{id}/cancelar     │  ← Pendiente → Cancelado
│  GET  /comunicaciones                   │  ← listado con filtros
└────────────────┬────────────────────────┘
                 │  tabla comunicacion (PostgreSQL)
┌────────────────▼────────────────────────┐
│  Worker (asyncio loop, mismo pod)       │
│  - SELECT * WHERE estado=Pendiente AND  │
│    (requiere_aprobacion=False OR        │
│     aprobado_at IS NOT NULL)            │
│  - UPDATE estado=Enviando               │
│  - SMTP send                            │
│  - UPDATE estado=Enviado / Error        │
│  - Reintento único en Error             │
└─────────────────────────────────────────┘
```

El worker se arranca como tarea asyncio background (`asyncio.create_task`) al iniciar la app FastAPI, o como proceso separado vía `docker-compose`. En test se reemplaza por un stub que popula `estado=Enviado` directamente.

---

### Variables de sustitución en plantillas

Variables soportadas en asunto y cuerpo (resueltas en preview y en despacho):
- `{{alumno.nombre}}` — nombre completo del alumno destinatario
- `{{alumno.legajo}}` — número de legajo (atributo de negocio, no credencial)
- `{{materia.nombre}}` — nombre de la materia
- `{{instancia.periodo}}` — período del dictado (ej: "2025-2C")
- `{{lote.descripcion}}` — descripción opcional del lote

Resolución: el service `ComunicacionService` recibe el contexto de sustitución en `preview()` y en `encolar()`. Variables no reconocidas se dejan literales con flag de warning en el preview.

---

### Aprobación configurable por tenant

El flag `requiere_aprobacion: bool` vive en la tabla `tenant` (ya existente). Si `True`, los mensajes masivos (lote con >1 destinatario) quedan en `estado=Pendiente` hasta recibir `aprobado_at` vía el endpoint de aprobación. Mensajes individuales (`lote_id=NULL`) no requieren aprobación incluso si el flag está activo — esto permite al docente enviar un mensaje puntual sin fricción.

---

### Permisos nuevos

| Permiso | Roles que lo tienen por defecto |
|---------|--------------------------------|
| `comunicacion:enviar` | PROFESOR, COORDINADOR, ADMIN |
| `comunicacion:aprobar` | COORDINADOR, ADMIN |
| `comunicacion:ver` | PROFESOR (solo sus propios), COORDINADOR, ADMIN |

Los permisos se insertan como datos de seed en la migración de RBAC (tabla `permiso` ya existe desde C-04).

---

### Estructura de archivos nuevos

```
backend/app/
├── models/comunicacion.py          # Comunicacion SQLAlchemy model
├── schemas/comunicacion.py         # Pydantic v2 schemas (Request/Response)
├── repositories/comunicacion_repository.py
├── services/comunicacion_service.py
├── routers/comunicaciones.py
└── workers/
    └── comunicacion_worker.py      # asyncio loop de despacho
alembic/versions/0014_comunicacion.py
tests/
├── unit/services/test_comunicacion_service.py
├── unit/workers/test_comunicacion_worker.py
└── api/v1/routers/test_comunicaciones.py
```

## Risks / Trade-offs

- **[Risk] El worker hace polling, no push** → latencia de despacho proporcional al intervalo de polling (default 10s). Mitigation: configurable vía `WORKER_POLL_INTERVAL_SECONDS`; aceptable para MVP.
- **[Risk] Reintento único en Error** → un mensaje que falla dos veces queda en estado Error permanente. Mitigation: el docente puede ver el estado y reenviar manualmente (post-MVP: backoff exponencial).
- **[Risk] Cifrado del destinatario hace imposible buscar por email** → por diseño: nunca se necesita buscar `Comunicacion` por email del alumno, solo por materia/lote/estado. Mitigation: índices en `tenant_id + estado + lote_id`.
- **[Risk] Si la app cae mientras el worker está en estado Enviando** → el mensaje queda en Enviando indefinidamente. Mitigation: al arrancar, el worker resetea a Error todos los mensajes en estado Enviando con `enviado_at IS NULL` y `created_at < now() - 5min`.

## Migration Plan

1. Ejecutar `alembic upgrade head` — crea tabla `comunicacion`.
2. Insertar permisos `comunicacion:enviar`, `comunicacion:aprobar`, `comunicacion:ver` en seed.
3. Asignar permisos a roles (PROFESOR, COORDINADOR, ADMIN).
4. Arrancar worker (o verificar que está activo en compose).
5. Rollback: `alembic downgrade -1` — DROP TABLE comunicacion (ningún otro módulo depende de ella aún).

## Open Questions

- **OQ-C12-01**: ¿El tenant tiene `requiere_aprobacion` como columna en la tabla `tenant` existente, o vive en una tabla de configuración separada? → Asumo columna directa en `tenant` (booleano, default `False`). Si el modelo de configuración del tenant cambia, se adapta en C-03/C-04.
- **OQ-C12-02**: ¿El proveedor SMTP del MVP es un servicio externo real (SendGrid, SES) o simulado? → Para el worker de test se usa un stub; para producción se configura vía variables de entorno. La selección del proveedor real es decisión de infraestructura, no de código.
