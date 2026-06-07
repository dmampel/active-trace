import uuid
from typing import Generic, TypeVar, Type, Optional, List, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.sql import func
from app.models.base import SoftDeleteMixin, TenantMixin
from app.core.tenancy import MissingTenantScopeError

ModelType = TypeVar("ModelType")
CreateSchemaType = TypeVar("CreateSchemaType")
UpdateSchemaType = TypeVar("UpdateSchemaType")

class BaseRepository(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    def __init__(self, model: Type[ModelType], session: AsyncSession):
        self.model = model
        self.session = session

    def _apply_tenant_scope(self, query: Any, tenant_id: Optional[uuid.UUID]) -> Any:
        if issubclass(self.model, TenantMixin):
            if tenant_id is None:
                raise MissingTenantScopeError(f"Missing tenant_id for tenant-scoped model {self.model.__name__}")
            query = query.where(self.model.tenant_id == tenant_id)
        return query

    def _apply_soft_delete(self, query: Any, include_deleted: bool = False) -> Any:
        if issubclass(self.model, SoftDeleteMixin) and not include_deleted:
            query = query.where(self.model.deleted_at.is_(None))
        return query

    async def get(
        self,
        id: uuid.UUID | Any,
        tenant_id: Optional[uuid.UUID] = None,
        include_deleted: bool = False,
    ) -> Optional[ModelType]:
        query = select(self.model).where(self.model.id == id)
        query = self._apply_tenant_scope(query, tenant_id)
        query = self._apply_soft_delete(query, include_deleted)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list(
        self,
        tenant_id: Optional[uuid.UUID] = None,
        include_deleted: bool = False,
        skip: int = 0,
        limit: int = 100,
    ) -> List[ModelType]:
        query = select(self.model)
        query = self._apply_tenant_scope(query, tenant_id)
        query = self._apply_soft_delete(query, include_deleted)
        query = query.offset(skip).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def delete(
        self,
        id: uuid.UUID | Any,
        tenant_id: Optional[uuid.UUID] = None,
    ) -> bool:
        item = await self.get(id, tenant_id=tenant_id)
        if not item:
            return False

        if issubclass(self.model, SoftDeleteMixin):
            query = update(self.model).where(self.model.id == id)
            query = self._apply_tenant_scope(query, tenant_id)
            query = query.values(deleted_at=func.now())
            await self.session.execute(query)
        else:
            await self.session.delete(item)

        await self.session.commit()
        return True
