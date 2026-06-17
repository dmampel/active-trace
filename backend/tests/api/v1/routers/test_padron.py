"""Tests de integración para el router de padrón.

Patrón: TestClient + mocked get_current_user + patched RbacRepository.
El service se mockea para aislar la capa HTTP de la lógica de negocio.
"""
import io
import os
import pathlib
import uuid
from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5433/activia_trace_test")
os.environ.setdefault("TEST_DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5433/activia_trace_test")
os.environ.setdefault("SECRET_KEY", "a" * 64)
os.environ.setdefault("ENCRYPTION_KEY", "b" * 64)

from fastapi.testclient import TestClient

from app.main import app
from app.core.dependencies import get_current_user, get_db

TENANT_ID = uuid.uuid4()
USER_ID = uuid.uuid4()
MATERIA_ID = uuid.uuid4()

FIXTURES = pathlib.Path(__file__).parent.parent.parent.parent / "fixtures" / "padron"


def _make_user(user_id=None, tenant_id=None):
    user = MagicMock()
    user.id = user_id or USER_ID
    user.tenant_id = tenant_id or TENANT_ID
    user.impersonado_id = None
    return user


async def _fake_db():
    yield AsyncMock()


@contextmanager
def _client_with_perms(perms: list[str], user=None):
    app.dependency_overrides[get_current_user] = lambda: user or _make_user()
    app.dependency_overrides[get_db] = _fake_db
    target = "app.repositories.rbac_repository.RbacRepository.get_effective_permissions"
    with patch(target, new=AsyncMock(return_value=set(perms))):
        try:
            yield TestClient(app, raise_server_exceptions=False)
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_db, None)


# ── POST /{materia_id}/importar ───────────────────────────────────────────────


