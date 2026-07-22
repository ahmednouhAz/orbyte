"""OrbyteError — the single exception type for all Orbyte business errors.

Raise ``OrbyteError`` instead of ``HTTPException`` in business code.  A global
FastAPI exception handler (registered via ``register_orbyte_exception_handlers``)
converts it into a JSON response with the standard
``{"error_code": "...", "detail": "..."}`` shape.

Usage::

    from orbyte.error_handling.error_codes import OrbyteErrorCode
    from orbyte.error_handling.exceptions import OrbyteError

    raise OrbyteError(OrbyteErrorCode.NOT_FOUND, "Session not found")

For upstream errors with a dynamic HTTP status (e.g. billing service),
use ``status_code_override``::

    raise OrbyteError(
        OrbyteErrorCode.BAD_GATEWAY,
        detail,
        status_code_override=upstream_status,
    )
"""

from fastapi import FastAPI
from fastapi import Request
from fastapi.responses import JSONResponse

from orbyte.error_handling.error_codes import OrbyteErrorCode
from orbyte.utils.logger import setup_logger

logger = setup_logger()


class OrbyteError(Exception):
    """Structured error that maps to a specific ``OrbyteErrorCode``.

    Attributes:
        error_code: The ``OrbyteErrorCode`` enum member.
        detail: Human-readable detail (defaults to the error code string).
        status_code: HTTP status — either overridden or from the error code.
    """

    def __init__(
        self,
        error_code: OrbyteErrorCode,
        detail: str | None = None,
        *,
        status_code_override: int | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        resolved_detail = detail or error_code.code
        super().__init__(resolved_detail)
        self.error_code = error_code
        self.detail = resolved_detail
        self._status_code_override = status_code_override
        self.headers = headers

    @property
    def status_code(self) -> int:
        return self._status_code_override or self.error_code.status_code


def log_orbyte_error(exc: OrbyteError) -> None:
    detail = exc.detail
    status_code = exc.status_code
    if status_code >= 500:
        logger.error("OrbyteError %s: %s", exc.error_code.code, detail)
    elif status_code >= 400:
        logger.warning("OrbyteError %s: %s", exc.error_code.code, detail)


def orbyte_error_to_json_response(exc: OrbyteError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.error_code.detail(exc.detail),
        headers=exc.headers,
    )


def register_orbyte_exception_handlers(app: FastAPI) -> None:
    """Register a global handler that converts ``OrbyteError`` to JSON responses.

    Must be called *after* the app is created but *before* it starts serving.
    The handler logs at WARNING for 4xx and ERROR for 5xx.
    """

    @app.exception_handler(OrbyteError)
    async def _handle_orbyte_error(
        request: Request,  # noqa: ARG001
        exc: OrbyteError,
    ) -> JSONResponse:
        log_orbyte_error(exc)
        return orbyte_error_to_json_response(exc)
