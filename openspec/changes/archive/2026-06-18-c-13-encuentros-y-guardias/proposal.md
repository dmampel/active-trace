## Why

La plataforma carece de trazabilidad sobre los encuentros sincrónicos (clases virtuales) y las guardias de atención a alumnos. Sin este módulo no hay supervisión de coordinación sobre qué encuentros se realizaron, ni posibilidad de generar el calendario para el aula virtual del LMS. Las guardias cubiertas por tutores tampoco quedan registradas, imposibilitando auditoría y liquidación futura.

## What Changes

- **Nuevo modelo `SlotEncuentro`**: plantilla recurrente que define día, horario, frecuencia semanal y cantidad de semanas de una serie de encuentros.
- **Nuevo modelo `InstanciaEncuentro`**: encuentro concreto derivado de un slot (o creado de forma independiente). Soporta estado `Programado | Realizado | Cancelado`, `meet_url`, `video_url` y `comentario`.
- **Nuevo modelo `Guardia`**: registro de una guardia de atención cubierta por un tutor, con materia, carrera/cohorte, día, rango horario y estado.
- **Creación recurrente (F6.1, RN-13)**: al crear un slot con `cant_semanas > 0`, el sistema genera automáticamente todas las instancias de la serie.
- **Creación de encuentro único (F6.2)**: slot con `fecha_unica` → genera exactamente 1 instancia.
- **Edición de instancia (F6.3)**: estado, `meet_url`, `video_url`, `comentario` editables por instancia sin afectar al slot ni a otras instancias (RN-14).
- **Bloque HTML para LMS (F6.4)**: endpoint que retorna HTML formateado con el calendario de encuentros y sus grabaciones, listo para embeber en el aula virtual.
- **Vista admin de encuentros (F6.5)**: endpoint transversal de todos los encuentros del tenant para supervisión por COORDINADOR/ADMIN.
- **Registro y consulta de guardias (F6.6)**: TUTOR registra sus guardias propias; COORDINADOR/ADMIN consulta global con filtros y exporta a CSV.
- **Migración `013_slot_encuentro_instancia_guardia`**: tablas `slot_encuentro`, `instancia_encuentro`, `guardia`.
- **Endpoints**: `GET/POST /api/encuentros/slots`, `GET/PATCH /api/encuentros/instancias/{id}`, `GET /api/encuentros/admin`, `GET /api/encuentros/html-block`, `GET/POST /api/guardias`, `GET /api/guardias/export`.

## Capabilities

### New Capabilities
- `encuentros-y-guardias`: gestión de encuentros sincrónicos (slots recurrentes e instancias) y registro de guardias de tutores, con supervisión transversal y exportación para el LMS.

### Modified Capabilities
<!-- ninguna spec existente cambia de requisitos -->

## Impact

- **Backend**: nuevos modelos, schemas Pydantic, repositories, services y routers. Migración Alembic `013`.
- **Dependencias**: `C-07` (usuarios y asignaciones) — los slots y guardias referencian `Asignacion`.
- **Sin impacto en frontend**: este change cubre solo el backend; la UI se implementa en `C-23 frontend-coordinacion`.
- **Permisos nuevos**: `encuentros:gestionar` (PROFESOR, COORDINADOR, ADMIN) y `guardias:registrar` (TUTOR) / `guardias:consultar` (COORDINADOR, ADMIN).