class TestImportarArchivo:
    def test_importar_xlsx_returns_201(self, monkeypatch):
        from app.schemas.padron import ImportarResultadoOut
        from app.services import padron_service as svc_mod

        version_id = uuid.uuid4()
        monkeypatch.setattr(
            svc_mod.PadronService, "importar_archivo",
            AsyncMock(return_value=ImportarResultadoOut(
                version_id=version_id, total_importado=5, activa=True
            )),
        )

        xlsx_bytes = (FIXTURES / "padron_valido.xlsx").read_bytes()

        with _client_with_perms(["padron:importar"]) as client:
            response = client.post(
                f"/api/v1/padron/{MATERIA_ID}/importar",
                files={"file": ("padron.xlsx", io.BytesIO(xlsx_bytes), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                data={"cohorte_id": str(uuid.uuid4())},
            )

        assert response.status_code == 201
        assert response.json()["total_importado"] == 5

    def test_importar_csv_returns_201(self, monkeypatch):
        from app.schemas.padron import ImportarResultadoOut
        from app.services import padron_service as svc_mod

        version_id = uuid.uuid4()
        monkeypatch.setattr(
            svc_mod.PadronService, "importar_archivo",
            AsyncMock(return_value=ImportarResultadoOut(
                version_id=version_id, total_importado=5, activa=True
            )),
        )

        csv_bytes = (FIXTURES / "padron_valido.csv").read_bytes()

        with _client_with_perms(["padron:importar"]) as client:
            response = client.post(
                f"/api/v1/padron/{MATERIA_ID}/importar",
                files={"file": ("padron.csv", io.BytesIO(csv_bytes), "text/csv")},
                data={"cohorte_id": str(uuid.uuid4())},
            )

        assert response.status_code == 201

    def test_sin_permiso_returns_403(self):
        with _client_with_perms([]) as client:
            response = client.post(
                f"/api/v1/padron/{MATERIA_ID}/importar",
                files={"file": ("padron.csv", io.BytesIO(b"nombre,apellidos,email\n"), "text/csv")},
                data={"cohorte_id": str(uuid.uuid4())},
            )

        assert response.status_code == 403

    def test_columna_faltante_returns_400(self, monkeypatch):
        from fastapi import HTTPException
        from app.services import padron_service as svc_mod

        monkeypatch.setattr(
            svc_mod.PadronService, "importar_archivo",
            AsyncMock(side_effect=HTTPException(status_code=400, detail="Columnas obligatorias faltantes: email")),
        )

        xlsx_bytes = (FIXTURES / "padron_sin_email.xlsx").read_bytes()

        with _client_with_perms(["padron:importar"]) as client:
            response = client.post(
                f"/api/v1/padron/{MATERIA_ID}/importar",
                files={"file": ("padron.xlsx", io.BytesIO(xlsx_bytes), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                data={"cohorte_id": str(uuid.uuid4())},
            )

        assert response.status_code == 400

    def test_archivo_grande_returns_413(self, monkeypatch):
        from fastapi import HTTPException
        from app.services import padron_service as svc_mod

        monkeypatch.setattr(
            svc_mod.PadronService, "importar_archivo",
            AsyncMock(side_effect=HTTPException(status_code=413, detail="Archivo demasiado grande")),
        )

        with _client_with_perms(["padron:importar"]) as client:
            response = client.post(
                f"/api/v1/padron/{MATERIA_ID}/importar",
                files={"file": ("big.xlsx", io.BytesIO(b"fake"), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                data={"cohorte_id": str(uuid.uuid4())},
            )

        assert response.status_code == 413


# ── GET /{materia_id}/activo ──────────────────────────────────────────────────


class TestGetActivo:
    def test_con_version_activa_returns_200(self, monkeypatch):
        from datetime import datetime, timezone
        from app.schemas.padron import VersionPadronDetalleOut
        from app.services import padron_service as svc_mod

        mock_response = VersionPadronDetalleOut(
            id=uuid.uuid4(),
            materia_id=MATERIA_ID,
            cohorte_id=uuid.uuid4(),
            cargado_por=USER_ID,
            cargado_at=datetime.now(timezone.utc),
            activa=True,
            entradas=[],
        )
        monkeypatch.setattr(
            svc_mod.PadronService, "get_activo",
            AsyncMock(return_value=mock_response),
        )

        with _client_with_perms(["padron:leer"]) as client:
            response = client.get(f"/api/v1/padron/{MATERIA_ID}/activo")

        assert response.status_code == 200

    def test_sin_version_activa_returns_404(self, monkeypatch):
        from fastapi import HTTPException
        from app.services import padron_service as svc_mod

        monkeypatch.setattr(
            svc_mod.PadronService, "get_activo",
            AsyncMock(side_effect=HTTPException(status_code=404, detail="Sin padrón activo")),
        )

        with _client_with_perms(["padron:leer"]) as client:
            response = client.get(f"/api/v1/padron/{MATERIA_ID}/activo")

        assert response.status_code == 404

    def test_sin_permiso_returns_403(self):
        with _client_with_perms([]) as client:
            response = client.get(f"/api/v1/padron/{MATERIA_ID}/activo")

        assert response.status_code == 403


# ── DELETE /{materia_id}/activo ───────────────────────────────────────────────


class TestVaciarPadron:
    def test_vaciar_propio_returns_204(self, monkeypatch):
        from app.services import padron_service as svc_mod

        monkeypatch.setattr(
            svc_mod.PadronService, "vaciar",
            AsyncMock(return_value=None),
        )

        with _client_with_perms(["padron:importar"]) as client:
            response = client.delete(
                f"/api/v1/padron/{MATERIA_ID}/activo",
                params={"cohorte_id": str(uuid.uuid4())},
            )

        assert response.status_code == 204

    def test_vaciar_otro_usuario_returns_403(self, monkeypatch):
        from fastapi import HTTPException
        from app.services import padron_service as svc_mod

        monkeypatch.setattr(
            svc_mod.PadronService, "vaciar",
            AsyncMock(side_effect=HTTPException(status_code=403, detail="RN-04")),
        )

        with _client_with_perms(["padron:importar"]) as client:
            response = client.delete(
                f"/api/v1/padron/{MATERIA_ID}/activo",
                params={"cohorte_id": str(uuid.uuid4())},
            )

        assert response.status_code == 403


# ── POST /{materia_id}/importar-moodle ────────────────────────────────────────


class TestImportarMoodle:
    def test_success_returns_201(self, monkeypatch):
        from app.schemas.padron import ImportarResultadoOut
        from app.services import padron_service as svc_mod

        version_id = uuid.uuid4()
        monkeypatch.setattr(
            svc_mod.PadronService, "importar_moodle",
            AsyncMock(return_value=ImportarResultadoOut(
                version_id=version_id, total_importado=10, activa=True
            )),
        )

        with _client_with_perms(["padron:importar"]) as client:
            response = client.post(
                f"/api/v1/padron/{MATERIA_ID}/importar-moodle",
                json={"course_id": 42, "cohorte_id": str(uuid.uuid4())},
            )

        assert response.status_code == 201

    def test_moodle_no_configurado_returns_422(self, monkeypatch):
        from fastapi import HTTPException
        from app.services import padron_service as svc_mod

        monkeypatch.setattr(
            svc_mod.PadronService, "importar_moodle",
            AsyncMock(side_effect=HTTPException(
                status_code=422, detail="Moodle no configurado para este tenant."
            )),
        )

        with _client_with_perms(["padron:importar"]) as client:
            response = client.post(
                f"/api/v1/padron/{MATERIA_ID}/importar-moodle",
                json={"course_id": 1, "cohorte_id": str(uuid.uuid4())},
            )

        assert response.status_code == 422

    def test_moodle_auth_error_returns_503(self, monkeypatch):
        from fastapi import HTTPException
        from app.services import padron_service as svc_mod

        monkeypatch.setattr(
            svc_mod.PadronService, "importar_moodle",
            AsyncMock(side_effect=HTTPException(
                status_code=503, detail="Error de autenticación con Moodle."
            )),
        )

        with _client_with_perms(["padron:importar"]) as client:
            response = client.post(
                f"/api/v1/padron/{MATERIA_ID}/importar-moodle",
                json={"course_id": 1, "cohorte_id": str(uuid.uuid4())},
            )

        assert response.status_code == 503


# ── Reemplazo de versión (RN-05) ──────────────────────────────────────────────


class TestReemplazarVersion:
    def test_segunda_importacion_desactiva_anterior(self, monkeypatch):
        """Smoke test: el endpoint retorna 201 en segunda importación (el repo garantiza la lógica)."""
        from app.schemas.padron import ImportarResultadoOut
        from app.services import padron_service as svc_mod

        version_id = uuid.uuid4()
        monkeypatch.setattr(
            svc_mod.PadronService, "importar_archivo",
            AsyncMock(return_value=ImportarResultadoOut(
                version_id=version_id, total_importado=3, activa=True
            )),
        )

        csv_bytes = b"nombre,apellidos,email\nJuan,Perez,j@t.com\n"

        with _client_with_perms(["padron:importar"]) as client:
            r1 = client.post(
                f"/api/v1/padron/{MATERIA_ID}/importar",
                files={"file": ("p.csv", io.BytesIO(csv_bytes), "text/csv")},
                data={"cohorte_id": str(uuid.uuid4())},
            )
            r2 = client.post(
                f"/api/v1/padron/{MATERIA_ID}/importar",
                files={"file": ("p.csv", io.BytesIO(csv_bytes), "text/csv")},
                data={"cohorte_id": str(uuid.uuid4())},
            )

        assert r1.status_code == 201
        assert r2.status_code == 201
