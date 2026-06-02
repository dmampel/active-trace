# Skill Registry

Generated automatically during SDD Init.

## Project Standards (auto-resolved)

### General
- No automatic builds
- No unrequested commits
- No AI attribution in commits
- Strict TDD Mode: enabled
- AES-256 for PII
- Multi-tenant row-level security
- Soft-delete always

### Backend
- Python 3.13, FastAPI, SQLAlchemy 2.0 (async), Alembic, Pydantic v2
- snake_case for Python
- Pydantic schemas with extra='forbid'
- Max 500 LOC per file
- JWT auth + refresh rotation
- RBAC granular (modulo:accion)

### Frontend
- React 18, TypeScript, Vite, Tailwind CSS, TanStack Query
- PascalCase for React components
- Max 200 LOC per component

