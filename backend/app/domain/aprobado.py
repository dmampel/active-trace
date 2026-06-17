"""Derivación pura del estado aprobado (C-10, D2).

Esta función NO tiene I/O, NO accede a la base de datos, NO importa SQLAlchemy.
Es una función de dominio pura: determinística, testeable en aislamiento total.

Reglas (spec §Derivación determinística del estado aprobado):
1. Si existe nota_numerica → aprobado = nota_numerica >= (umbral_pct / 100) * nota_maxima
2. Si solo existe nota_textual → aprobado = nota_textual ∈ valores_aprobatorios
3. Cuando coexisten ambas → la nota numérica tiene precedencia (fuente cuantitativa primaria)
4. Sin ninguna nota → False (sin nota = no aprobado a efectos de seguimiento)

El Service es responsable de resolver:
- el umbral vigente (UmbralMateria de la asignación, o defecto del tenant = 60%)
- la nota_maxima (del export del LMS, o default 10.0)

Y luego llamar a esta función con esos valores resueltos.
"""

from __future__ import annotations

DEFAULT_UMBRAL_PCT: int = 60
DEFAULT_NOTA_MAXIMA: float = 10.0


def derivar_aprobado(
    nota_numerica: float | None,
    nota_textual: str | None,
    umbral_pct: int,
    nota_maxima: float,
    valores_aprobatorios: list[str],
) -> bool:
    """Deriva si una calificación es aprobatoria según las reglas de dominio.

    Args:
        nota_numerica: Nota cuantitativa (ej. 7.5). None si no aplica.
        nota_textual: Nota cualitativa (ej. "Satisfactorio"). None si no aplica.
        umbral_pct: Umbral de aprobación en porcentaje (ej. 60 para 60%).
        nota_maxima: Escala máxima posible (ej. 10.0).
        valores_aprobatorios: Lista de valores textuales que representan aprobación.

    Returns:
        True si la calificación es aprobatoria, False en caso contrario.
    """
    # Regla 1 y 3: la nota numérica tiene precedencia cuando está presente
    if nota_numerica is not None:
        umbral_minimo = (umbral_pct / 100.0) * nota_maxima
        return nota_numerica >= umbral_minimo

    # Regla 2: solo textual
    if nota_textual is not None:
        return nota_textual in valores_aprobatorios

    # Regla 4: sin nota
    return False
