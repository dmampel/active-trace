"""Service de gestión de usuarios.

Responsabilidades:
- Cifrado/descifrado de PII (DNI, CUIL, CBU, alias_cbu) con AES256GCMCipher
- Unicidad de email por tenant (409 si duplicado)
- Mapeo a DTO de listado (sin PII) vs detalle (con PII descifrada)
- Cascada de cierre de asignaciones al desactivar usuario

Regla crítica: el cifrado/descifrado de PII ocurre SOLO aquí — nunca en
Repository ni Model. Las columnas *_enc nunca aparecen en logs.
"""
import uuid
from datetime import date
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import ASIGNACION_MODIFICAR, record_audit
from app.core.config import get_settings
from app.core.security import AES256GCMCipher


# ── Cipher singleton (clave de configuración) ─────────────────────────────────

def _build_cipher() -> AES256GCMCipher:
    key_hex = get_settings().encryption_key
    # La clave se almacena como hex (min 64 chars = 32 bytes). Tomamos los primeros 32 bytes.
    key_bytes = bytes.fromhex(key_hex[:64])
    return AES256GCMCipher(key_bytes)


_cipher: AES256GCMCipher = _build_cipher()


# ── Helpers de PII ────────────────────────────────────────────────────────────

def encrypt_pii(value: Optional[str]) -> Optional[str]:
    """Cifra un valor PII. Retorna None si value es None.

    No loguea el valor en texto plano en ningún caso.
    """
    if value is None:
        return None
    return _cipher.encrypt(value)


def decrypt_pii(ciphertext: Optional[str]) -> Optional[str]:
    """Descifra un valor PII cifrado. Retorna None si ciphertext es None.

    No loguea el valor en texto plano en ningún caso.
    """
    if ciphertext is None:
        return None
    return _cipher.decrypt(ciphertext)


# ── UsuarioService ────────────────────────────────────────────────────────────

class UsuarioService:
    def __init__(self, session: AsyncSession, current_user, request=None):
        self.session = session
        self.current_user = current_user
        self.request = request

    def _repo(self):
        from app.repositories.usuario_repository import UsuarioRepository
        return UsuarioRepository(self.session)

    def _asig_repo(self):
        from app.repositories.asignacion_repository import AsignacionRepository
        return AsignacionRepository(self.session)

    def _to_list_dto(self, user) -> dict:
        """DTO de listado: SIN PII en claro."""
        from app.schemas.usuario import UsuarioListItem
        return UsuarioListItem(
            id=user.id,
            tenant_id=user.tenant_id,
            email=user.email,
            nombre=user.nombre,
            apellidos=user.apellidos,
            legajo=user.legajo,
            legajo_profesional=user.legajo_profesional,
            banco=user.banco,
            regional=user.regional,
            facturador=user.facturador,
            estado=user.estado,
        )

    def _to_detail_dto(self, user) -> dict:
        """DTO de detalle: CON PII descifrada."""
        from app.schemas.usuario import UsuarioDetail
        return UsuarioDetail(
            id=user.id,
            tenant_id=user.tenant_id,
            email=user.email,
            nombre=user.nombre,
            apellidos=user.apellidos,
            dni=decrypt_pii(user.dni_enc),
            cuil=decrypt_pii(user.cuil_enc),
            cbu=decrypt_pii(user.cbu_enc),
            alias_cbu=decrypt_pii(user.alias_cbu_enc),
            legajo=user.legajo,
            legajo_profesional=user.legajo_profesional,
            banco=user.banco,
            regional=user.regional,
            facturador=user.facturador,
            estado=user.estado,
        )

    async def create(self, data: dict):
        """Crea un usuario cifrando PII y hasheando el password.

        Lanza 409 si email duplicado en tenant.
        """
        from app.core.security import hash_password
        # Hashear password antes de persistir
        raw_password = data.pop("password", None)
        if raw_password:
            data["password_hash"] = hash_password(raw_password)

        pii_data = {
            "dni_enc": encrypt_pii(data.pop("dni", None)),
            "cuil_enc": encrypt_pii(data.pop("cuil", None)),
            "cbu_enc": encrypt_pii(data.pop("cbu", None)),
            "alias_cbu_enc": encrypt_pii(data.pop("alias_cbu", None)),
        }
        data.update({k: v for k, v in pii_data.items() if v is not None})
        try:
            user = await self._repo().create(self.current_user.tenant_id, data)
        except IntegrityError:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail="Email ya registrado en el tenant")
        return self._to_list_dto(user)

    async def list_users(self):
        users = await self._repo().list_active(self.current_user.tenant_id)
        return [self._to_list_dto(u) for u in users]

    async def get_detail(self, user_id: uuid.UUID):
        user = await self._repo().get_by_id(user_id, self.current_user.tenant_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
        return self._to_detail_dto(user)

    async def update(self, user_id: uuid.UUID, data: dict):
        # Cifrar PII si viene en el payload
        for field, col in [("dni", "dni_enc"), ("cuil", "cuil_enc"),
                            ("cbu", "cbu_enc"), ("alias_cbu", "alias_cbu_enc")]:
            if field in data:
                data[col] = encrypt_pii(data.pop(field))

        from app.models.estructura import EstadoEntidad
        if data.get("estado") == EstadoEntidad.inactiva:
            await self._cascade_close_assignments(user_id)

        user = await self._repo().update(user_id, self.current_user.tenant_id, data)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
        return self._to_list_dto(user)

    async def soft_delete(self, user_id: uuid.UUID) -> None:
        found = await self._repo().soft_delete(user_id, self.current_user.tenant_id)
        if not found:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

    async def _cascade_close_assignments(self, user_id: uuid.UUID) -> None:
        """Cierra todas las asignaciones vigentes del usuario.

        Para cada una: setea hasta=fecha_baja, audita ASIGNACION_MODIFICAR,
        y emite alerta al responsable_id si no es null.
        """
        today = date.today()
        asig_repo = self._asig_repo()
        vigentes = await asig_repo.list_vigentes(
            self.current_user.tenant_id, user_id=user_id
        )
        notified_responsables: set[uuid.UUID] = set()
        for asig in vigentes:
            await asig_repo.update(asig.id, self.current_user.tenant_id, {"hasta": today})
            await record_audit(
                self.session,
                self.current_user,
                ASIGNACION_MODIFICAR,
                request=self.request,
                detail={"asignacion_id": str(asig.id), "motivo": "usuario_desactivado", "hasta": str(today)},
            )
            if asig.responsable_id and asig.responsable_id not in notified_responsables:
                # Alerta de vacancia (en esta iteración: registrada en auditoría)
                await record_audit(
                    self.session,
                    self.current_user,
                    "VACANCIA_GENERADA",
                    request=self.request,
                    detail={
                        "responsable_id": str(asig.responsable_id),
                        "asignacion_id": str(asig.id),
                        "usuario_id": str(user_id),
                    },
                )
                notified_responsables.add(asig.responsable_id)
