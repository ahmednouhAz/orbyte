from orbyte.error_handling.error_codes import OrbyteErrorCode
from orbyte.error_handling.exceptions import OrbyteError
from shared_configs.configs import MULTI_TENANT


def require_hook_enabled() -> None:
    """FastAPI dependency that gates all hook management endpoints.

    Hooks are only available in single-tenant / self-hosted EE deployments.

    Use as: Depends(require_hook_enabled)
    """
    if MULTI_TENANT:
        raise OrbyteError(
            OrbyteErrorCode.SINGLE_TENANT_ONLY,
            "Hooks are not available in multi-tenant deployments",
        )
