"""Servicio de encuentros sincrónicos (C-13).

Responsabilidades:
- crear_slot(): aplica RN-13 — genera N instancias recurrentes o 1 única.
- editar_instancia(): aplica RN-14 — edita solo los campos provistos.
- listar_slots_propios(): slots del docente autenticado (por asignacion_id).
- listar_admin(): todas las instancias del tenant para COORDINADOR/ADMIN.
- generar_html_block(): tabla HTML con Jinja2 auto-escape (D3).

NO accede directamente a la DB — siempre vía repositorios.
NO contiene lógica de RBAC — eso es responsabilidad de los routers.
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta

from fastapi import HTTPException, status
from jinja2 import Environment

from app.models.encuentro import EstadoInstanciaEncuentro, InstanciaEncuentro, SlotEncuentro
from app.repositories.encuentro_repository import (
    InstanciaEncuentroRepository,
    SlotEncuentroRepository,
)
from app.schemas.encuentro import (
    InstanciaEncuentroUpdate,
    SlotEncuentroCreate,
    SlotEncuentroResponse,
)

# Jinja2 con auto-escape activado para proteger contra HTML injection (D3)
_JINJA_ENV = Environment(autoescape=True)

_HTML_TEMPLATE = _JINJA_ENV.from_string(
    """<table>
<thead>
  <tr><th>Fecha</th><th>Hora</th><th>Estado</th><th>Enlace</th><th>Comentario</th></tr>
