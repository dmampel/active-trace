"""Tests unitarios para la máquina de estados y el worker de comunicaciones (C-12, Tareas 9.1–9.8).

9.1–9.4: Tests de validar_transicion (máquina de estados pura).
9.5–9.8: Tests de integración del worker con SQLite in-memory.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select, update

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5433/activia_trace_test")
os.environ.setdefault("TEST_DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5433/activia_trace_test")
os.environ.setdefault("SECRET_KEY", "a" * 64)
os.environ.setdefault("ENCRYPTION_KEY", "b" * 64)

from app.models.base import Base
import app.models  # noqa: F401

from app.core.security import AES256GCMCipher, derive_encryption_key
from app.models.comunicacion import Comunicacion, EstadoComunicacion, validar_transicion
from app.models.tenant import Tenant
from app.repositories.comunicacion_repository import ComunicacionRepository


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
    t = Tenant(id=uuid.uuid4(), name="TenantWorker")
    db.add(t)
    await db.commit()
    return t


@pytest.fixture
def repo(db, cipher) -> ComunicacionRepository:
    return ComunicacionRepository(db, cipher)


# ── 9.1 Transición Pendiente → Enviando válida ────────────────────────────────


def test_transicion_pendiente_enviando_valida():
    """Pendiente → Enviando es válida."""
    validar_transicion(EstadoComunicacion.Pendiente, EstadoComunicacion.Enviando)  # no lanza


# ── 9.2 Transición Enviando → Enviado válida ─────────────────────────────────


def test_transicion_enviando_enviado_valida():
    """Enviando → Enviado es válida."""
    validar_transicion(EstadoComunicacion.Enviando, EstadoComunicacion.Enviado)  # no lanza


# ── 9.3 Transición Enviando → Error válida ───────────────────────────────────


def test_transicion_enviando_error_valida():
    """Enviando → Error es válida."""
    validar_transicion(EstadoComunicacion.Enviando, EstadoComunicacion.Error)  # no lanza


# ── 9.4 Transición inversa rechazada ────────────────────────────────────────


def test_transicion_inversa_rechazada():
    """Enviado → Pendiente es inválida → ValueError."""
    with pytest.raises(ValueError, match="inválida"):
        validar_transicion(EstadoComunicacion.Enviado, EstadoComunicacion.Pendiente)


def test_transicion_cancelado_a_pendiente_rechazada():
    """Cancelado → Pendiente es inválida → ValueError."""
    with pytest.raises(ValueError):
        validar_transicion(EstadoComunicacion.Cancelado, EstadoComunicacion.Pendiente)


# ── Helpers para crear comunicaciones en tests del worker ─────────────────────


async def _crear_comunicacion(
    db,
    repo,
    tenant,
    *,
    estado: EstadoComunicacion = EstadoComunicacion.Pendiente,
    aprobado_at: datetime | None = None,
    created_at: datetime | None = None,
) -> Comunicacion:
    com = await repo.create(
        tenant_id=tenant.id,
        enviado_por=uuid.uuid4(),
        materia_id=uuid.uuid4(),
        destinatario_plain="test@example.com",
        asunto="Test",
        cuerpo="Cuerpo",
    )
    await db.commit()

    # Aplicar overrides de estado/campos si los hay
    updates: dict = {}
    if estado != EstadoComunicacion.Pendiente:
        updates["estado"] = estado
    if aprobado_at is not None:
        updates["aprobado_at"] = aprobado_at
    if created_at is not None:
        updates["created_at"] = created_at

    if updates:
        upd = update(Comunicacion).where(Comunicacion.id == com.id).values(**updates)
        await db.execute(upd)
        await db.commit()
        await db.refresh(com)

    return com


# ── 9.5 Worker despacha Pendiente aprobado ────────────────────────────────────


@pytest.mark.asyncio
async def test_worker_despacha_pendiente_aprobado(engine, tenant):
    """Stub SMTP ok → mensaje queda en Enviado, enviado_at registrado."""
    from app.workers.comunicacion_worker import _process_pendientes

    # Crear mensaje Pendiente (tenant sin requiere_aprobacion → False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    cipher = AES256GCMCipher(derive_encryption_key("b" * 64))

    async with session_factory() as session:
        repo = ComunicacionRepository(session, cipher)
        com = await repo.create(
            tenant_id=tenant.id,
            enviado_por=uuid.uuid4(),
            materia_id=uuid.uuid4(),
            destinatario_plain="alumno@test.com",
            asunto="Hola",
            cuerpo="Cuerpo",
        )
        await session.commit()
        com_id = com.id

    # Stub SMTP exitoso
    smtp_stub = MagicMock()
    smtp_stub.send = AsyncMock(return_value=True)

    await _process_pendientes(session_factory, smtp_stub)

    # Verificar estado en DB
    async with session_factory() as session:
        result = await session.execute(select(Comunicacion).where(Comunicacion.id == com_id))
        com = result.scalar_one()

    assert com.estado == EstadoComunicacion.Enviado
    assert com.enviado_at is not None
    smtp_stub.send.assert_called_once_with(
        to="alumno@test.com", subject="Hola", body="Cuerpo"
    )


# ── 9.6 Worker SMTP falla → mensaje queda en Error ───────────────────────────


@pytest.mark.asyncio
async def test_worker_smtp_falla_pasa_a_error(engine, tenant):
    """Stub SMTP lanza exception → mensaje queda en Error."""
    from app.workers.comunicacion_worker import _process_pendientes

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    cipher = AES256GCMCipher(derive_encryption_key("b" * 64))

    async with session_factory() as session:
        repo = ComunicacionRepository(session, cipher)
        com = await repo.create(
            tenant_id=tenant.id,
            enviado_por=uuid.uuid4(),
            materia_id=uuid.uuid4(),
            destinatario_plain="fail@test.com",
            asunto="Falla",
            cuerpo="Cuerpo",
        )
        await session.commit()
        com_id = com.id

    # Stub SMTP que lanza error
    smtp_stub = MagicMock()
    smtp_stub.send = AsyncMock(side_effect=Exception("SMTP connection refused"))

    await _process_pendientes(session_factory, smtp_stub)

    async with session_factory() as session:
        result = await session.execute(select(Comunicacion).where(Comunicacion.id == com_id))
        com = result.scalar_one()

    assert com.estado == EstadoComunicacion.Error


# ── 9.7 Worker omite mensajes sin aprobación cuando tenant lo requiere ────────


@pytest.mark.asyncio
async def test_worker_no_procesa_sin_aprobacion_cuando_requiere(engine):
    """Tenant con requiere_aprobacion=True, mensaje sin aprobado_at → worker lo omite."""
    from app.workers.comunicacion_worker import _process_pendientes
    from sqlalchemy import update as sql_update

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    cipher = AES256GCMCipher(derive_encryption_key("b" * 64))

    # Crear tenant que requiere aprobación
    async with session_factory() as session:
        tenant_req = Tenant(id=uuid.uuid4(), name="TenantConAprobacion")
        tenant_req.requiere_aprobacion = True
        session.add(tenant_req)
        await session.commit()

        repo = ComunicacionRepository(session, cipher)
        com = await repo.create(
            tenant_id=tenant_req.id,
            enviado_por=uuid.uuid4(),
            materia_id=uuid.uuid4(),
            destinatario_plain="pending@test.com",
            asunto="Pendiente aprobación",
            cuerpo="Cuerpo",
        )
        await session.commit()
        com_id = com.id

    smtp_stub = MagicMock()
    smtp_stub.send = AsyncMock(return_value=True)

    await _process_pendientes(session_factory, smtp_stub)

    # El mensaje NO debe haber sido procesado — SMTP no fue llamado
    smtp_stub.send.assert_not_called()

    async with session_factory() as session:
        result = await session.execute(select(Comunicacion).where(Comunicacion.id == com_id))
        com = result.scalar_one()

    assert com.estado == EstadoComunicacion.Pendiente  # sigue Pendiente


# ── 9.8 Worker resetea huérfanos al arrancar ─────────────────────────────────


@pytest.mark.asyncio
async def test_worker_reset_huerfanos_al_arrancar(engine, tenant):
    """Mensaje Enviando sin enviado_at y antiguo → worker lo resetea a Error al iniciar."""
    from app.workers.comunicacion_worker import run_worker

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    cipher = AES256GCMCipher(derive_encryption_key("b" * 64))

    # Crear mensaje huérfano: estado=Enviando, enviado_at=None, created_at viejo
    viejo = datetime.now(timezone.utc) - timedelta(minutes=10)
    async with session_factory() as session:
        repo = ComunicacionRepository(session, cipher)
        com = await repo.create(
            tenant_id=tenant.id,
            enviado_por=uuid.uuid4(),
            materia_id=uuid.uuid4(),
            destinatario_plain="huerfano@test.com",
            asunto="Huérfano",
            cuerpo="Cuerpo",
        )
        # Simular estado Enviando huérfano
        upd = (
            update(Comunicacion)
            .where(Comunicacion.id == com.id)
            .values(estado=EstadoComunicacion.Enviando, created_at=viejo)
        )
        await session.execute(upd)
        await session.commit()
        com_id = com.id

    # SMTP stub que nunca se llama (el worker para inmediatamente)
    smtp_stub = MagicMock()
    smtp_stub.send = AsyncMock(return_value=True)

    stop_event = asyncio.Event()
    stop_event.set()  # detener inmediatamente tras el reset de huérfanos

    await run_worker(
        db_session_factory=session_factory,
        smtp_client=smtp_stub,
        poll_interval=1,
        stop_event=stop_event,
    )

    # El mensaje huérfano debe haberse pasado a Error
    async with session_factory() as session:
        result = await session.execute(select(Comunicacion).where(Comunicacion.id == com_id))
        com = result.scalar_one()

    assert com.estado == EstadoComunicacion.Error
