"""CE hook executor.

HookSkipped and HookSoftFailed are real classes kept here because
process_message.py (CE code) uses isinstance checks against them.

execute_hook is the public entry point. It dispatches to _execute_hook_impl
via fetch_versioned_implementation, which always resolves to this CE no-op
(the EE Hooks/Webhooks implementation was removed) and returns HookSkipped().
"""

from typing import Any
from typing import TypeVar

from pydantic import BaseModel
from sqlalchemy.orm import Session

from orbyte.db.enums import HookPoint
from orbyte.utils.variable_functionality import fetch_versioned_implementation


class HookSkipped:
    """No active hook configured for this hook point."""


class HookSoftFailed:
    """Hook was called but failed with SOFT fail strategy — continuing."""


T = TypeVar("T", bound=BaseModel)


def _execute_hook_impl(
    *,
    db_session: Session,  # noqa: ARG001
    hook_point: HookPoint,  # noqa: ARG001
    payload: dict[str, Any],  # noqa: ARG001
    response_type: type[T],  # noqa: ARG001
) -> T | HookSkipped | HookSoftFailed:
    """CE no-op — hooks are not available without EE."""
    return HookSkipped()


def execute_hook(
    *,
    db_session: Session,
    hook_point: HookPoint,
    payload: dict[str, Any],
    response_type: type[T],
) -> T | HookSkipped | HookSoftFailed:
    """Execute the hook for the given hook point.

    Dispatches to the versioned implementation so EE gets the real executor
    and CE gets the no-op stub, without any changes at the call site.
    """
    impl = fetch_versioned_implementation("orbyte.hooks.executor", "_execute_hook_impl")
    return impl(
        db_session=db_session,
        hook_point=hook_point,
        payload=payload,
        response_type=response_type,
    )
