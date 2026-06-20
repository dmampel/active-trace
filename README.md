# active-trace

Plataforma de gestión académica y trazabilidad multi-tenant. Opera como capa de orquestación sobre Moodle: consolida calificaciones, detecta atrasos, gestiona comunicación saliente con aprobación, equipos docentes, encuentros, coloquios, liquidaciones de honorarios y auditoría completa. Cada institución es un tenant aislado.

---

## Requisitos

- **Docker** y **Docker Compose**
- Para desarrollo del frontend por separado: **Node.js 20+**

---

## Levantar el proyecto

```bash
docker-compose up --build -d
```

| Servicio | URL |
|----------|-----|
| Frontend | http://localhost:5173 |
| Backend API / Swagger | http://localhost:8000/docs |

---

## Aplicar migraciones

```bash
docker-compose exec api alembic upgrade head
```

---

## Seed de datos de prueba

Carga un tenant completo con usuarios de todos los roles, estructura académica, alumnos, calificaciones, comunicaciones, encuentros, evaluaciones, avisos, tareas, liquidaciones y mensajería.

```bash
docker-compose exec api python scripts/seed.py
```

### Credenciales (contraseña: `trace1234`)

| Rol | Email |
|-----|-------|
| ADMIN | admin@trace.utn.edu.ar |
| COORDINADOR | coordinador@trace.utn.edu.ar |
| NEXO | nexo@trace.utn.edu.ar |
| PROFESOR | profesor@trace.utn.edu.ar |
| TUTOR | tutor@trace.utn.edu.ar |
| FINANZAS | finanzas@trace.utn.edu.ar |
| ALUMNO | alumno@trace.utn.edu.ar |

> En desarrollo, el login muestra estos usuarios como acceso rápido (botones + autocompletado en el campo email).

---

## Desarrollo del frontend (HMR)

```bash
docker-compose up postgres api redis -d
cd frontend
npm install
npm run dev
```

---

## Tests

```bash
# Frontend
cd frontend && npm test

# Backend
docker-compose exec api pytest
```

---

## Documentación

- Stack y arquitectura: [`docs/ARQUITECTURA.md`](./docs/ARQUITECTURA.md)
- Dominio y reglas de negocio: [`knowledge-base/`](./knowledge-base/)
- Plan de implementación: [`CHANGES.md`](./CHANGES.md)
