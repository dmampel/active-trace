"""Schemas Pydantic para el módulo de padrón.

Todos los schemas tienen extra='forbid' para rechazar campos no declarados.
El campo email en los schemas de salida siempre está descifrado (plaintext);
el cifrado/descifrado ocurre en el Service, nunca en schemas ni repositories.
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


# ── Requests ──────────────────────────────────────────────────────────────────


class ImportarPadronMoodleRequest(BaseModel):
    """Body para importar padrón desde Moodle WS."""

    model_config = ConfigDict(extra="forbid")

    course_id: int
    cohorte_id: uuid.UUID


class MoodleConfigRequest(BaseModel):
    """Body para configurar la conexión Moodle de un tenant."""

    model_config = ConfigDict(extra="forbid")

    moodle_url: str
    moodle_token: str


# ── Responses ─────────────────────────────────────────────────────────────────


class EntradaPadronOut(BaseModel):
    """Entrada individual del padrón (alumno). Email siempre descifrado."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    nombre: str
    apellidos: str
    email: str  # descifrado por el Service antes de serializar
    comision: Optional[str] = None
    regional: Optional[str] = None
    usuario_id: Optional[uuid.UUID] = None


class VersionPadronOut(BaseModel):
    """Metadata de una versión del padrón."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    materia_id: uuid.UUID
    cohorte_id: uuid.UUID
    cargado_por: Optional[uuid.UUID] = None
    cargado_at: datetime
    activa: bool
    total_entradas: int = 0


class VersionPadronDetalleOut(BaseModel):
    """VersionPadron con sus EntradaPadron incluidas."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    materia_id: uuid.UUID
    cohorte_id: uuid.UUID
    cargado_por: Optional[uuid.UUID] = None
    cargado_at: datetime
    activa: bool
    entradas: list[EntradaPadronOut]


class ImportarResultadoOut(BaseModel):
    """Resultado de una operación de importación."""

    model_config = ConfigDict(extra="forbid")

    version_id: uuid.UUID
    total_importado: int
    activa: bool
