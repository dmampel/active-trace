"""Service de gestión del padrón de alumnos.

Responsabilidades:
- Parsear archivos xlsx/csv y validar columnas obligatorias
- Cifrar email de cada EntradaPadron (PII) antes de persistir
- Descifrar email al leer (get_activo)
- Coordinar importación desde archivo y desde Moodle WS
- Auditoría de eventos PADRON_IMPORTADO y PADRON_VACIADO

Regla crítica: el cifrado/descifrado de PII (email) ocurre SOLO aquí.
"""

import csv
import io
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import AES256GCMCipher, derive_encryption_key
from app.models.padron import EntradaPadron, VersionPadron
from app.models.tenant_moodle_config import TenantMoodleConfig
from app.repositories.moodle_config_repository import MoodleConfigRepository
from app.repositories.padron_repository import PadronRepository
from app.schemas.padron import (
    EntradaPadronOut,
    ImportarResultadoOut,
    VersionPadronDetalleOut,
    VersionPadronOut,
)


# ── Excepciones de dominio ────────────────────────────────────────────────────


class TooLargeError(Exception):
    """El archivo supera el límite de 5.000 filas."""


# ── Cipher singleton (lazy-initialized) ──────────────────────────────────────


_cipher: Optional[AES256GCMCipher] = None


def _get_cipher() -> AES256GCMCipher:
    """Retorna el cipher AES-256. Se inicializa al primer uso (no al importar el módulo)."""
    global _cipher
    if _cipher is None:
        _cipher = AES256GCMCipher(derive_encryption_key(get_settings().encryption_key))
    return _cipher

MAX_ROWS = 5_000
REQUIRED_COLUMNS = {"nombre", "apellidos", "email"}
OPTIONAL_COLUMNS = {"comision", "regional"}


# ── PadronService ─────────────────────────────────────────────────────────────


