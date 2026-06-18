"""Tests unitarios de los schemas de encuentros y guardias (C-13).

Verifica RN-13 (validación SlotEncuentroCreate) y GuardiaCreate.
Estos son tests de lógica pura — sin DB, sin HTTP.
"""

from __future__ import annotations

import uuid
from datetime import date, time

import pytest
from pydantic import ValidationError

from app.schemas.encuentro import SlotEncuentroCreate
from app.schemas.guardia import GuardiaCreate


# ── SlotEncuentroCreate — RN-13 ───────────────────────────────────────────────


class TestSlotEncuentroCreateRN13:
    def test_recurrente_valido(self):
        """cant_semanas=4 + fecha_inicio → válido."""
        slot = SlotEncuentroCreate(
            titulo="Clase",
            cant_semanas=4,
            fecha_inicio=date(2026, 3, 2),
            hora=time(10, 0),
        )
        assert slot.cant_semanas == 4
        assert slot.fecha_unica is None

    def test_unico_valido(self):
        """fecha_unica sola → válido."""
        slot = SlotEncuentroCreate(
            titulo="Clase única",
            fecha_unica=date(2026, 3, 15),
            hora=time(14, 0),
        )
        assert slot.fecha_unica == date(2026, 3, 15)
        assert slot.cant_semanas is None

    def test_ambos_simultaneos_invalido(self):
        """cant_semanas > 0 y fecha_unica juntos → ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            SlotEncuentroCreate(
                titulo="Conflicto",
                cant_semanas=4,
                fecha_inicio=date(2026, 3, 2),
                fecha_unica=date(2026, 3, 15),
                hora=time(10, 0),
            )
        assert "mutuamente excluyentes" in str(exc_info.value)

    def test_cant_semanas_53_invalido(self):
        """cant_semanas=53 → ValidationError (máximo 52)."""
        with pytest.raises(ValidationError) as exc_info:
            SlotEncuentroCreate(
                titulo="Demasiado",
                cant_semanas=53,
                fecha_inicio=date(2026, 3, 2),
                hora=time(10, 0),
            )
        assert "52" in str(exc_info.value)

    def test_cant_semanas_52_valido(self):
        """cant_semanas=52 → válido (límite exacto)."""
        slot = SlotEncuentroCreate(
            titulo="Un año",
            cant_semanas=52,
            fecha_inicio=date(2026, 1, 5),
            hora=time(9, 0),
        )
        assert slot.cant_semanas == 52

    def test_ninguno_invalido(self):
        """Ni cant_semanas ni fecha_unica → ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            SlotEncuentroCreate(
                titulo="Incompleto",
                hora=time(10, 0),
            )
        assert "Debe proveer" in str(exc_info.value)

    def test_recurrente_sin_fecha_inicio_invalido(self):
        """cant_semanas sin fecha_inicio → ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            SlotEncuentroCreate(
                titulo="Sin inicio",
                cant_semanas=4,
                hora=time(10, 0),
            )
        assert "fecha_inicio" in str(exc_info.value)

    def test_extra_field_forbid(self):
        """Campo extra en SlotEncuentroCreate → ValidationError."""
        with pytest.raises(ValidationError):
            SlotEncuentroCreate(
                titulo="x",
                fecha_unica=date(2026, 3, 15),
                hora=time(10, 0),
                campo_extra="no permitido",
            )


# ── GuardiaCreate ─────────────────────────────────────────────────────────────


class TestGuardiaCreate:
    def test_guardia_valida(self):
        """GuardiaCreate con horario válido → OK."""
        g = GuardiaCreate(
            materia_id=uuid.uuid4(),
            dia=date(2026, 3, 10),
            horario="14:00–14:45",
        )
        assert g.horario == "14:00–14:45"

    def test_horario_vacio_invalido(self):
        """Horario vacío → ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            GuardiaCreate(
                materia_id=uuid.uuid4(),
                dia=date(2026, 3, 10),
                horario="",
            )
        assert "vacío" in str(exc_info.value)

    def test_horario_solo_espacios_invalido(self):
        """Horario con solo espacios → ValidationError."""
        with pytest.raises(ValidationError):
            GuardiaCreate(
                materia_id=uuid.uuid4(),
                dia=date(2026, 3, 10),
                horario="   ",
            )

    def test_asignacion_id_no_en_schema(self):
        """asignacion_id no existe en GuardiaCreate (extra='forbid')."""
        with pytest.raises(ValidationError):
            GuardiaCreate(
                materia_id=uuid.uuid4(),
                dia=date(2026, 3, 10),
                horario="14:00–14:45",
                asignacion_id=str(uuid.uuid4()),  # campo prohibido
            )

    def test_extra_field_forbid(self):
        """Campo extra → ValidationError (extra='forbid')."""
        with pytest.raises(ValidationError):
            GuardiaCreate(
                materia_id=uuid.uuid4(),
                dia=date(2026, 3, 10),
                horario="14:00–14:45",
                tenant_id=str(uuid.uuid4()),  # campo prohibido
            )
