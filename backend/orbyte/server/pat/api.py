"""API endpoints for Personal Access Tokens."""

from fastapi import APIRouter
from fastapi import Depends
from sqlalchemy.orm import Session

from orbyte.auth.permissions import require_permission
from orbyte.db.engine.sql_engine import get_session
from orbyte.db.enums import PatType
from orbyte.db.enums import Permission
from orbyte.db.models import User
from orbyte.db.pat import create_pat
from orbyte.db.pat import list_user_pats
from orbyte.db.pat import revoke_pat
from orbyte.error_handling.error_codes import OrbyteErrorCode
from orbyte.error_handling.exceptions import OrbyteError
from orbyte.server.pat.models import CreatedTokenResponse
from orbyte.server.pat.models import CreateTokenRequest
from orbyte.server.pat.models import PatScopeOption
from orbyte.server.pat.models import SELECTABLE_PAT_SCOPES
from orbyte.server.pat.models import TokenResponse
from orbyte.utils.logger import setup_logger

logger = setup_logger()

router = APIRouter(prefix="/user/pats")


def _validate_assignable_scopes(scopes: list[Permission] | None) -> None:
    """None = unrestricted; a provided list must be non-empty and assignable."""
    if scopes is None:
        return
    if not scopes:
        raise OrbyteError(
            OrbyteErrorCode.INVALID_INPUT,
            "A scoped token must include at least one scope.",
        )
    unsupported = [s for s in scopes if s not in SELECTABLE_PAT_SCOPES]
    if unsupported:
        raise OrbyteError(
            OrbyteErrorCode.INVALID_INPUT,
            f"Unsupported token scope(s): {', '.join(s.value for s in unsupported)}",
        )


@router.get("/scopes")
def list_selectable_scopes(
    _: User = Depends(require_permission(Permission.BASIC_ACCESS)),
) -> list[PatScopeOption]:
    """The scopes a user may assign when minting a token, with display metadata."""
    return list(SELECTABLE_PAT_SCOPES.values())


@router.get("")
def list_tokens(
    user: User = Depends(require_permission(Permission.BASIC_ACCESS)),
    db_session: Session = Depends(get_session),
) -> list[TokenResponse]:
    """List all active user-created tokens for current user."""
    pats = list_user_pats(db_session, user.id, pat_type=PatType.USER)
    return [TokenResponse.model_validate(pat) for pat in pats]


@router.post("")
def create_token(
    request: CreateTokenRequest,
    user: User = Depends(require_permission(Permission.BASIC_ACCESS)),
    db_session: Session = Depends(get_session),
) -> CreatedTokenResponse:
    """Create new personal access token for current user."""
    _validate_assignable_scopes(request.scopes)

    try:
        pat, raw_token = create_pat(
            db_session=db_session,
            user_id=user.id,
            name=request.name,
            expiration_days=request.expiration_days,
            scopes=request.scopes,
        )
    except ValueError as e:
        raise OrbyteError(OrbyteErrorCode.INVALID_INPUT, str(e))

    db_session.commit()

    logger.info("User %s created PAT '%s'", user.email, request.name)

    return CreatedTokenResponse(
        **TokenResponse.model_validate(pat).model_dump(),
        token=raw_token,  # ONLY time we return the raw token!
    )


@router.delete("/{token_id}")
def delete_token(
    token_id: int,
    user: User = Depends(require_permission(Permission.BASIC_ACCESS)),
    db_session: Session = Depends(get_session),
) -> dict[str, str]:
    """Delete (revoke) personal access token. Only owner can revoke their own tokens."""
    success = revoke_pat(db_session, token_id, user.id, pat_type=PatType.USER)
    if not success:
        raise OrbyteError(OrbyteErrorCode.NOT_FOUND, "Token not found or not owned by user")
    db_session.commit()

    logger.info("User %s revoked token %s", user.email, token_id)
    return {"message": "Token deleted successfully"}
