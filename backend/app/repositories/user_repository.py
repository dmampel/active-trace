import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import PasswordResetToken, RefreshToken, User


class UserRepository:

    @staticmethod
    async def get_by_email(session: AsyncSession, tenant_id: uuid.UUID, email: str) -> User | None:
        stmt = select(User).where(
            User.tenant_id == tenant_id,
            func.lower(User.email) == email.lower(),
            User.deleted_at.is_(None),
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_id(session: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID) -> User | None:
        stmt = select(User).where(
            User.tenant_id == tenant_id,
            User.id == user_id,
            User.deleted_at.is_(None),
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def create_refresh_token(
        session: AsyncSession,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
        token_hash: str,
        family_id: uuid.UUID,
        expires_at: datetime,
    ) -> RefreshToken:
        rt = RefreshToken(
            user_id=user_id,
            tenant_id=tenant_id,
            token_hash=token_hash,
            family_id=family_id,
            expires_at=expires_at,
        )
        session.add(rt)
        return rt

    @staticmethod
    async def get_refresh_token_by_hash(
        session: AsyncSession, token_hash: str, tenant_id: uuid.UUID
    ) -> RefreshToken | None:
        stmt = select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.tenant_id == tenant_id,
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def revoke_refresh_family(session: AsyncSession, family_id: uuid.UUID) -> None:
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=datetime.now(timezone.utc))
        )
        await session.execute(stmt)

    @staticmethod
    async def create_reset_token(
        session: AsyncSession,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
        token_hash: str,
        expires_at: datetime,
    ) -> PasswordResetToken:
        prt = PasswordResetToken(
            user_id=user_id,
            tenant_id=tenant_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        session.add(prt)
        return prt

    @staticmethod
    async def get_reset_token_by_hash(
        session: AsyncSession, token_hash: str, tenant_id: uuid.UUID
    ) -> PasswordResetToken | None:
        stmt = select(PasswordResetToken).where(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.tenant_id == tenant_id,
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def mark_reset_token_used(session: AsyncSession, token_id: uuid.UUID) -> None:
        stmt = (
            update(PasswordResetToken)
            .where(PasswordResetToken.id == token_id)
            .values(used_at=datetime.now(timezone.utc))
        )
        await session.execute(stmt)
