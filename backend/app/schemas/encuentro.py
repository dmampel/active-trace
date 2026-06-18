"""Schemas Pydantic v2 para el módulo de encuentros (C-13).

Todos los schemas usan extra='forbid' para rechazar campos no declarados.

RN-13: SlotEncuentroCreate valida que exactamente uno de cant_semanas > 0
o fecha_unica esté presente (mutuamente excluyentes). cant_semanas <= 52.
"""

from __future__ import annotations

import uuid
from datetime import date, time
from typing import Optional

from pydantic import BaseModel, ConfigDict, model_validator

from app.models.encuentro import DiaSemana, EstadoInstanciaEncuentro


# ── InstanciaEncuentro ────────────────────────────────────────────────────────


class InstanciaEncuentroResponse(BaseModel):
    """Respuesta de una instancia individual de encuentro."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    slot_id: Optional[uuid.UUID]
    fecha: date
    hora: time
    estado: EstadoInstanciaEncuentro
    meet_url: Optional[str]
    video_url: Optional[str]
    comentario: Optional[str]


class InstanciaEncuentroUpdate(BaseModel):
    """Payload para editar una instancia individual (PATCH).

    Todos los campos son opcionales — solo se actualizan los provistos (RN-14).
    """

    model_config = ConfigDict(extra="forbid")

    estado: Optional[EstadoInstanciaEncuentro] = None
    meet_url: Optional[str] = None
    video_url: Optional[str] = None
    comentario: Optional[str] = None


# ── SlotEncuentro ─────────────────────────────────────────────────────────────


class SlotEncuentroCreate(BaseModel):
    """Payload para crear un slot de encuentro.

    RN-13: exactamente uno de cant_semanas > 0 o fecha_unica debe estar presente.
    cant_semanas <= 52 (máximo 1 año de recurrencia).

    Recurrente: cant_semanas > 0, fecha_inicio, dia_semana, hora (fecha_unica = None).
    Único:      fecha_unica, hora (cant_semanas = None, fecha_inicio = None).
    """

    model_config = ConfigDict(extra="forbid")

    titulo: str
    cant_semanas: Optional[int] = None
    fecha_inicio: Optional[date] = None
    dia_semana: Optional[DiaSemana] = None
    fecha_unica: Optional[date] = None
    hora: time
    meet_url: Optional[str] = None
    descripcion: Optional[str] = None

    @model_validator(mode="after")
    def validar_exclusividad_rn13(self) -> "SlotEncuentroCreate":
        """RN-13: cant_semanas > 0 XOR fecha_unica (mutuamente excluyentes)."""
        tiene_recurrente = self.cant_semanas is not None and self.cant_semanas > 0
        tiene_unico = self.fecha_unica is not None

        if tiene_recurrente and tiene_unico:
            raise ValueError(
                "cant_semanas y fecha_unica son mutuamente excluyentes. "
                "Provea uno o el otro, no ambos."
            )
        if not tiene_recurrente and not tiene_unico:
            raise ValueError(
                "Debe proveer cant_semanas > 0 (recurrente) o fecha_unica (único)."
            )
        if tiene_recurrente:
            if self.cant_semanas > 52:  # type: ignore[operator]
                raise ValueError("cant_semanas no puede superar 52 (máximo 1 año).")
            if self.fecha_inicio is None:
                raise ValueError(
                    "fecha_inicio es requerida para slots recurrentes."
                )
        return self


class SlotEncuentroResponse(BaseModel):
    """Respuesta de un slot con su lista de instancias anidadas."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    asignacion_id: uuid.UUID
    titulo: str
    cant_semanas: Optional[int]
    fecha_inicio: Optional[date]
    dia_semana: Optional[DiaSemana]
    fecha_unica: Optional[date]
    hora: time
    meet_url: Optional[str]
    descripcion: Optional[str]
    instancias: list[InstanciaEncuentroResponse] = []
