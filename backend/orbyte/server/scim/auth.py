"""Community-edition stub for SCIM authentication.

SCIM provisioning has been removed from this deployment. This module exists
solely so ``fetch_ee_implementation_or_noop("orbyte.server.scim.auth",
"verify_scim_token")`` in ``orbyte/server/auth_check.py`` has a base
implementation to resolve — no SCIM routes are registered, so this
dependency is never actually attached to a route or invoked.
"""

from fastapi import HTTPException
from fastapi import Request


def verify_scim_token(request: Request) -> None:  # noqa: ARG001
    raise HTTPException(status_code=404, detail="SCIM is not available")
