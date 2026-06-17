"""Tests TDD para el cruce de reporte de finalización (C-10 — Tareas 5.1–5.5).

RN-07: entrega textual finalizada sin calificación → "sin corregir"
RN-08: actividades de escala numérica se excluyen del reporte "sin corregir"

El cruce es puro (sin DB): compara el reporte de finalización (list[dict])
con las calificaciones ya importadas (list[Calificacion]).
"""

import uuid
from datetime import datetime, timezone

import pytest

from app.models.calificacion import Calificacion, OrigenCalificacion


def _cal(entrada_padron_id: uuid.UUID, actividad: str, nota_textual: str | None = "Satisfactorio") -> Calificacion:
    """Helper — construye una Calificacion sin persistir."""
    return Calificacion(
        entrada_padron_id=entrada_padron_id,
        materia_id=uuid.uuid4(),
        actividad=actividad,
        nota_numerica=None,
        nota_textual=nota_textual,
        origen=OrigenCalificacion.IMPORTADO,
        importado_at=datetime.now(timezone.utc),
        tenant_id=uuid.uuid4(),
    )


# ── Cruce de finalización ─────────────────────────────────────────────────────


class TestCruceFinalizacion:
    def test_entrega_textual_finalizada_sin_calificacion_es_sin_corregir(self):
        """RN-07: textual finalizada sin nota → aparece como 'sin corregir'."""
        from app.services.calificacion_finalizacion import detectar_sin_corregir

        entrada_id = uuid.uuid4()
        finalizaciones = [
            {"entrada_padron_id": entrada_id, "actividad": "Proyecto", "escala": "textual", "finalizado": True},
        ]
        calificaciones = []  # sin notas

        sin_corregir = detectar_sin_corregir(finalizaciones, calificaciones)

        assert len(sin_corregir) == 1
        assert sin_corregir[0]["entrada_padron_id"] == entrada_id
        assert sin_corregir[0]["actividad"] == "Proyecto"

    def test_actividad_numerica_no_figura_aunque_no_tenga_nota(self):
        """RN-08: actividad numérica finalizada sin calificación NO es 'sin corregir'."""
        from app.services.calificacion_finalizacion import detectar_sin_corregir

        entrada_id = uuid.uuid4()
        finalizaciones = [
            {"entrada_padron_id": entrada_id, "actividad": "TP1", "escala": "numerica", "finalizado": True},
        ]
        calificaciones = []

        sin_corregir = detectar_sin_corregir(finalizaciones, calificaciones)

        assert len(sin_corregir) == 0

    def test_entrega_textual_ya_calificada_no_figura(self):
        """Triangulación: textual finalizada y con calificación → NO es sin corregir."""
        from app.services.calificacion_finalizacion import detectar_sin_corregir

        entrada_id = uuid.uuid4()
        finalizaciones = [
            {"entrada_padron_id": entrada_id, "actividad": "Proyecto", "escala": "textual", "finalizado": True},
        ]
        calificaciones = [_cal(entrada_id, "Proyecto", nota_textual="Satisfactorio")]

        sin_corregir = detectar_sin_corregir(finalizaciones, calificaciones)

        assert len(sin_corregir) == 0

    def test_solo_finalizadas_cuentan(self):
        """Triangulación: textual no finalizada → NO es sin corregir."""
        from app.services.calificacion_finalizacion import detectar_sin_corregir

        entrada_id = uuid.uuid4()
        finalizaciones = [
            {"entrada_padron_id": entrada_id, "actividad": "Proyecto", "escala": "textual", "finalizado": False},
        ]
        calificaciones = []

        sin_corregir = detectar_sin_corregir(finalizaciones, calificaciones)

        assert len(sin_corregir) == 0

    def test_mix_textual_y_numerica_solo_textual_figura(self):
        """Triangulación: mezcla de escalas — solo textuales sin nota aparecen."""
        from app.services.calificacion_finalizacion import detectar_sin_corregir

        entrada_id = uuid.uuid4()
        finalizaciones = [
            {"entrada_padron_id": entrada_id, "actividad": "TP1", "escala": "numerica", "finalizado": True},
            {"entrada_padron_id": entrada_id, "actividad": "Proyecto", "escala": "textual", "finalizado": True},
        ]
        calificaciones = []

        sin_corregir = detectar_sin_corregir(finalizaciones, calificaciones)

        nombres = [s["actividad"] for s in sin_corregir]
        assert "TP1" not in nombres
        assert "Proyecto" in nombres
