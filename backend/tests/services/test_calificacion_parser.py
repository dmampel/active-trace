"""Tests TDD para el parser de calificaciones del LMS (C-10 — Tareas 4.1–4.7).

Testa el parsing puro en aislamiento: sin DB, sin fixtures async.
Reglas del dominio (RN-01, RN-02, D3 del design.md):
- Columna numérica: encabezado termina en '(Real)'
- Columna textual: celdas con valores de la escala cualitativa configurada
- preview() no escribe ninguna Calificacion
- import persiste solo las actividades seleccionadas
"""

import io
import uuid
from datetime import datetime, timezone

import pytest

# Escala textual de prueba
ESCALA_TEXTUAL = ["Satisfactorio", "Supera lo esperado", "No satisfactorio", "No alcanzado"]


def _build_csv(rows: list[list[str]]) -> bytes:
    """Construye bytes CSV desde una lista de filas."""
    content = "\n".join(",".join(row) for row in rows)
    return content.encode("utf-8")


# ── Detección de columnas numéricas (RN-01) ────────────────────────────────────


class TestDeteccionColumnasNumericas:
    def test_columna_con_sufijo_real_es_numerica(self):
        """RN-01: encabezado 'TP1 (Real)' → actividad numérica 'TP1'."""
        from app.services.calificacion_parser import detectar_actividades

        encabezados = ["Nombre", "Email", "TP1 (Real)", "Comentarios"]
        actividades = detectar_actividades(encabezados, ESCALA_TEXTUAL)

        nombres = [a["nombre"] for a in actividades]
        escalas = {a["nombre"]: a["escala"] for a in actividades}

        assert "TP1" in nombres
        assert escalas["TP1"] == "numerica"

    def test_columna_sin_sufijo_real_no_es_numerica(self):
        """RN-01 inverso: 'Comentarios' no tiene sufijo (Real) → no es numérica."""
        from app.services.calificacion_parser import detectar_actividades

        encabezados = ["Nombre", "Email", "Comentarios", "TP1 (Real)"]
        actividades = detectar_actividades(encabezados, ESCALA_TEXTUAL)

        nombres = [a["nombre"] for a in actividades]
        assert "Comentarios" not in nombres

    def test_multiples_columnas_numericas(self):
        """Triangulación: varios '(Real)' se detectan todos."""
        from app.services.calificacion_parser import detectar_actividades

        encabezados = ["Nombre", "Email", "TP1 (Real)", "TP2 (Real)", "Final (Real)"]
        actividades = detectar_actividades(encabezados, ESCALA_TEXTUAL)

        nombres_num = [a["nombre"] for a in actividades if a["escala"] == "numerica"]
        assert set(nombres_num) == {"TP1", "TP2", "Final"}

    def test_columna_metadata_ignorada(self):
        """Columnas de metadatos (Nombre, Email, etc.) no son actividades."""
        from app.services.calificacion_parser import detectar_actividades

        encabezados = ["Nombre", "Apellidos", "Email", "DNI", "TP1 (Real)"]
        actividades = detectar_actividades(encabezados, ESCALA_TEXTUAL)

        nombres = [a["nombre"] for a in actividades]
        assert "Nombre" not in nombres
        assert "Apellidos" not in nombres
        assert "Email" not in nombres
        assert "DNI" not in nombres


# ── Detección de columnas textuales (RN-02) ────────────────────────────────────


class TestDeteccionColumnasTextuales:
    def test_columna_con_valores_de_escala_es_textual(self):
        """RN-02: columna con celda 'Satisfactorio' → textual."""
        from app.services.calificacion_parser import detectar_actividades_en_filas

        encabezados = ["Nombre", "Email", "Trabajo Integrador"]
        filas = [
            {"Nombre": "Ana", "Email": "ana@test.com", "Trabajo Integrador": "Satisfactorio"},
            {"Nombre": "Luis", "Email": "luis@test.com", "Trabajo Integrador": "No satisfactorio"},
        ]
        actividades = detectar_actividades_en_filas(encabezados, filas, ESCALA_TEXTUAL)

        nombres = [a["nombre"] for a in actividades if a["escala"] == "textual"]
        assert "Trabajo Integrador" in nombres

    def test_columna_sin_valores_de_escala_no_es_textual(self):
        """Triangulación: columna con texto libre no es textual."""
        from app.services.calificacion_parser import detectar_actividades_en_filas

        encabezados = ["Nombre", "Email", "Observaciones"]
        filas = [
            {"Nombre": "Ana", "Email": "ana@test.com", "Observaciones": "Muy buen alumno"},
        ]
        actividades = detectar_actividades_en_filas(encabezados, filas, ESCALA_TEXTUAL)

        nombres = [a["nombre"] for a in actividades]
        assert "Observaciones" not in nombres

    def test_columna_vacia_no_es_textual(self):
        """Columna vacía no se interpreta como textual."""
        from app.services.calificacion_parser import detectar_actividades_en_filas

        encabezados = ["Nombre", "Email", "TP Pendiente"]
        filas = [
            {"Nombre": "Ana", "Email": "ana@test.com", "TP Pendiente": ""},
            {"Nombre": "Luis", "Email": "luis@test.com", "TP Pendiente": None},
        ]
        actividades = detectar_actividades_en_filas(encabezados, filas, ESCALA_TEXTUAL)

        nombres = [a["nombre"] for a in actividades]
        assert "TP Pendiente" not in nombres


# ── Preview: no escribe en DB (Tarea 4.4) ────────────────────────────────────


