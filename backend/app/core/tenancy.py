class MissingTenantScopeError(Exception):
    """
    Raised when an operation that requires tenant isolation is attempted 
    without providing a valid tenant_id. 
    This enforces row-level security and fail-closed behavior.
    """
    pass
