"""Tests unitarios para PadronService._parse_xlsx y _parse_csv.

TDD Strict:
- Prueba los parsers en aislamiento (sin DB, sin dependencias async)
- Triangulación: happy path + columna faltante + archivo grande + columnas extra
"""
import io
import pathlib

import pytest

FIXTURES = pathlib.Path(__file__).parent.parent / "fixtures" / "padron"


# ── Fixtures helpers ──────────────────────────────────────────────────────────


def xlsx_bytes(filename: str) -> bytes:
    return (FIXTURES / filename).read_bytes()


def csv_bytes(filename: str) -> bytes:
    return (FIXTURES / filename).read_bytes()


# ── _parse_xlsx ───────────────────────────────────────────────────────────────


class TestParseXlsx:
    def test_happy_path_returns_rows(self):
        from app.services.padron_service import PadronService

        rows = PadronService._parse_xlsx(xlsx_bytes("padron_valido.xlsx"))

        assert len(rows) == 5
        assert rows[0]["nombre"] == "Juan"
        assert rows[0]["apellidos"] == "Pérez"
        assert rows[0]["email"] == "juan@test.com"

    def test_columnas_extra_ignoradas(self):
        from app.services.padron_service import PadronService

        rows = PadronService._parse_xlsx(xlsx_bytes("padron_valido.xlsx"))

        # La fixture tiene columna 'comision' y 'regional' — deben estar en el dict
        # pero no deben romper el parser
        assert "comision" in rows[0]

    def test_columna_faltante_raises_value_error(self):
        from app.services.padron_service import PadronService

        with pytest.raises(ValueError, match="email"):
            PadronService._parse_xlsx(xlsx_bytes("padron_sin_email.xlsx"))

    def test_archivo_grande_raises_too_large_error(self):
        from app.services.padron_service import PadronService, TooLargeError

        with pytest.raises(TooLargeError):
            PadronService._parse_xlsx(xlsx_bytes("padron_grande.xlsx"))


# ── _parse_csv ────────────────────────────────────────────────────────────────


class TestParseCsv:
    def test_happy_path_returns_rows(self):
        from app.services.padron_service import PadronService

        rows = PadronService._parse_csv(csv_bytes("padron_valido.csv"))

        assert len(rows) == 5
        assert rows[0]["nombre"] == "Juan"
        assert rows[0]["apellidos"] == "Pérez"
        assert rows[0]["email"] == "juan@test.com"

    def test_columnas_extra_ignoradas(self):
        from app.services.padron_service import PadronService

        rows = PadronService._parse_csv(csv_bytes("padron_valido.csv"))
        assert "comision" in rows[0]

    def test_columna_faltante_raises_value_error(self):
        from app.services.padron_service import PadronService

        bad_csv = b"nombre,apellidos\nJuan,Perez\n"
        with pytest.raises(ValueError, match="email"):
            PadronService._parse_csv(bad_csv)

    def test_csv_grande_raises_too_large_error(self):
        from app.services.padron_service import PadronService, TooLargeError

        # Generar CSV con 5001 filas de datos
        lines = ["nombre,apellidos,email"]
        for i in range(5001):
            lines.append(f"Nombre{i},Apellido{i},user{i}@test.com")
        big_csv = "\n".join(lines).encode("utf-8")

        with pytest.raises(TooLargeError):
            PadronService._parse_csv(big_csv)
