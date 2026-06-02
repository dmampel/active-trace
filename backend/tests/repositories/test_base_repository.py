import pytest
import uuid
from sqlalchemy import Column, String
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from app.models.base import Base, UUIDMixin, TimestampMixin, SoftDeleteMixin, TenantMixin
from app.models.tenant import Tenant
from app.repositories.base import BaseRepository
from app.core.tenancy import MissingTenantScopeError

class DummyItem(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin, TenantMixin):
    __tablename__ = "dummy_items"
    name = Column(String)

class DummyRepository(BaseRepository[DummyItem, dict, dict]):
    def __init__(self, session: AsyncSession):
        super().__init__(DummyItem, session)

@pytest.fixture
async def async_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
async def db_session(async_engine):
    async with AsyncSession(async_engine, expire_on_commit=False) as session:
        yield session

@pytest.fixture
async def setup_data(db_session):
    # Create two tenants
    t1 = Tenant(id=uuid.uuid4(), name="Tenant A")
    t2 = Tenant(id=uuid.uuid4(), name="Tenant B")
    db_session.add_all([t1, t2])
    
    # Create items for each tenant
    i1 = DummyItem(id=uuid.uuid4(), name="Item A1", tenant_id=t1.id)
    i2 = DummyItem(id=uuid.uuid4(), name="Item B1", tenant_id=t2.id)
    db_session.add_all([i1, i2])
    await db_session.commit()
    return {"t1_id": t1.id, "t2_id": t2.id, "i1_id": i1.id, "i2_id": i2.id}

@pytest.mark.asyncio
async def test_repository_enforces_tenant_scope(db_session, setup_data):
    repo = DummyRepository(db_session)
    t1_id = setup_data["t1_id"]
    
    # List should only return items for t1
    items = await repo.list(tenant_id=t1_id)
    assert len(items) == 1
    assert items[0].name == "Item A1"
    
    # Get should fail for an item belonging to another tenant
    i2_id = setup_data["i2_id"]
    item = await repo.get(id=i2_id, tenant_id=t1_id)
    assert item is None

@pytest.mark.asyncio
async def test_repository_missing_tenant_raises_error(db_session, setup_data):
    repo = DummyRepository(db_session)
    
    with pytest.raises(MissingTenantScopeError):
        await repo.list()
        
    with pytest.raises(MissingTenantScopeError):
        await repo.get(id=setup_data["i1_id"])

@pytest.mark.asyncio
async def test_repository_soft_delete(db_session, setup_data):
    repo = DummyRepository(db_session)
    t1_id = setup_data["t1_id"]
    i1_id = setup_data["i1_id"]
    
    # Delete the item
    await repo.delete(id=i1_id, tenant_id=t1_id)
    
    # Verify it doesn't show up in normal lists
    items = await repo.list(tenant_id=t1_id)
    assert len(items) == 0
    
    # Verify we can't get it
    item = await repo.get(id=i1_id, tenant_id=t1_id)
    assert item is None
    
    # Verify we CAN get it if we explicitly include deleted
    item_deleted = await repo.get(id=i1_id, tenant_id=t1_id, include_deleted=True)
    assert item_deleted is not None
    assert item_deleted.deleted_at is not None
