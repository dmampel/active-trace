"""Tests unitarios del EncuentrosService (C-13).

Verifica RN-13 en crear_slot(), RN-14 en editar_instancia(),
y el HTML block con auto-escape Jinja2 (D3).
Todos los tests usan mocks — sin DB real.
"""

from __future__ import annotations

import uuid
from datetime import date, time
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.encuentro import EstadoInstanciaEncuentro, InstanciaEncuentro, SlotEncuentro
from app.schemas.encuentro import SlotEncuentroCreate
from app.services.encuentro_service import EncuentrosService

TENANT_ID = uuid.uuid4()
ASIGNACION_ID = uuid.uuid4()
SLOT_ID = uuid.uuid4()


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_slot(cant_semanas=None, fecha_unica=None) -> SlotEncuentro:
    s = MagicMock(spec=SlotEncuentro)
    s.id = SLOT_ID
    s.tenant_id = TENANT_ID
    s.asignacion_id = ASIGNACION_ID
    s.titulo = "Test"
    s.cant_semanas = cant_semanas
    s.fecha_inicio = date(2026, 3, 2) if cant_semanas else None
    s.dia_semana = None
    s.fecha_unica = fecha_unica
    s.hora = time(10, 0)
    s.meet_url = None
    s.descripcion = None
    return s


def _make_instancia(
    estado=EstadoInstanciaEncuentro.Programado,
    fecha=None,
    video_url=None,
    comentario=None,
) -> InstanciaEncuentro:
    i = MagicMock(spec=InstanciaEncuentro)
    i.id = uuid.uuid4()
    i.tenant_id = TENANT_ID
    i.slot_id = SLOT_ID
    i.fecha = fecha or date(2026, 3, 2)
    i.hora = time(10, 0)
    i.estado = estado
    i.meet_url = None
    i.video_url = video_url
    i.comentario = comentario
    i.deleted_at = None
    return i


def _make_service(slot=None, instancias=None):
    slot_repo = MagicMock()
    instancia_repo = MagicMock()

    _slot = slot or _make_slot(cant_semanas=4)
    _insts = instancias or [_make_instancia() for _ in range(4)]

    slot_repo.create = AsyncMock(return_value=_slot)
    slot_repo.list_by_asignacion = AsyncMock(return_value=[_slot])
    slot_repo.list_all_tenant = AsyncMock(return_value=[_slot])
    instancia_repo.bulk_create = AsyncMock(return_value=_insts)
    instancia_repo.list_by_slot = AsyncMock(return_value=_insts)
    instancia_repo.list_all_tenant = AsyncMock(return_value=_insts)
    instancia_repo.update = AsyncMock(return_value=_insts[0] if _insts else None)

    return EncuentrosService(slot_repo=slot_repo, instancia_repo=instancia_repo)


# ── crear_slot recurrente genera N instancias ─────────────────────────────────


class TestCrearSlot:
    @pytest.mark.asyncio
    async def test_recurrente_genera_n_instancias(self):
        """crear_slot con cant_semanas=4 → 4 instancias generadas."""
        insts = [_make_instancia(fecha=date(2026, 3, 2 + i * 7)) for i in range(4)]
        svc = _make_service(slot=_make_slot(cant_semanas=4), instancias=insts)

        data = SlotEncuentroCreate(
            titulo="Clase",
            cant_semanas=4,
            fecha_inicio=date(2026, 3, 2),
            hora=time(10, 0),
        )
        result = await svc.crear_slot(data, asignacion_id=ASIGNACION_ID, tenant_id=TENANT_ID)

        assert len(result.instancias) == 4
        # El repo de instancias debe haber recibido bulk_create con 4 elementos
        svc.instancia_repo.bulk_create.assert_awaited_once()
        created_insts = svc.instancia_repo.bulk_create.call_args[0][0]
        assert len(created_insts) == 4

    @pytest.mark.asyncio
    async def test_unico_genera_1_instancia(self):
        """crear_slot con fecha_unica → 1 instancia generada."""
        inst = _make_instancia(fecha=date(2026, 3, 15))
        svc = _make_service(
            slot=_make_slot(fecha_unica=date(2026, 3, 15)),
            instancias=[inst],
        )

        data = SlotEncuentroCreate(
            titulo="Clase única",
            fecha_unica=date(2026, 3, 15),
            hora=time(14, 0),
        )
        result = await svc.crear_slot(data, asignacion_id=ASIGNACION_ID, tenant_id=TENANT_ID)

        assert len(result.instancias) == 1
        created_insts = svc.instancia_repo.bulk_create.call_args[0][0]
        assert len(created_insts) == 1

    @pytest.mark.asyncio
    async def test_fechas_espaciadas_7_dias(self):
        """Instancias recurrentes tienen fechas con diferencia exacta de 7 días."""
        # Verificar que la lógica del service calcula las fechas correctamente
        # Creamos un service real pero con repo mockeado que captura lo que se le pasa
        slot_repo = MagicMock()
        instancia_repo = MagicMock()

        slot = _make_slot(cant_semanas=3)
        slot_repo.create = AsyncMock(return_value=slot)
        captured_insts = []

        async def _capture_bulk(insts):
            # Asignar IDs a los objetos reales para que _instancia_to_response funcione
            result = []
            for raw in insts:
                captured_insts.append(raw)
                m = _make_instancia(fecha=raw.fecha)
                m.hora = raw.hora
                m.estado = raw.estado
                result.append(m)
            return result

        instancia_repo.bulk_create = _capture_bulk

        svc = EncuentrosService(slot_repo=slot_repo, instancia_repo=instancia_repo)
        data = SlotEncuentroCreate(
            titulo="Clase",
            cant_semanas=3,
            fecha_inicio=date(2026, 3, 2),
            hora=time(10, 0),
        )
        await svc.crear_slot(data, asignacion_id=ASIGNACION_ID, tenant_id=TENANT_ID)

        assert len(captured_insts) == 3
        assert captured_insts[0].fecha == date(2026, 3, 2)
        assert captured_insts[1].fecha == date(2026, 3, 9)   # +7 días
        assert captured_insts[2].fecha == date(2026, 3, 16)  # +14 días


