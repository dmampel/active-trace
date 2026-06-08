## MODIFIED Requirements

### Requirement: Tenant Isolation by Default
The system MUST scope all database queries to a specific `tenant_id` by default unless explicitly bypassed. All repository operations SHALL use `AsyncSession` (SQLAlchemy 2.0 async). The `BaseRepository` SHALL be the single source of async query patterns for all entities.

#### Scenario: Querying data for a specific tenant
- **WHEN** the system queries entities via `BaseRepository.list(tenant_id=A)`
- **THEN** only records belonging to Tenant A MUST be returned

#### Scenario: Attempting to access data from another tenant
- **WHEN** the system attempts to fetch a record via `BaseRepository.get(id=X, tenant_id=A)` where record X belongs to Tenant B
- **THEN** the system MUST return a Not Found (404) or None result

---

### Requirement: Missing Tenant Scope Fails Closed
The system MUST NOT allow querying tenant-scoped entities without explicitly providing the `tenant_id`.

#### Scenario: Querying without a tenant ID
- **WHEN** code calls `BaseRepository.list()` without providing `tenant_id` on a tenant-scoped model
- **THEN** the system MUST raise `MissingTenantScopeError`
- **AND** the query MUST NOT hit the database

## ADDED Requirements

### Requirement: Repository delete does not commit internally
`BaseRepository.delete()` SHALL perform the soft-delete operation but SHALL NOT call `session.commit()`. Transaction management (commit/rollback) is the exclusive responsibility of the service or router layer.

#### Scenario: Delete within a multi-step transaction
- **WHEN** a service calls `BaseRepository.delete()` followed by other write operations in the same session
- **THEN** all operations are part of the same transaction and committed together by the service
- **AND** a failure in any subsequent operation rolls back the delete as well

#### Scenario: Delete called standalone
- **WHEN** a router calls delete and then commits the session itself
- **THEN** the record is soft-deleted and the commit succeeds

### Requirement: All repositories use AsyncSession
Every repository class (UserRepository, RbacRepository, EstructuraRepository, AuditLogRepository, BaseRepository) SHALL operate exclusively with `AsyncSession`. No synchronous SQLAlchemy sessions SHALL be used in the request path. The only acceptable use of synchronous sessions is in `alembic/env.py` for database migrations.

#### Scenario: Async repository in async router
- **WHEN** an async FastAPI router uses a repository injected via `Depends(get_db)`
- **THEN** the repository receives an `AsyncSession` and all queries are non-blocking

#### Scenario: No sync session in request path
- **WHEN** any router or service method executes during a request cycle
- **THEN** no synchronous SQLAlchemy `Session` object is used (only `AsyncSession`)