class PadronService:
    def __init__(self, session: AsyncSession, current_user, request=None):
        self.session = session
        self.current_user = current_user
        self.request = request
        self._repo = PadronRepository(session)
        self._moodle_repo = MoodleConfigRepository(session)

    # ── Parsers (métodos estáticos — sin async, testables en aislamiento) ─────

    @staticmethod
    def _parse_xlsx(file_bytes: bytes) -> list[dict]:
        """Parsea un archivo xlsx y retorna una lista de dicts.

        Columnas obligatorias: nombre, apellidos, email.
        Columnas adicionales son incluidas en el dict (tolerantes).

        Raises:
            ValueError: si falta alguna columna obligatoria.
            TooLargeError: si el archivo supera MAX_ROWS filas de datos.
        """
        import openpyxl

        wb = openpyxl.load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
        ws = wb.active

        rows_iter = ws.iter_rows(values_only=True)

        # Primera fila = cabecera
        try:
            header_row = next(rows_iter)
        except StopIteration:
            raise ValueError("Archivo xlsx vacío — no se encontró cabecera.")

        headers = [str(h).strip().lower() if h is not None else "" for h in header_row]

        # Validar columnas obligatorias
        missing = REQUIRED_COLUMNS - set(headers)
        if missing:
            raise ValueError(
                f"Columnas obligatorias faltantes: {', '.join(sorted(missing))}"
            )

        result: list[dict] = []
        for row in rows_iter:
            row_dict = {headers[i]: (str(v).strip() if v is not None else "") for i, v in enumerate(row)}
            # Saltar filas completamente vacías
            if not any(row_dict.get(col) for col in REQUIRED_COLUMNS):
                continue
            result.append(row_dict)
            if len(result) > MAX_ROWS:
                wb.close()
                raise TooLargeError(
                    f"El archivo supera el límite de {MAX_ROWS} filas."
                )

        wb.close()
        return result

    @staticmethod
    def _parse_csv(file_bytes: bytes) -> list[dict]:
        """Parsea un archivo CSV UTF-8 y retorna una lista de dicts.

        Columnas obligatorias: nombre, apellidos, email.
        Columnas adicionales son incluidas en el dict.

        Raises:
            ValueError: si falta alguna columna obligatoria.
            TooLargeError: si supera MAX_ROWS filas de datos.
        """
        text = file_bytes.decode("utf-8")
        reader = csv.DictReader(io.StringIO(text))

        if reader.fieldnames is None:
            raise ValueError("Archivo CSV vacío — no se encontró cabecera.")

        headers = {f.strip().lower() for f in reader.fieldnames if f}

        missing = REQUIRED_COLUMNS - headers
        if missing:
            raise ValueError(
                f"Columnas obligatorias faltantes: {', '.join(sorted(missing))}"
            )

        result: list[dict] = []
        for row in reader:
            normalized = {k.strip().lower(): v.strip() if v else "" for k, v in row.items() if k}
            if not any(normalized.get(col) for col in REQUIRED_COLUMNS):
                continue
            result.append(normalized)
            if len(result) > MAX_ROWS:
                raise TooLargeError(
                    f"El archivo supera el límite de {MAX_ROWS} filas."
                )

        return result

    # ── Lógica de importación ─────────────────────────────────────────────────

    def _rows_to_entradas(
        self, rows: list[dict], tenant_id: uuid.UUID
    ) -> list[EntradaPadron]:
        """Convierte filas parseadas a objetos EntradaPadron con email cifrado."""
        entradas = []
        for row in rows:
            email_plaintext = row.get("email", "")
            entrada = EntradaPadron(
                tenant_id=tenant_id,
                nombre=row.get("nombre", ""),
                apellidos=row.get("apellidos", ""),
                email_enc=_get_cipher().encrypt(email_plaintext),
                comision=row.get("comision") or None,
                regional=row.get("regional") or None,
            )
            entradas.append(entrada)
        return entradas

    async def importar_archivo(
        self,
        materia_id: uuid.UUID,
        cohorte_id: uuid.UUID,
        file_bytes: bytes,
        filename: str,
    ) -> ImportarResultadoOut:
        """Importa padrón desde archivo xlsx o csv.

        Raises:
            HTTPException 400: si faltan columnas obligatorias o el archivo es inválido.
            HTTPException 413: si el archivo supera 5.000 filas.
        """
        ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""

        try:
            if ext in ("xlsx", "xls"):
                rows = self._parse_xlsx(file_bytes)
            elif ext == "csv":
                rows = self._parse_csv(file_bytes)
            else:
                # Fallback: intentar CSV
                try:
                    rows = self._parse_csv(file_bytes)
                except Exception:
                    rows = self._parse_xlsx(file_bytes)
        except TooLargeError as exc:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=str(exc),
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Archivo inválido o no soportado: {exc}",
            )

        tenant_id = self.current_user.tenant_id
        version = VersionPadron(
            tenant_id=tenant_id,
            materia_id=materia_id,
            cohorte_id=cohorte_id,
            cargado_por=self.current_user.id,
            cargado_at=datetime.now(timezone.utc),
            activa=True,
        )
        entradas = self._rows_to_entradas(rows, tenant_id)
        saved = await self._repo.crear_version_con_entradas(version, entradas)

        # Auditoría
        from app.core.audit import record_audit
        await record_audit(
            self.session,
            self.current_user,
            "PADRON_IMPORTADO",
            request=self.request,
            detail={
                "version_id": str(saved.id),
                "total_entradas": len(rows),
                "fuente": "archivo",
            },
            materia_id=materia_id,
        )

        return ImportarResultadoOut(
            version_id=saved.id,
            total_importado=len(rows),
            activa=saved.activa,
        )

    async def importar_moodle(
        self,
        materia_id: uuid.UUID,
        cohorte_id: uuid.UUID,
        course_id: int,
    ) -> ImportarResultadoOut:
        """Importa padrón desde Moodle Web Services.

        Raises:
            HTTPException 422: si el tenant no tiene config Moodle.
            HTTPException 503: si Moodle devuelve error de auth o timeout.
        """
        from app.integrations.moodle_ws import MoodleAuthError, MoodleUnavailableError, MoodleWSClient

        tenant_id = self.current_user.tenant_id
        config = await self._moodle_repo.get_by_tenant(tenant_id)
        if config is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Moodle no configurado para este tenant.",
            )

        moodle_url = _get_cipher().decrypt(config.moodle_url_enc)
        moodle_token = _get_cipher().decrypt(config.moodle_token_enc)

        try:
            client = MoodleWSClient(moodle_url=moodle_url, token=moodle_token)
            rows = await client.get_course_participants(course_id)
        except MoodleAuthError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Error de autenticación con Moodle. Verificar token.",
            )
        except MoodleUnavailableError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Moodle no disponible. Intentar más tarde.",
            )

        version = VersionPadron(
            tenant_id=tenant_id,
            materia_id=materia_id,
            cohorte_id=cohorte_id,
            cargado_por=self.current_user.id,
            cargado_at=datetime.now(timezone.utc),
            activa=True,
        )
        entradas = self._rows_to_entradas(rows, tenant_id)
        saved = await self._repo.crear_version_con_entradas(version, entradas)

        # Auditoría
        from app.core.audit import record_audit
        await record_audit(
            self.session,
            self.current_user,
            "PADRON_IMPORTADO",
            request=self.request,
            detail={
                "version_id": str(saved.id),
                "total_entradas": len(rows),
                "fuente": "moodle",
                "course_id": course_id,
            },
            materia_id=materia_id,
        )

        return ImportarResultadoOut(
            version_id=saved.id,
            total_importado=len(rows),
            activa=saved.activa,
        )

    async def get_activo(
        self,
        materia_id: uuid.UUID,
    ) -> VersionPadronDetalleOut:
        """Retorna la versión activa del padrón con entradas (email descifrado).

        Raises:
            HTTPException 404: si no hay versión activa.
        """
        tenant_id = self.current_user.tenant_id

        # Obtener versión activa (sin cohorte_id para simplificar la lectura —
        # devuelve la última activa de cualquier cohorte para esta materia)
        from sqlalchemy import select

        q = (
            select(VersionPadron)
            .where(
                VersionPadron.tenant_id == tenant_id,
                VersionPadron.materia_id == materia_id,
                VersionPadron.activa.is_(True),
                VersionPadron.deleted_at.is_(None),
            )
            .order_by(VersionPadron.cargado_at.desc())
            .limit(1)
        )
        result = await self.session.execute(q)
        version = result.scalar_one_or_none()

        if version is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sin padrón activo para esta materia.",
            )

        entradas_raw = await self._repo.get_entradas(version.id, tenant_id)

        entradas_out = [
            EntradaPadronOut(
                id=e.id,
                nombre=e.nombre,
                apellidos=e.apellidos,
                email=_get_cipher().decrypt(e.email_enc),
                comision=e.comision,
                regional=e.regional,
                usuario_id=e.usuario_id,
            )
            for e in entradas_raw
        ]

        return VersionPadronDetalleOut(
            id=version.id,
            materia_id=version.materia_id,
            cohorte_id=version.cohorte_id,
            cargado_por=version.cargado_por,
            cargado_at=version.cargado_at,
            activa=version.activa,
            entradas=entradas_out,
        )

    async def listar_versiones(
        self,
        materia_id: uuid.UUID,
    ) -> list[VersionPadronOut]:
        """Lista todas las versiones (activas e inactivas) de una materia."""
        tenant_id = self.current_user.tenant_id
        versions = await self._repo.listar_versiones(materia_id, tenant_id)

        result = []
        for v in versions:
            # Contar entradas sin cargar todas en memoria
            from sqlalchemy import func, select
            from app.models.padron import EntradaPadron as EP

            count_q = select(func.count()).where(EP.version_id == v.id)
            count_result = await self.session.execute(count_q)
            total = count_result.scalar_one()

            result.append(
                VersionPadronOut(
                    id=v.id,
                    materia_id=v.materia_id,
                    cohorte_id=v.cohorte_id,
                    cargado_por=v.cargado_por,
                    cargado_at=v.cargado_at,
                    activa=v.activa,
                    total_entradas=total,
                )
            )
        return result

    async def vaciar(
        self,
        materia_id: uuid.UUID,
        cohorte_id: uuid.UUID,
    ) -> None:
        """Vacía el padrón activo (soft-delete) si fue cargado por el usuario en sesión.

        Raises:
            HTTPException 404: si no hay versión activa.
            HTTPException 403: si la versión fue cargada por otro usuario.
        """
        tenant_id = self.current_user.tenant_id
        usuario_id = self.current_user.id

        version = await self._repo.soft_delete_activa(
            materia_id=materia_id,
            cohorte_id=cohorte_id,
            tenant_id=tenant_id,
            cargado_por=usuario_id,
        )

        if version is None:
            # Verificar si existe una versión de otro usuario para dar 403 vs 404
            existing = await self._repo.get_activa(materia_id, cohorte_id, tenant_id)
            if existing is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Sin padrón activo para esta materia.",
                )
            # Existe pero fue cargada por otro usuario
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo el usuario que cargó el padrón puede vaciarlo (RN-04).",
            )

        # Auditoría
        from app.core.audit import record_audit
        await record_audit(
            self.session,
            self.current_user,
            "PADRON_VACIADO",
            request=self.request,
            detail={
                "version_id": str(version.id),
                "materia_id": str(materia_id),
            },
            materia_id=materia_id,
        )

    async def upsert_moodle_config(
        self,
        moodle_url: str,
        moodle_token: str,
    ) -> None:
        """Guarda la configuración Moodle del tenant (cifrada)."""
        tenant_id = self.current_user.tenant_id
        config = TenantMoodleConfig(
            tenant_id=tenant_id,
            moodle_url_enc=_get_cipher().encrypt(moodle_url),
            moodle_token_enc=_get_cipher().encrypt(moodle_token),
        )
        await self._moodle_repo.upsert(config, tenant_id)
