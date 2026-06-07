import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.repositories.base import BaseRepository


class AuditLogRepository(BaseRepository[AuditLog, dict, dict]):
    def __init__(self, session: Any):
        super().__init__(AuditLog, session)

    async def update(self, *args: Any, **kwargs: Any) -> None:  # type: ignore[override]
        raise NotImplementedError("AuditLog es append-only — no se permite UPDATE")

    async def delete(self, *args: Any, **kwargs: Any) -> None:  # type: ignore[override]
        raise NotImplementedError("AuditLog es append-only — no se permite DELETE")

    async def create_entry(self, entry_data: dict) -> AuditLog:
        entry = AuditLog(**entry_data)
        self.session.add(entry)
        await self.session.flush()
        return entry

    @staticmethod
    def sync_create_entry(session: Session, entry_data: dict) -> AuditLog:
        """Sync variant for use in the sync auth service context."""
        entry = AuditLog(**entry_data)
        session.add(entry)
        session.flush()
        return entry