</thead>
<tbody>
{% for inst in instancias %}
  <tr>
    <td>{{ inst.fecha }}</td>
    <td>{{ inst.hora }}</td>
    <td>{{ inst.estado }}</td>
    <td>{% if inst.estado == 'Realizado' and inst.video_url %}<a href="{{ inst.video_url }}">Ver video</a>{% endif %}</td>
    <td>{{ inst.comentario or '' }}</td>
  </tr>
{% endfor %}
</tbody>
</table>"""
)


class EncuentrosService:
    def __init__(
        self,
        slot_repo: SlotEncuentroRepository,
        instancia_repo: InstanciaEncuentroRepository,
    ) -> None:
        self.slot_repo = slot_repo
        self.instancia_repo = instancia_repo

    async def crear_slot(
        self,
        data: SlotEncuentroCreate,
        *,
        asignacion_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> SlotEncuentroResponse:
        """Crea un SlotEncuentro y genera sus InstanciaEncuentro (RN-13).

        Recurrente: genera cant_semanas instancias con fechas espaciadas 7 días.
        Único: genera 1 instancia con fecha_unica.
        """
        slot = SlotEncuentro(
            tenant_id=tenant_id,
            asignacion_id=asignacion_id,
            titulo=data.titulo,
            cant_semanas=data.cant_semanas,
            fecha_inicio=data.fecha_inicio,
            dia_semana=data.dia_semana,
            fecha_unica=data.fecha_unica,
            hora=data.hora,
            meet_url=data.meet_url,
            descripcion=data.descripcion,
        )
        slot = await self.slot_repo.create(slot)

        # Generación de instancias (D2 — en el service, no en DB)
        instancias_data: list[InstanciaEncuentro] = []
        if data.cant_semanas and data.cant_semanas > 0 and data.fecha_inicio:
            # Recurrente: N instancias con intervalos de 7 días
            for n in range(data.cant_semanas):
                fecha_inst: date = data.fecha_inicio + timedelta(weeks=n)
                instancias_data.append(
                    InstanciaEncuentro(
                        tenant_id=tenant_id,
                        slot_id=slot.id,
                        fecha=fecha_inst,
                        hora=data.hora,
                        estado=EstadoInstanciaEncuentro.Programado,
                    )
                )
        else:
            # Único: 1 instancia con fecha_unica
            assert data.fecha_unica is not None  # garantizado por RN-13 en schema
            instancias_data.append(
                InstanciaEncuentro(
                    tenant_id=tenant_id,
                    slot_id=slot.id,
                    fecha=data.fecha_unica,
                    hora=data.hora,
                    estado=EstadoInstanciaEncuentro.Programado,
                )
            )

        instancias = await self.instancia_repo.bulk_create(instancias_data)

        return SlotEncuentroResponse(
            id=slot.id,
            asignacion_id=slot.asignacion_id,
            titulo=slot.titulo,
            cant_semanas=slot.cant_semanas,
            fecha_inicio=slot.fecha_inicio,
            dia_semana=slot.dia_semana,
            fecha_unica=slot.fecha_unica,
            hora=slot.hora,
            meet_url=slot.meet_url,
            descripcion=slot.descripcion,
            instancias=[
                _instancia_to_response(i) for i in instancias
            ],
        )

    async def editar_instancia(
        self,
        instancia_id: uuid.UUID,
        data: InstanciaEncuentroUpdate,
        *,
        tenant_id: uuid.UUID,
    ):
        """Edita solo los campos provistos de una instancia individual (RN-14).

        Retorna 404 si la instancia no existe o pertenece a otro tenant.
        """
        instancia = await self.instancia_repo.update(
            instancia_id,
            tenant_id,
            estado=data.estado,
            meet_url=data.meet_url,
            video_url=data.video_url,
            comentario=data.comentario,
        )
        if instancia is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Instancia de encuentro no encontrada",
            )
        return _instancia_to_response(instancia)

    async def listar_slots_propios(
        self,
        asignacion_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> list[SlotEncuentroResponse]:
        """Retorna slots del usuario autenticado con sus instancias."""
        slots = await self.slot_repo.list_by_asignacion(asignacion_id, tenant_id)
        result = []
        for slot in slots:
            instancias = await self.instancia_repo.list_by_slot(slot.id, tenant_id)
            result.append(
                SlotEncuentroResponse(
                    id=slot.id,
                    asignacion_id=slot.asignacion_id,
                    titulo=slot.titulo,
                    cant_semanas=slot.cant_semanas,
                    fecha_inicio=slot.fecha_inicio,
                    dia_semana=slot.dia_semana,
                    fecha_unica=slot.fecha_unica,
                    hora=slot.hora,
                    meet_url=slot.meet_url,
                    descripcion=slot.descripcion,
                    instancias=[_instancia_to_response(i) for i in instancias],
                )
            )
        return result

    async def listar_admin(self, tenant_id: uuid.UUID):
        """Retorna todas las instancias del tenant para COORDINADOR/ADMIN."""
        from app.schemas.encuentro import InstanciaEncuentroResponse
        instancias = await self.instancia_repo.list_all_tenant(tenant_id)
        return [_instancia_to_response(i) for i in instancias]

    async def generar_html_block(
        self,
        asignacion_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> str:
        """Genera bloque HTML con calendario de encuentros (D3).

        Jinja2 auto-escape activo — caracteres especiales escapados automáticamente.
        """
        slots = await self.slot_repo.list_by_asignacion(asignacion_id, tenant_id)
        all_instancias = []
        for slot in slots:
            instancias = await self.instancia_repo.list_by_slot(slot.id, tenant_id)
            all_instancias.extend(instancias)

        # Ordenar por fecha
        all_instancias.sort(key=lambda i: i.fecha)

        # Construir contexto para Jinja2 (dicts plain para auto-escape correcto)
        ctx_instancias = [
            {
                "fecha": str(i.fecha),
                "hora": str(i.hora),
                "estado": i.estado.value,
                "video_url": i.video_url or "",
                "comentario": i.comentario or "",
            }
            for i in all_instancias
        ]
        return _HTML_TEMPLATE.render(instancias=ctx_instancias)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _instancia_to_response(i: InstanciaEncuentro):
    from app.schemas.encuentro import InstanciaEncuentroResponse
    return InstanciaEncuentroResponse(
        id=i.id,
        slot_id=i.slot_id,
        fecha=i.fecha,
        hora=i.hora,
        estado=i.estado,
        meet_url=i.meet_url,
        video_url=i.video_url,
        comentario=i.comentario,
    )
