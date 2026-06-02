import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.user import PasswordResetToken, RefreshToken, User


class UserRepository:

    @staticmethod
    def get_by_email(session: Session, tenant_id: uuid.UUID, email: str) -> User | None:
        stmt = select(User).where(
            User.tenant_id == tenant_id,
            User.email == email,
            User.deleted_at.is_(None),
        )
        return session.execute(stmt).scalar_one_or_none()

    @staticmethod
    def get_by_id(session: Session, tenant_id: uuid.UUID, user_id: uuid.UUID) -> User | None:
        stmt = select(User).where(
            User.tenant_id == tenant_id,
            User.id == user_id,
            User.deleted_at.is_(None),
        )
        return session.execute(stmt).scalar_one_or_none()

    @staticmethod
    def create_refresh_token(
        session: Session,
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
    def get_refresh_token_by_hash(session: Session, token_hash: str) -> RefreshToken | None:
        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        return session.execute(stmt).scalar_one_or_none()

    @staticmethod
    def revoke_refresh_family(session: Session, family_id: uuid.UUID) -> None:
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=datetime.now(timezone.utc))
        )
        session.execute(stmt)

    @staticmethod
    def create_reset_token(
        session: Session,
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
    def get_reset_token_by_hash(session: Session, token_hash: str) -> PasswordResetToken | None:
        stmt = select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
        return session.execute(stmt).scalar_one_or_none()

    @staticmethod
    def mark_reset_token_used(session: Session, token_id: uuid.UUID) -> None:
        stmt = (
            update(PasswordResetToken)
            .where(PasswordResetToken.id == token_id)
            .values(used_at=datetime.now(timezone.utc))
        )
        session.execute(stmt)
