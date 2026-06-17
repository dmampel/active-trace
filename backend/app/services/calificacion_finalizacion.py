"""Cruce del reporte de finalización con calificaciones importadas (C-10, D4).

Detecta "posibles trabajos sin corregir": actividades textuales finalizadas por el
alumno pero sin calificación registrada.

Reglas (spec §Importación del reporte de finalización):
- RN-07: entrega textual finalizada sin Calificacion → reportar como "sin corregir"
- RN-08: actividades de escala numérica se excluyen SIEMPRE (ausencia = no entregado)

Esta función es PURA: no hace I/O, no accede a DB. El Service la llama con datos
ya resueltos desde el repositorio.
"""

from __future__ import annotations

import uuid

from app.models.calificacion import Calificacion


def detectar_sin_corregir(
    finalizaciones: list[dict],
    calificaciones: list[Calificacion],
) -> list[dict]:
    """Detecta entregas textuales finalizadas sin calificación.

    Args:
        finalizaciones: Lista de dicts con keys:
            - entrada_padron_id: uuid.UUID
            - actividad: str
            - escala: "textual" | "numerica"
            - finalizado: bool
        calificaciones: Lista de Calificacion ya importadas (cualquier escala).

    Returns:
        Lista de dicts con los campos "entrada_padron_id" y "actividad"
        de las entregas sin corregir.
    """
    # Índice rápido: (entrada_padron_id, actividad) → tiene calificación
    calificadas: set[tuple] = {
        (cal.entrada_padron_id, cal.actividad)
        for cal in calificaciones
    }

    sin_corregir = []
    for fin in finalizaciones:
        # RN-08: excluir escalas numéricas
        if fin.get("escala") != "textual":
            continue
        # Solo finalizadas
        if not fin.get("finalizado"):
            continue
        # RN-07: sin calificación registrada
        key = (fin["entrada_padron_id"], fin["actividad"])
        if key not in calificadas:
            sin_corregir.append({
                "entrada_padron_id": fin["entrada_padron_id"],
                "actividad": fin["actividad"],
            })

    return sin_corregir
