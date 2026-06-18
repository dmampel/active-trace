"""Tests unitarios para ComunicacionService (C-12, Tareas 8.2–8.11).

Usa SQLite in-memory con el mismo patrón del resto de los services tests.
El cipher AES-256 se instancia real (no mockeado) para validar cifrado/descifrado.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5433/activia_trace_test")
os.environ.setdefault("TEST_DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5433/activia_trace_test")
os.environ.setdefault("SECRET_KEY", "a" * 64)
os.environ.setdefault("ENCRYPTION_KEY", "b" * 64)

from app.models.base import Base
import app.models  # noqa: F401

from app.core.security import AES256GCMCipher, derive_encryption_key
from app.models.comunicacion import EstadoComunicacion
from app.models.tenant import Tenant
from app.repositories.comunicacion_repository import ComunicacionRepository
from app.schemas.comunicacion import (
    ComunicacionEnviarRequest,
    ComunicacionPreviewRequest,
)
from app.services.comunicacion_service import ComunicacionService


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
async def engine():
    e = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with e.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield e
    async with e.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await e.dispose()


@pytest.fixture
async def db(engine):
    async with AsyncSession(engine, expire_on_commit=False) as session:
        yield session


@pytest.fixture
def cipher() -> AES256GCMCipher:
    return AES256GCMCipher(derive_encryption_key("b" * 64))


@pytest.fixture
async def tenant(db) -> Tenant:
    t = Tenant(id=uuid.uuid4(), name="TenantTest")
    db.add(t)
    await db.commit()
    return t


@pytest.fixture
def svc(db, cipher) -> ComunicacionService:
    repo = ComunicacionRepository(db, cipher)
    return ComunicacionService(repo=repo, audit_log_repo=None)


# ── 8.2 preview resuelve variables ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_preview_resuelve_variables(svc):
    """preview con {{alumno.nombre}} → nombre real en respuesta."""
    req = ComunicacionPreviewRequest(
        asunto="Hola {{alumno.nombre}}",
        cuerpo="Tu legajo es {{alumno.legajo}}",
        contexto={"alumno.nombre": "Ana García", "alumno.legajo": "12345"},
    )
    resp = await svc.preview(req)

    assert resp.asunto_renderizado == "Hola Ana García"
    assert resp.cuerpo_renderizado == "Tu legajo es 12345"
    assert resp.warnings == []


# ── 8.3 preview warning por variable desconocida ──────────────────────────────


@pytest.mark.asyncio
async def test_preview_warnings_variable_desconocida(svc):
    """Variable {{foo.bar}} desconocida → se deja literal + entry en warnings."""
    req = ComunicacionPreviewRequest(
        asunto="Hola {{alumno.nombre}}",
        cuerpo="Valor: {{foo.bar}}",
        contexto={"alumno.nombre": "Ana"},
    )
    resp = await svc.preview(req)

    assert resp.asunto_renderizado == "Hola Ana"
    assert "{{foo.bar}}" in resp.cuerpo_renderizado  # literal preservado
    assert len(resp.warnings) == 1
    assert "foo.bar" in resp.warnings[0]


# ── 8.4 preview no persiste ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_preview_no_persiste(svc, db):
    """Llamar preview → verificar 0 registros en DB."""
    from sqlalchemy import select, func
    from app.models.comunicacion import Comunicacion

    req = ComunicacionPreviewRequest(
        asunto="Test",
        cuerpo="Cuerpo",
        contexto={},
    )
    await svc.preview(req)

    count_q = select(func.count(Comunicacion.id))
    result = await db.execute(count_q)
    assert result.scalar() == 0


# ── 8.5 encolar individual crea Pendiente ─────────────────────────────────────


@pytest.mark.asyncio
async def test_encolar_individual_crea_pendiente(svc, db, tenant, cipher):
    """Encolar 1 dest → 1 registro Pendiente, lote_id=None, destinatario cifrado."""
    from sqlalchemy import select
    from app.models.comunicacion import Comunicacion

    materia_id = uuid.uuid4()
    req = ComunicacionEnviarRequest(
        destinatarios=["alumno@test.com"],
        asunto="Test",
        cuerpo="Cuerpo",
        materia_id=materia_id,
    )
    resp = await svc.encolar(req, usuario_id=uuid.uuid4(), tenant_id=tenant.id)
    await db.commit()

    assert resp.total == 1
    assert resp.lote_id is None
    assert len(resp.ids_encolados) == 1

    # Verificar en DB
    com_q = select(Comunicacion).where(Comunicacion.id == resp.ids_encolados[0])
    result = await db.execute(com_q)
    com = result.scalar_one()

    assert com.estado == EstadoComunicacion.Pendiente
    assert com.lote_id is None
    # destinatario debe estar cifrado — no es texto plano
    assert com.destinatario != "alumno@test.com"
    # pero descifrable
    assert cipher.decrypt(com.destinatario) == "alumno@test.com"


# ── 8.6 encolar masivo mismo lote ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_encolar_masivo_mismo_lote(svc, db, tenant):
    """Encolar 3 dest → 3 registros con mismo lote_id."""
    from sqlalchemy import select
    from app.models.comunicacion import Comunicacion

    materia_id = uuid.uuid4()
    req = ComunicacionEnviarRequest(
        destinatarios=["a@t.com", "b@t.com", "c@t.com"],
        asunto="Masivo",
        cuerpo="Cuerpo",
        materia_id=materia_id,
    )
    resp = await svc.encolar(req, usuario_id=uuid.uuid4(), tenant_id=tenant.id)
    await db.commit()

    assert resp.total == 3
    assert resp.lote_id is not None
    assert len(resp.ids_encolados) == 3

    # Todos tienen el mismo lote_id
    coms_q = select(Comunicacion).where(Comunicacion.lote_id == resp.lote_id)
    result = await db.execute(coms_q)
    coms = result.scalars().all()
    assert len(coms) == 3
    for com in coms:
        assert com.lote_id == resp.lote_id


# ── 8.7 encolar sin destinatarios falla ───────────────────────────────────────


@pytest.mark.asyncio
async def test_encolar_sin_destinatarios_falla(svc, tenant):
    """Lista vacía → ValidationError."""
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        ComunicacionEnviarRequest(
            destinatarios=[],
            asunto="Test",
            cuerpo="Cuerpo",
            materia_id=uuid.uuid4(),
        )


# ── 8.8 aprobar lote actualiza aprobado_at ───────────────────────────────────


@pytest.mark.asyncio
async def test_aprobar_lote_actualiza_aprobado_at(svc, db, tenant):
    """Aprobar lote → todos los Pendiente del lote tienen aprobado_at IS NOT NULL."""
    from sqlalchemy import select
    from app.models.comunicacion import Comunicacion

    materia_id = uuid.uuid4()
    req = ComunicacionEnviarRequest(
        destinatarios=["a@t.com", "b@t.com"],
        asunto="Test",
        cuerpo="Cuerpo",
        materia_id=materia_id,
    )
    enq_resp = await svc.encolar(req, usuario_id=uuid.uuid4(), tenant_id=tenant.id)
    await db.commit()

    lote_id = enq_resp.lote_id
    aprobador_id = uuid.uuid4()
    accion_resp = await svc.aprobar_lote(lote_id, tenant.id, aprobador_id)
    await db.commit()

    assert accion_resp.afectados == 2

    coms_q = select(Comunicacion).where(Comunicacion.lote_id == lote_id)
    result = await db.execute(coms_q)
    coms = result.scalars().all()
    for com in coms:
        assert com.aprobado_at is not None


# ── 8.9 cancelar lote transiciona Cancelado ──────────────────────────────────


@pytest.mark.asyncio
async def test_cancelar_lote_transiciona_cancelado(svc, db, tenant):
    """Cancelar lote → todos Pendiente → Cancelado."""
    from sqlalchemy import select
    from app.models.comunicacion import Comunicacion

    req = ComunicacionEnviarRequest(
        destinatarios=["a@t.com", "b@t.com"],
        asunto="Test",
        cuerpo="Cuerpo",
        materia_id=uuid.uuid4(),
    )
    enq_resp = await svc.encolar(req, usuario_id=uuid.uuid4(), tenant_id=tenant.id)
    await db.commit()

    lote_id = enq_resp.lote_id
    accion_resp = await svc.cancelar_lote(lote_id, tenant.id, uuid.uuid4())
    await db.commit()

    assert accion_resp.afectados == 2
    assert accion_resp.estado_nuevo == EstadoComunicacion.Cancelado.value

    coms_q = select(Comunicacion).where(Comunicacion.lote_id == lote_id)
    result = await db.execute(coms_q)
    coms = result.scalars().all()
    for com in coms:
        assert com.estado == EstadoComunicacion.Cancelado


# ── 8.10 cancelar individual Pendiente → Cancelado ───────────────────────────


@pytest.mark.asyncio
async def test_cancelar_individual_pendiente_ok(svc, db, tenant):
    """Pendiente → Cancelado exitosamente."""
    req = ComunicacionEnviarRequest(
        destinatarios=["solo@t.com"],
        asunto="Test",
        cuerpo="Cuerpo",
        materia_id=uuid.uuid4(),
    )
    enq_resp = await svc.encolar(req, usuario_id=uuid.uuid4(), tenant_id=tenant.id)
    await db.commit()

    com_id = enq_resp.ids_encolados[0]
    resp = await svc.cancelar_individual(com_id, tenant.id, uuid.uuid4())
    await db.commit()

    assert resp.estado == EstadoComunicacion.Cancelado


# ── 8.11 cancelar individual Enviado falla con 422 ───────────────────────────


@pytest.mark.asyncio
async def test_cancelar_individual_enviado_falla(svc, db, tenant, cipher):
    """Intentar cancelar un mensaje Enviado → HTTPException 422."""
    from sqlalchemy import select, update
    from app.models.comunicacion import Comunicacion
    from fastapi import HTTPException

    # Encolar y luego simular que fue enviado
    req = ComunicacionEnviarRequest(
        destinatarios=["enviado@t.com"],
        asunto="Test",
        cuerpo="Cuerpo",
        materia_id=uuid.uuid4(),
    )
    enq_resp = await svc.encolar(req, usuario_id=uuid.uuid4(), tenant_id=tenant.id)
    await db.commit()

    com_id = enq_resp.ids_encolados[0]

    # Simular estado Enviado directamente en DB
    upd = (
        update(Comunicacion)
        .where(Comunicacion.id == com_id)
        .values(estado=EstadoComunicacion.Enviado, enviado_at=datetime.now(timezone.utc))
    )
    await db.execute(upd)
    await db.commit()

    with pytest.raises(HTTPException) as exc_info:
        await svc.cancelar_individual(com_id, tenant.id, uuid.uuid4())

    assert exc_info.value.status_code == 422
