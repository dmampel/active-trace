# Soft Delete Specification

## Purpose
Define the mechanism for logical deletion of entities to preserve the audit trail.

## Requirements

### Requirement: Logical Deletion

The system MUST NOT physically delete records from the database when a delete operation is requested.

#### Scenario: Deleting a record
- GIVEN an existing record in the database
- WHEN the system executes `BaseRepository.delete(id=X, tenant_id=A)`
- THEN the record MUST remain in the database
- AND its `deleted_at` timestamp MUST be set to the current UTC time

### Requirement: Exclusion of Deleted Records

The system MUST exclude soft-deleted records from standard retrieval operations.

#### Scenario: Listing records after a deletion
- GIVEN a record X that has `deleted_at` populated
- WHEN the system lists records using `BaseRepository.list(tenant_id=A)`
- THEN record X MUST NOT be included in the results

#### Scenario: Fetching a deleted record by ID
- GIVEN a record X that has `deleted_at` populated
- WHEN the system attempts to fetch it using `BaseRepository.get(id=X, tenant_id=A)`
- THEN the system MUST return None
