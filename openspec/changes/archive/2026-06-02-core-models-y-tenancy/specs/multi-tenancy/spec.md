# Multi-Tenancy Specification

## Purpose
Define the rules for data isolation across different institutions (tenants) using row-level security enforced at the application layer via a BaseRepository.

## Requirements

### Requirement: Tenant Isolation by Default

The system MUST scope all database queries to a specific `tenant_id` by default unless explicitly bypassed.

#### Scenario: Querying data for a specific tenant
- GIVEN a user authenticated under Tenant A
- WHEN the system queries entities via `BaseRepository.list(tenant_id=A)`
- THEN only records belonging to Tenant A MUST be returned

#### Scenario: Attempting to access data from another tenant
- GIVEN a user authenticated under Tenant A
- WHEN the system attempts to fetch a record via `BaseRepository.get(id=X, tenant_id=A)` where record X belongs to Tenant B
- THEN the system MUST return a Not Found (404) or None result

### Requirement: Missing Tenant Scope Fails Closed

The system MUST NOT allow querying tenant-scoped entities without explicitly providing the `tenant_id`.

#### Scenario: Querying without a tenant ID
- GIVEN a developer writes a query using `BaseRepository.list()` without providing `tenant_id`
- WHEN the code is executed
- THEN the system MUST raise a critical internal error (e.g., `MissingTenantScopeError`)
- AND the query MUST NOT hit the database
