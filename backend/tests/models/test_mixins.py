import pytest
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Session
from app.models.base import Base, UUIDMixin, TimestampMixin, SoftDeleteMixin, TenantMixin
from app.models.tenant import Tenant

# Create a test-specific model using the mixins
class DummyModel(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin, TenantMixin):
    __tablename__ = "dummy"
    name = Column(String(50))

@pytest.fixture(scope="module")
def engine():
    # Use SQLite in-memory for fast model/mixin unit testing
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    return eng

@pytest.fixture
def session(engine):
    with Session(engine) as session:
        yield session

def test_mixins_behavior(session):
    # Setup a tenant first due to ForeignKey constraint
    tenant = Tenant(name="Test Tenant")
    session.add(tenant)
    session.commit()
    
    # Create Dummy Model
    dummy = DummyModel(name="Test", tenant_id=tenant.id)
    session.add(dummy)
    session.commit()
    
    # Test UUIDMixin
    assert isinstance(dummy.id, uuid.UUID)
    
    # Test TimestampMixin
    assert dummy.created_at is not None
    assert dummy.updated_at is not None
    assert dummy.created_at <= dummy.updated_at
    
    # Test SoftDeleteMixin
    assert dummy.deleted_at is None
    
    # Test TenantMixin
    assert dummy.tenant_id == tenant.id
    
    # Update and check updated_at
    old_updated_at = dummy.updated_at
    dummy.name = "Updated Test"
    session.commit()
    
    assert dummy.updated_at >= old_updated_at
    
    # Soft delete
    dummy.deleted_at = datetime.now(timezone.utc)
    session.commit()
    assert dummy.deleted_at is not None
