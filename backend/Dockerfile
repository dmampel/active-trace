# ── Builder stage ──────────────────────────────────────────────────────────────
# Instala dependencias con uv (rápido, lock determinista) en un virtualenv.
# Se separa de la imagen final para que la runtime no incluya toolchain de build.
FROM python:3.13-slim AS builder

# uv: gestor de dependencias rápido (recomendado sobre pip para multi-stage)
RUN pip install --no-cache-dir uv==0.5.26

WORKDIR /app

# Copiar solo los manifests primero (aprovecha cache de Docker si no cambiaron)
COPY pyproject.toml ./

# Instalar dependencias en /app/.venv (sin las de dev)
RUN uv venv .venv && \
    uv pip install --python .venv/bin/python -e "." --no-cache

# ── Runtime stage ─────────────────────────────────────────────────────────────
# Imagen final mínima: solo el venv + código de app/
FROM python:3.13-slim AS runtime

WORKDIR /app

# Copiar el virtualenv con todas las deps ya instaladas
COPY --from=builder /app/.venv .venv

# Copiar el código de la aplicación y archivos de migraciones
COPY app/ app/
COPY alembic/ alembic/
COPY alembic.ini .

# Variable de entorno para que el venv sea el Python por defecto
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Puerto de la app (configurable en Easypanel)
EXPOSE 8000

# Comando por defecto: servidor ASGI de producción
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
