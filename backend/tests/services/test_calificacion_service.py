"""Tests TDD para CalificacionService (C-10 — Tareas 7.1–7.4 y verificación integración).

Valida:
- Una importación exitosa registra AuditLog con accion="CALIFICACIONES_IMPORTAR"
- Preview no genera el evento de auditoría
- Selección vacía no genera el evento de auditoría
"""

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.models.base import Base
from app.models.tenant import Tenant
from app.models.audit_log import AuditLog
import app.models  # noqa: F401


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
async def tenant(db):
    t = Tenant(id=uuid.uuid4(), name="Tenant Audit")
    db.add(t)
    await db.commit()
    return t


@pytest.fixture
async def usuario_id():
    return uuid.uuid4()


@pytest.fixture
async def entrada_padron(db, tenant):
    from app.models.padron import EntradaPadron, VersionPadron

    vp = VersionPadron(
        tenant_id=tenant.id,
        materia_id=uuid.uuid4(),
        cohorte_id=uuid.uuid4(),
        cargado_por=uuid.uuid4(),
        activa=True,
    )
    db.add(vp)
    await db.flush()

    ep = EntradaPadron(
        version_id=vp.id,
        tenant_id=tenant.id,
        nombre="Test",
        apellidos="Alumno",
        email_enc="ENC",
    )
    db.add(ep)
    await db.commit()
    return ep


def _build_service(db):
    from app.repositories.audit_log_repository import AuditLogRepository
    from app.repositories.calificacion_repository import CalificacionRepository
    from app.repositories.umbral_repository import UmbralRepository
    from app.services.calificacion_service import CalificacionService
    from app.services.umbral_service import UmbralService

    cal_repo = CalificacionRepository(db)
    audit_repo = AuditLogRepository(db)
    umbral_repo = UmbralRepository(db)
    umbral_svc = UmbralService(umbral_repo)
    return CalificacionService(cal_repo, audit_repo, umbral_svc)


# ── Auditoría de importación ──────────────────────────────────────────────────


class TestCalificacionServiceAuditoria:
    async def test_importar_registra_audit_log(self, db, tenant, usuario_id, entrada_padron):
        """Una importación exitosa registra AuditLog con CALIFICACIONES_IMPORTAR."""
        service = _build_service(db)
        materia_id = uuid.uuid4()

        # Actividades detectadas (simula resultado del parser)
        actividades = [
            {"nombre": "TP1", "escala": "numerica", "columna_csv": "TP1 (Real)"},
        ]
        filas = [{"entrada_padron_id": entrada_padron.id, "TP1 (Real)": "8"}]

        await service.importar(
            tenant_id=tenant.id,
            actor_id=usuario_id,
            materia_id=materia_id,
            actividades=actividades,
            seleccionadas=["TP1"],
            filas=filas,
            ip="127.0.0.1",
            user_agent="TestAgent/1.0",
        )

        result = await db.execute(
            select(AuditLog).where(
                AuditLog.tenant_id == tenant.id,
                AuditLog.accion == "CALIFICACIONES_IMPORTAR",
            )
        )
        logs = result.scalars().all()
        assert len(logs) == 1
        log = logs[0]
        assert log.actor_id == usuario_id
        assert log.materia_id == materia_id
        assert log.filas_afectadas == 1
        assert log.ip == "127.0.0.1"
        assert log.user_agent == "TestAgent/1.0"

    async def test_preview_no_registra_audit_log(self, db, tenant, usuario_id):
        """preview() no crea ningún AuditLog."""
        service = _build_service(db)
        materia_id = uuid.uuid4()

        csv_data = b"Nombre,Email,TP1 (Real)\nAna,ana@test.com,8"
        await service.preview(
            tenant_id=tenant.id,
            materia_id=materia_id,
            csv_data=csv_data,
            escala_textual=[],
        )

        result = await db.execute(select(AuditLog))
        logs = result.scalars().all()
        assert len(logs) == 0

    async def test_seleccion_vacia_no_registra_audit_log(self, db, tenant, usuario_id, entrada_padron):
        """Importación con lista de actividades seleccionadas vacía → sin auditoría."""
        service = _build_service(db)
        materia_id = uuid.uuid4()

        actividades = [
            {"nombre": "TP1", "escala": "numerica", "columna_csv": "TP1 (Real)"},
        ]
        filas = [{"entrada_padron_id": entrada_padron.id, "TP1 (Real)": "8"}]

        await service.importar(
            tenant_id=tenant.id,
            actor_id=usuario_id,
            materia_id=materia_id,
            actividades=actividades,
            seleccionadas=[],  # selección vacía → 0 calificaciones
            filas=filas,
            ip="127.0.0.1",
            user_agent="TestAgent/1.0",
        )

        result = await db.execute(select(AuditLog))
        logs = result.scalars().all()
        assert len(logs) == 0