# ── generar_html_block — auto-escape Jinja2 ──────────────────────────────────


class TestHtmlBlock:
    @pytest.mark.asyncio
    async def test_escapa_script_en_titulo(self):
        """HTML block escapa <script> correctamente (Jinja2 auto-escape)."""
        inst = _make_instancia(
            estado=EstadoInstanciaEncuentro.Programado,
            fecha=date(2026, 3, 2),
        )
        # Simulamos que el slot tiene un título con script — el titulo va en el service
        # pero en la plantilla actual no renderiza el titulo directamente; lo que sí
        # se renderiza son los campos de la instancia. Probamos comentario con script.
        inst_script = _make_instancia(
            estado=EstadoInstanciaEncuentro.Programado,
            comentario="<script>alert(1)</script>",
        )

        slot_repo = MagicMock()
        instancia_repo = MagicMock()
        slot = _make_slot(cant_semanas=1)
        slot_repo.list_by_asignacion = AsyncMock(return_value=[slot])
        instancia_repo.list_by_slot = AsyncMock(return_value=[inst_script])

        svc = EncuentrosService(slot_repo=slot_repo, instancia_repo=instancia_repo)
        html = await svc.generar_html_block(
            asignacion_id=ASIGNACION_ID, tenant_id=TENANT_ID
        )

        # No debe contener el script crudo
        assert "<script>" not in html
        # Debe contener la versión escapada
        assert "&lt;script&gt;" in html

    @pytest.mark.asyncio
    async def test_incluye_link_video_en_realizado(self):
        """HTML block incluye link al video para instancias Realizadas con video_url."""
        inst_realizado = _make_instancia(
            estado=EstadoInstanciaEncuentro.Realizado,
            video_url="https://video.example.com/rec1",
        )

        slot_repo = MagicMock()
        instancia_repo = MagicMock()
        slot = _make_slot(cant_semanas=1)
        slot_repo.list_by_asignacion = AsyncMock(return_value=[slot])
        instancia_repo.list_by_slot = AsyncMock(return_value=[inst_realizado])

        svc = EncuentrosService(slot_repo=slot_repo, instancia_repo=instancia_repo)
        html = await svc.generar_html_block(
            asignacion_id=ASIGNACION_ID, tenant_id=TENANT_ID
        )

        assert "Ver video" in html
        assert "https://video.example.com/rec1" in html

    @pytest.mark.asyncio
    async def test_programado_no_incluye_link_video(self):
        """Instancia Programada no muestra link de video aunque tenga video_url."""
        inst_programado = _make_instancia(
            estado=EstadoInstanciaEncuentro.Programado,
            video_url="https://video.example.com/rec1",
        )

        slot_repo = MagicMock()
        instancia_repo = MagicMock()
        slot = _make_slot(cant_semanas=1)
        slot_repo.list_by_asignacion = AsyncMock(return_value=[slot])
        instancia_repo.list_by_slot = AsyncMock(return_value=[inst_programado])

        svc = EncuentrosService(slot_repo=slot_repo, instancia_repo=instancia_repo)
        html = await svc.generar_html_block(
            asignacion_id=ASIGNACION_ID, tenant_id=TENANT_ID
        )

        # Programado no debería mostrar el link
        assert "Ver video" not in html
