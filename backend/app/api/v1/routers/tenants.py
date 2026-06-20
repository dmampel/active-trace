import uuid
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.models.tenant import Tenant

router = APIRouter(prefix="/api/v1/tenants", tags=["tenants"])


class TenantPublic(BaseModel):
    id: uuid.UUID
    name: str

    model_config = {"from_attributes": True}


@router.get("", response_model=list[TenantPublic])
async def list_active_tenants(db: AsyncSession = Depends(get_db)):
    """Devuelve los tenants activos. Endpoint público para resolución en el login."""
    result = await db.execute(
        select(Tenant).where(Tenant.is_active.is_(True), Tenant.deleted_at.is_(None))
    )
    return result.scalars().all()