class TestPreviewNoPersiste:
    def test_parsear_preview_retorna_estructura_sin_objetos_orm(self):
        """preview() retorna dicts planos — sin instancias SQLAlchemy."""
        from app.services.calificacion_parser import parsear_csv_preview

        csv_data = _build_csv([
            ["Nombre", "Email", "TP1 (Real)", "Trabajo Final"],
            ["Ana García", "ana@test.com", "8", "Satisfactorio"],
            ["Luis Pérez", "luis@test.com", "6", "No satisfactorio"],
        ])

        resultado = parsear_csv_preview(csv_data, ESCALA_TEXTUAL)

        assert "actividades" in resultado
        assert "filas" in resultado
        # No hay instancias de Calificacion en el resultado
        from app.models.calificacion import Calificacion
        for fila in resultado["filas"]:
            assert not isinstance(fila, Calificacion)

    def test_preview_detecta_actividades_mixtas(self):
        """Preview detecta actividades numéricas y textuales en el mismo archivo."""
        from app.services.calificacion_parser import parsear_csv_preview

        csv_data = _build_csv([
            ["Nombre", "Email", "TP1 (Real)", "Trabajo Final"],
            ["Ana García", "ana@test.com", "8", "Satisfactorio"],
        ])

        resultado = parsear_csv_preview(csv_data, ESCALA_TEXTUAL)
        actividades = resultado["actividades"]

        escalas = {a["nombre"]: a["escala"] for a in actividades}
        assert "TP1" in escalas
        assert escalas["TP1"] == "numerica"
        assert "Trabajo Final" in escalas
        assert escalas["Trabajo Final"] == "textual"


# ── Importar solo actividades seleccionadas (Tarea 4.5) ──────────────────────


class TestImportarActividadesSeleccionadas:
    def test_importar_2_de_3_actividades(self):
        """Dado 3 actividades, seleccionar 2 → solo esas 2 generan Calificacion."""
        from app.services.calificacion_parser import construir_calificaciones

        materia_id = uuid.uuid4()
        tenant_id = uuid.uuid4()
        entrada_id_1 = uuid.uuid4()
        entrada_id_2 = uuid.uuid4()

        # Simulamos el resultado del preview — actividades detectadas
        actividades = [
            {"nombre": "TP1", "escala": "numerica", "columna_csv": "TP1 (Real)"},
            {"nombre": "TP2", "escala": "numerica", "columna_csv": "TP2 (Real)"},
            {"nombre": "Final", "escala": "textual", "columna_csv": "Final"},
        ]
        # Solo seleccionamos TP1 y Final
        seleccionadas = ["TP1", "Final"]

        filas = [
            {
                "entrada_padron_id": entrada_id_1,
                "TP1 (Real)": "8",
                "TP2 (Real)": "7",
                "Final": "Satisfactorio",
            },
            {
                "entrada_padron_id": entrada_id_2,
                "TP1 (Real)": "6",
                "TP2 (Real)": "9",
                "Final": "No satisfactorio",
            },
        ]

        cals = construir_calificaciones(
            filas=filas,
            actividades=actividades,
            seleccionadas=seleccionadas,
            materia_id=materia_id,
            tenant_id=tenant_id,
            importado_at=datetime.now(timezone.utc),
        )

        # 2 alumnos × 2 actividades seleccionadas = 4 calificaciones
        assert len(cals) == 4
        actividades_generadas = {c.actividad for c in cals}
        assert actividades_generadas == {"TP1", "Final"}
        assert "TP2" not in actividades_generadas

    def test_nota_textual_vs_numerica_mapea_correctamente(self):
        """Triangulación: nota numérica → nota_numerica; textual → nota_textual."""
        from app.services.calificacion_parser import construir_calificaciones

        materia_id = uuid.uuid4()
        tenant_id = uuid.uuid4()
        entrada_id = uuid.uuid4()

        actividades = [
            {"nombre": "TP1", "escala": "numerica", "columna_csv": "TP1 (Real)"},
            {"nombre": "Proyecto", "escala": "textual", "columna_csv": "Proyecto"},
        ]
        seleccionadas = ["TP1", "Proyecto"]
        filas = [{
            "entrada_padron_id": entrada_id,
            "TP1 (Real)": "7.5",
            "Proyecto": "Satisfactorio",
        }]

        cals = construir_calificaciones(
            filas=filas,
            actividades=actividades,
            seleccionadas=seleccionadas,
            materia_id=materia_id,
            tenant_id=tenant_id,
            importado_at=datetime.now(timezone.utc),
        )

        tp1 = next(c for c in cals if c.actividad == "TP1")
        proyecto = next(c for c in cals if c.actividad == "Proyecto")

        assert tp1.nota_numerica == 7.5
        assert tp1.nota_textual is None
        assert proyecto.nota_numerica is None
        assert proyecto.nota_textual == "Satisfactorio"

    def test_fila_con_nota_vacia_genera_calificacion_sin_nota(self):
        """Triangulación: celda vacía → nota_numerica=None y nota_textual=None."""
        from app.services.calificacion_parser import construir_calificaciones

        materia_id = uuid.uuid4()
        tenant_id = uuid.uuid4()
        entrada_id = uuid.uuid4()

        actividades = [
            {"nombre": "TP1", "escala": "numerica", "columna_csv": "TP1 (Real)"},
        ]
        seleccionadas = ["TP1"]
        filas = [{"entrada_padron_id": entrada_id, "TP1 (Real)": ""}]

        cals = construir_calificaciones(
            filas=filas,
            actividades=actividades,
            seleccionadas=seleccionadas,
            materia_id=materia_id,
            tenant_id=tenant_id,
            importado_at=datetime.now(timezone.utc),
        )

        # Fila vacía aún genera una Calificacion (sin nota)
        assert len(cals) == 1
        assert cals[0].nota_numerica is None
        assert cals[0].nota_textual is None
