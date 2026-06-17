"""Tests TDD para derivar_aprobado — función pura de dominio (C-10).

Cobertura ≥90% de la regla de negocio. Sin I/O, sin DB, sin fixtures async.
Cada scenario del spec tiene al menos un test; la triangulación cubre límites y precedencias.

Reglas (D2 del design.md):
1. Si nota_numerica presente → aprobado = nota_numerica >= (umbral_pct/100) * nota_maxima
2. Si solo nota_textual → aprobado = nota_textual ∈ valores_aprobatorios
3. Cuando coexisten ambas → numérica tiene precedencia
4. Sin ninguna nota → False
"""

import pytest
from app.domain.aprobado import derivar_aprobado

APROBATORIOS = ["Satisfactorio", "Supera lo esperado"]


# ── Numérica ──────────────────────────────────────────────────────────────────


def test_numerica_por_encima_del_umbral_aprueba():
    """Scenario spec: 7/10 con umbral 60% → true (7 >= 6.0)."""
    assert derivar_aprobado(
        nota_numerica=7.0,
        nota_textual=None,
        umbral_pct=60,
        nota_maxima=10.0,
        valores_aprobatorios=APROBATORIOS,
    ) is True


def test_numerica_en_limite_exacto_aprueba():
    """Scenario spec: 6/10 con umbral 60% → true (límite inclusivo)."""
    assert derivar_aprobado(
        nota_numerica=6.0,
        nota_textual=None,
        umbral_pct=60,
        nota_maxima=10.0,
        valores_aprobatorios=APROBATORIOS,
    ) is True


def test_numerica_por_debajo_del_umbral_no_aprueba():
    """Scenario spec: 5/10 con umbral 60% → false."""
    assert derivar_aprobado(
        nota_numerica=5.0,
        nota_textual=None,
        umbral_pct=60,
        nota_maxima=10.0,
        valores_aprobatorios=APROBATORIOS,
    ) is False


def test_numerica_nota_maxima_diferente():
    """Triangulación: 7/20 con umbral 60% → 7 < 12 → false."""
    assert derivar_aprobado(
        nota_numerica=7.0,
        nota_textual=None,
        umbral_pct=60,
        nota_maxima=20.0,
        valores_aprobatorios=APROBATORIOS,
    ) is False


def test_numerica_umbral_alto():
    """Triangulación: 8/10 con umbral 90% → false."""
    assert derivar_aprobado(
        nota_numerica=8.0,
        nota_textual=None,
        umbral_pct=90,
        nota_maxima=10.0,
        valores_aprobatorios=APROBATORIOS,
    ) is False


# ── Textual ───────────────────────────────────────────────────────────────────


def test_textual_en_conjunto_aprobatorio_aprueba():
    """Scenario spec: 'Satisfactorio' ∈ valores_aprobatorios → true."""
    assert derivar_aprobado(
        nota_numerica=None,
        nota_textual="Satisfactorio",
        umbral_pct=60,
        nota_maxima=10.0,
        valores_aprobatorios=APROBATORIOS,
    ) is True


def test_textual_supera_lo_esperado_aprueba():
    """Triangulación: segundo valor del conjunto aprobatorio."""
    assert derivar_aprobado(
        nota_numerica=None,
        nota_textual="Supera lo esperado",
        umbral_pct=60,
        nota_maxima=10.0,
        valores_aprobatorios=APROBATORIOS,
    ) is True


def test_textual_fuera_del_conjunto_no_aprueba():
    """Scenario spec: 'No satisfactorio' ∉ valores_aprobatorios → false."""
    assert derivar_aprobado(
        nota_numerica=None,
        nota_textual="No satisfactorio",
        umbral_pct=60,
        nota_maxima=10.0,
        valores_aprobatorios=APROBATORIOS,
    ) is False


def test_textual_conjunto_vacio_no_aprueba():
    """Triangulación: sin valores aprobatorios definidos → false."""
    assert derivar_aprobado(
        nota_numerica=None,
        nota_textual="Satisfactorio",
        umbral_pct=60,
        nota_maxima=10.0,
        valores_aprobatorios=[],
    ) is False


# ── Precedencia numérica sobre textual ───────────────────────────────────────


def test_precedencia_numerica_sobre_textual_reprueba():
    """Scenario spec: 5/10 (umbral 60%) + 'Satisfactorio' → false (numérica gana)."""
    assert derivar_aprobado(
        nota_numerica=5.0,
        nota_textual="Satisfactorio",
        umbral_pct=60,
        nota_maxima=10.0,
        valores_aprobatorios=APROBATORIOS,
    ) is False


def test_precedencia_numerica_sobre_textual_aprueba():
    """Triangulación inversa: 7/10 + 'No satisfactorio' → true (numérica gana)."""
    assert derivar_aprobado(
        nota_numerica=7.0,
        nota_textual="No satisfactorio",
        umbral_pct=60,
        nota_maxima=10.0,
        valores_aprobatorios=APROBATORIOS,
    ) is True


# ── Sin nota ──────────────────────────────────────────────────────────────────


def test_sin_nota_no_aprueba():
    """Scenario spec: sin nota_numerica ni nota_textual → false."""
    assert derivar_aprobado(
        nota_numerica=None,
        nota_textual=None,
        umbral_pct=60,
        nota_maxima=10.0,
        valores_aprobatorios=APROBATORIOS,
    ) is False


def test_textual_none_y_numerica_none_son_equivalentes():
    """Triangulación: ambas None explícitas → false."""
    result = derivar_aprobado(
        nota_numerica=None,
        nota_textual=None,
        umbral_pct=70,
        nota_maxima=20.0,
        valores_aprobatorios=["A", "B"],
    )
    assert result is False
