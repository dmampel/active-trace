## Context

El sistema tiene usuarios, roles, estructura académica y equipos docentes (C-01→C-08). El siguiente paso del camino crítico es incorporar alumnos reales a través del padrón. La KB define dos fuentes de ingesta: archivos xlsx/csv exportados del LMS (F1.3, F1.4) y la API de Moodle Web Services. El modelo de datos (E6) especifica `VersionPadron` + `EntradaPadron` con versionado explícito.

El padrón es prerrequisito bloqueante para C-10 (calificaciones) y todo lo que sigue del camino crítico.

## Goals / Non-Goals

**Goals:**
- Modelos SQLAlchemy `VersionPadron` / `EntradaPadron` con migración Alembic
- Repositorio con scope tenant y activación atómica de versión (desactiva la anterior en la misma transacción)
- Servicio de importación desde archivo: parse xlsx con openpyxl, csv con stdlib; detección automática de formato
- Cliente Moodle WS async (`httpx`) que obtiene participantes y genera una `VersionPadron` equivalente
- Config Moodle por tenant: URL + token almacenados cifrados (AES-256) en tabla `tenant_moodle_config`
- Endpoints REST con RBAC: importar, listar versiones, ver entradas, vaciar (scope-isolated, RN-04)
- Tests con DB real: fixtures de xlsx/csv en `tests/fixtures/padron/`

**Non-Goals:**
- Calificaciones (C-10), análisis de atrasados (C-11), comunicaciones (C-12)
- Sincronización bidireccional con Moodle (solo lectura en esta iteración)
- Job asíncrono para archivos grandes (el padrón típico son ~200 alumnos; sync es suficiente)
- UI (C-22/C-23)

## Decisions

### D1 — Versionado: VersionPadron como contenedor explícito

`VersionPadron` es el contenedor (materia × cohorte × cargado_por × timestamp). `EntradaPadron` son sus filas. Al importar un nuevo padrón se crea una versión nueva y se desactiva la anterior en la misma transacción. La columna `activa` (boolean) en `VersionPadron` indica la versión vigente.

**Alternativa considerada**: soft-delete de entradas directamente → descartada porque pierde el historial de quién importó qué y cuándo. El versionado explícito cumple la KB (E6) y facilita auditoría.

### D2 — Email de EntradaPadron: cifrado AES-256 via security module

`EntradaPadron.email` es PII según la KB (E6). Se cifra con el módulo `security.py` existente (AES-256-GCM), igual que email en `Usuario`. El repositorio descifra al leer si el caller tiene el permiso adecuado.

**Alternativa**: almacenar en plano → rechazada por regla dura #12 de CLAUDE.md.

### D3 — Config Moodle por tenant: tabla dedicada `tenant_moodle_config`

Nueva tabla `tenant_moodle_config` (FK → Tenant, columnas `moodle_url` y `moodle_token` cifradas con AES-256). El `MoodleWSClient` recibe la config ya descifrada.

**Alternativa**: variables de entorno globales → descartada; el sistema es multi-tenant y cada institución tiene su propia instancia de Moodle.

### D4 — Importación síncrona en el request

Los padrones típicos son ≤500 filas. Se procesa en el request con streaming de openpyxl (read_only=True). Si supera 5.000 filas se responde 413 con mensaje claro.

**Alternativa**: worker asíncrono → overkill para este volumen; C-12 ya cubre la cola de trabajos pesados. Se puede migrar fácilmente si el cliente escala.

### D5 — Vaciar (F1.5): soft-delete de la versión activa, no de las entradas

La operación "vaciar" soft-deletes la `VersionPadron` activa del (usuario, materia). Las `EntradaPadron` quedan físicamente pero ya no son visibles (se accede siempre via la versión). Esto cumple RN-04 (scope-isolated) y la regla dura de no hard-delete.

### D6 — Estructura de directorio consistente con el resto del backend

```
backend/app/
  models/padron.py
  repositories/padron_repository.py
  services/padron_service.py
  schemas/padron.py
  api/v1/padron.py          ← router
  integrations/moodle_ws.py
  integrations/__init__.py  (ya existe, vacío)
```
Migración: `alembic/versions/<ts>_add_padron_tables.py`

## Risks / Trade-offs

- **Archivos malformados**: openpyxl puede levantar excepciones no descriptivas. Mitigación: catch en el servicio, mapear a `400 Bad Request` con mensaje legible.
- **Token Moodle expirado/revocado**: el WS client recibirá 403 de Moodle. Mitigación: propagar como `503 Service Unavailable` con retry hint.
- **Email duplicado en el padrón**: un mismo alumno puede aparecer en múltiples versiones. No es un error — cada `EntradaPadron` es independiente. El cruce con `Usuario` es opcional en esta versión.
- **Columnas inesperadas en xlsx**: el parser es tolerante — ignora columnas que no reconoce. Solo falla si faltan las columnas obligatorias (nombre, apellidos, email).

## Migration Plan

1. `alembic revision --autogenerate -m "add padron tables"` → revisar y ajustar manualmente (indices, constraints).
2. `alembic upgrade head` en test DB antes de correr suite.
3. Rollback: `alembic downgrade -1` — tablas nuevas, sin datos que migrar, reversión limpia.

## Open Questions

- ¿El endpoint de import Moodle WS recibe el `course_id` de Moodle como parámetro del request o está configurado en `tenant_moodle_config`? → Asumo parámetro del request (un tenant puede tener múltiples cursos). Si el equipo prefiere config fija, se ajusta en C-10 sin afectar modelo.
