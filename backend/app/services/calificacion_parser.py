"""Parser puro para archivos de calificaciones del LMS (C-10, D3).

Responsabilidades de este módulo:
- Detectar columnas numéricas (sufijo '(Real)') y textuales (escala configurada).
- Generar la estructura de preview (actividades + filas) sin persistir.
- Construir instancias de Calificacion para las actividades seleccionadas.

NO hace I/O de red, NO accede a DB, NO tiene lógica de RBAC.
Es puro parsing — el Service lo llama y maneja la persistencia.

Columnas de metadatos ignoradas como actividades (RN-01):
Toda columna que no tenga sufijo '(Real)' ni valores de escala en sus celdas.
Las columnas de identificación (Nombre, Apellidos, Email, DNI, etc.) quedan
naturalmente excluidas porque no cumplen ninguna de las dos condiciones.
"""

from __future__ import annotations

import csv
import io
import uuid
from datetime import datetime
from typing import Optional

from app.models.calificacion import Calificacion, OrigenCalificacion

# Columnas de identificación del alumno — nunca son actividades
_COLS_METADATA = frozenset({
    "nombre", "apellidos", "email", "dni", "legajo",
    "comision", "regional", "id", "usuario",
})

_SUFIJO_NUMERICO = "(Real)"


def detectar_actividades(
    encabezados: list[str],
    escala_textual: list[str],
) -> list[dict]:
    """Detecta actividades numéricas desde los encabezados (solo sufijo (Real)).

    Retorna lista de dicts con keys: nombre, escala, columna_csv.
    No detecta textuales — para eso usar detectar_actividades_en_filas (necesita datos).
    """
    actividades = []
    for col in encabezados:
        col_lower = col.strip().lower()
        if col_lower in _COLS_METADATA:
            continue
        if col.strip().endswith(_SUFIJO_NUMERICO):
            nombre = col.strip()[: -len(_SUFIJO_NUMERICO)].strip()
            actividades.append({
                "nombre": nombre,
                "escala": "numerica",
                "columna_csv": col.strip(),
            })
    return actividades


def detectar_actividades_en_filas(
    encabezados: list[str],
    filas: list[dict],
    escala_textual: list[str],
) -> list[dict]:
    """Detecta actividades numéricas Y textuales analizando encabezados + celdas.

    Una columna es textual si al menos una celda de sus filas tiene un valor
    que pertenece a la escala configurada (escala_textual).
    """
    escala_set = set(escala_textual)
    actividades: list[dict] = []
    ya_vistas: set[str] = set()

    for col in encabezados:
        col_lower = col.strip().lower()
        if col_lower in _COLS_METADATA:
            continue
        col_key = col.strip()

        if col_key.endswith(_SUFIJO_NUMERICO):
            nombre = col_key[: -len(_SUFIJO_NUMERICO)].strip()
            if nombre not in ya_vistas:
                ya_vistas.add(nombre)
                actividades.append({
                    "nombre": nombre,
                    "escala": "numerica",
                    "columna_csv": col_key,
                })
            continue

        # Comprobar si alguna celda de esta columna tiene valor de escala textual
        tiene_textual = any(
            str(fila.get(col_key) or "").strip() in escala_set
            for fila in filas
            if fila.get(col_key)
        )
        if tiene_textual and col_key not in ya_vistas:
            ya_vistas.add(col_key)
            actividades.append({
                "nombre": col_key,
                "escala": "textual",
                "columna_csv": col_key,
            })

    return actividades


def parsear_csv_preview(
    contenido: bytes,
    escala_textual: list[str],
) -> dict:
    """Parsea un CSV del LMS y retorna la estructura de preview sin persistir.

    Retorna:
        {
            "actividades": [{"nombre": str, "escala": "numerica"|"textual", "columna_csv": str}],
            "filas": [dict — una por alumno, con las notas como strings],
        }
    """
    reader = csv.DictReader(io.StringIO(contenido.decode("utf-8")))
    encabezados = reader.fieldnames or []
    filas = list(reader)

    actividades = detectar_actividades_en_filas(
        list(encabezados), filas, escala_textual
    )

    return {
        "actividades": actividades,
        "filas": filas,
    }


def construir_calificaciones(
    filas: list[dict],
    actividades: list[dict],
    seleccionadas: list[str],
    materia_id: uuid.UUID,
    tenant_id: uuid.UUID,
    importado_at: datetime,
) -> list[Calificacion]:
    """Construye instancias de Calificacion para las actividades seleccionadas.

    No persiste — retorna la lista lista para que el Service haga bulk_crear.

    Args:
        filas: Filas del CSV/preview. Cada fila debe tener 'entrada_padron_id'.
        actividades: Lista completa de actividades detectadas en el preview.
        seleccionadas: Nombres de actividades que el usuario eligió importar.
        materia_id: UUID de la materia (del JWT/contexto, no de la fila).
        tenant_id: UUID del tenant (del JWT).
        importado_at: Timestamp de la importación.

    Returns:
        Lista de Calificacion sin persistir.
    """
    sel_set = set(seleccionadas)
    actividades_filtradas = [a for a in actividades if a["nombre"] in sel_set]
    resultado: list[Calificacion] = []

    for fila in filas:
        entrada_padron_id: uuid.UUID = fila["entrada_padron_id"]
        for act in actividades_filtradas:
            columna_csv = act["columna_csv"]
            valor_raw = str(fila.get(columna_csv) or "").strip()

            nota_numerica: Optional[float] = None
            nota_textual: Optional[str] = None

            if act["escala"] == "numerica":
                if valor_raw:
                    try:
                        nota_numerica = float(valor_raw)
                    except ValueError:
                        nota_numerica = None
            else:
                nota_textual = valor_raw if valor_raw else None

            cal = Calificacion(
                entrada_padron_id=entrada_padron_id,
                materia_id=materia_id,
                actividad=act["nombre"],
                nota_numerica=nota_numerica,
                nota_textual=nota_textual,
                origen=OrigenCalificacion.IMPORTADO,
                importado_at=importado_at,
                tenant_id=tenant_id,
            )
            resultado.append(cal)

    return resultado
