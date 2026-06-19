"""Service de perfil propio (C-20).

Responsabilidades:
- Resolver el usuario exclusivamente desde el JWT (current_user.id / tenant_id).
- Descifrar PII para el titular (cuil incluido).
- Actualizar solo campos editables; cifrar PII modificada.
- Mapear modalidad_cobro → facturador.
- Validar unicidad (tenant_id, email) → 409 si duplicado.

Regla crítica: identidad SIEMPRE del JWT, nunca de parámetros de request.
"""
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.usuario_service import decrypt_pii, encrypt_pii


class PerfilService:
    def __init__(self, session: AsyncSession, current_user):
        self.session = session
        self.current_user = current_user

    def _repo(self):
        from app.repositories.usuario_repository import UsuarioRepository
        return UsuarioRepository(self.session)

    def _to_perfil_dto(self, user):
        from app.schemas.perfil import PerfilRead
        return PerfilRead(
            id=user.id,
            tenant_id=user.tenant_id,
            email=user.email,
            nombre=user.nombre,
            apellidos=user.apellidos,
            # PII descifrada para el titular
            dni=decrypt_pii(user.dni_enc),
            cuil=decrypt_pii(user.cuil_enc),
            cbu=decrypt_pii(user.cbu_enc),
            alias_cbu=decrypt_pii(user.alias_cbu_enc),
            banco=user.banco,
            regional=user.regional,
            legajo=user.legajo,
            legajo_profesional=user.legajo_profesional,
            facturador=user.facturador,
            estado=user.estado,
        )

    async def leer_perfil(self):
        """Retorna el perfil del usuario del JWT con PII descifrada.

        Identidad exclusivamente del JWT — nunca de parámetros de request.
        """
        user = await self._repo().get_by_id(
            self.current_user.id, self.current_user.tenant_id
        )
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Perfil no encontrado",
            )
        return self._to_perfil_dto(user)

    async def actualizar_perfil(self, data: dict):
        """Actualiza solo los campos editables del propio perfil.

        - cuil NO es editable aquí (el schema ya lo rechaza con 422).
        - Cifra PII modificada (dni, cbu, alias_cbu).
        - Mapea modalidad_cobro → facturador.
        - Retorna 409 si email duplicado en el tenant.
        """
        # Mapeo modalidad_cobro → facturador
        modalidad = data.pop("modalidad_cobro", None)
        if modalidad is not None:
            data["facturador"] = modalidad == "factura"

        # Cifrar PII editable
        for field, col in [
            ("dni", "dni_enc"),
            ("cbu", "cbu_enc"),
            ("alias_cbu", "alias_cbu_enc"),
        ]:
            if field in data:
                data[col] = encrypt_pii(data.pop(field))

        try:
            user = await self._repo().update(
                self.current_user.id, self.current_user.tenant_id, data
            )
        except IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email ya registrado en el tenant",
            )

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Perfil no encontrado",
            )
        return self._to_perfil_dto(user)
