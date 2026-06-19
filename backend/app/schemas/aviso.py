"""Schemas Pydantic v2 para el módulo de avisos y acknowledgment (C-15).

Todos los schemas usan extra='forbid' para rechazar campos no declarados.
tenant_id nunca se acepta en requests — viene siempre del JWT.

Validaciones cross-field (model_validator):
- PorMateria exige materia_id
- PorCohorte exige cohorte_id
- PorRol    exige rol_destino
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, model_validator

from app.models.aviso import AlcanceAviso, SeveridadAviso


# ── AvisoCreate ───────────────────────────────────────────────────────────────


class AvisoCreate(BaseModel):
    """Payload para crear un aviso institucional.

    Validaciones cross-field:
    - alcance=PorMateria → materia_id es requerido
    - alcance=PorCohorte → cohorte_id es requerido
    - alcance=PorRol     → rol_destino es requerido
    tenant_id NO se acepta — viene del JWT.
    """

    model_config = ConfigDict(extra="forbid")

    alcance: AlcanceAviso
    materia_id: Optional[uuid.UUID] = None
    cohorte_id: Optional[uuid.UUID] = None
    rol_destino: Optional[str] = None
    severidad: SeveridadAviso = SeveridadAviso.Info
    titulo: str
    cuerpo: str
    inicio_en: datetime
    fin_en: Optional[datetime] = None
    orden: int = 0
    activo: bool = True
    requiere_ack: bool = False

    @model_validator(mode="after")
    def validar_contexto_alcance(self) -> "AvisoCreate":
        if self.alcance == AlcanceAviso.PorMateria and self.materia_id is None:
            raise ValueError("materia_id es requerido cuando alcance=PorMateria")
        if self.alcance == AlcanceAviso.PorCohorte and self.cohorte_id is None:
            raise ValueError("cohorte_id es requerido cuando alcance=PorCohorte")
        if self.alcance == AlcanceAviso.PorRol and self.rol_destino is None:
            raise ValueError("rol_destino es requerido cuando alcance=PorRol")
        return self


# ── AvisoUpdate ───────────────────────────────────────────────────────────────


class AvisoUpdate(BaseModel):
    """Payload para actualizar parcialmente un aviso.

    Todos los campos son opcionales. Las mismas validaciones cross-field aplican
    cuando alcance está presente.
    """

    model_config = ConfigDict(extra="forbid")

    alcance: Optional[AlcanceAviso] = None
    materia_id: Optional[uuid.UUID] = None
    cohorte_id: Optional[uuid.UUID] = None
    rol_destino: Optional[str] = None
    severidad: Optional[SeveridadAviso] = None
    titulo: Optional[str] = None
    cuerpo: Optional[str] = None
    inicio_en: Optional[datetime] = None
    fin_en: Optional[datetime] = None
    orden: Optional[int] = None
    activo: Optional[bool] = None
    requiere_ack: Optional[bool] = None

    @model_validator(mode="after")
    def validar_contexto_alcance(self) -> "AvisoUpdate":
        if self.alcance is None:
            return self
        if self.alcance == AlcanceAviso.PorMateria and self.materia_id is None:
            raise ValueError("materia_id es requerido cuando alcance=PorMateria")
        if self.alcance == AlcanceAviso.PorCohorte and self.cohorte_id is None:
            raise ValueError("cohorte_id es requerido cuando alcance=PorCohorte")
        if self.alcance == AlcanceAviso.PorRol and self.rol_destino is None:
            raise ValueError("rol_destino es requerido cuando alcance=PorRol")
        return self


# ── AvisoResponse ─────────────────────────────────────────────────────────────


class AvisoResponse(BaseModel):
    """Respuesta de aviso para gestión (COORDINADOR/ADMIN).

    Incluye contadores derivados de AcknowledgmentAviso:
    - total_vistas: usuarios únicos que confirmaron (igual a total_acks en este modelo)
    - total_acks: confirmaciones únicas registradas
    """

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    alcance: AlcanceAviso
    materia_id: Optional[uuid.UUID]
    cohorte_id: Optional[uuid.UUID]
    rol_destino: Optional[str]
    severidad: SeveridadAviso
    titulo: str
    cuerpo: str
    inicio_en: datetime
    fin_en: Optional[datetime]
    orden: int
    activo: bool
    requiere_ack: bool
    total_vistas: int
    total_acks: int


# ── AvisoFeedItem ─────────────────────────────────────────────────────────────


class AvisoFeedItem(BaseModel):
    """Vista del destinatario: aviso en el feed de mis-avisos.

    Sin contadores de gestión. Con flag ya_confirmado para que el cliente
    pueda mostrar el estado de lectura del usuario autenticado.
    """

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    alcance: AlcanceAviso
    severidad: SeveridadAviso
    titulo: str
    cuerpo: str
    inicio_en: datetime
    fin_en: Optional[datetime]
    orden: int
    requiere_ack: bool
    ya_confirmado: bool
