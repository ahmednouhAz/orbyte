from datetime import datetime
from datetime import timedelta
from datetime import timezone

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException

from sqlalchemy.orm import Session

from orbyte.auth.schemas import UserCreate
from orbyte.auth.users import current_curator_or_admin_user
from orbyte.auth.users import get_user_manager
from orbyte.auth.users import User
from orbyte.auth.users import UserManager
from orbyte.db.engine.sql_engine import get_session
from orbyte.db.join_link import create_join_link
from orbyte.db.join_link import fetch_join_link_by_id
from orbyte.db.join_link import fetch_join_links_for_group
from orbyte.db.join_link import record_join_link_use__no_commit
from orbyte.db.join_link import resolve_join_link
from orbyte.db.join_link import revoke_join_link
from orbyte.db.models import UserRole
from orbyte.db.user_group import add_users_to_user_group
from orbyte.db.user_group import fetch_user_group_by_id
from orbyte.db.user_group import user_curates_group
from orbyte.server.features.join_link.models import JoinLinkCreate
from orbyte.server.features.join_link.models import JoinLinkCreateResponse
from orbyte.server.features.join_link.models import JoinLinkLookupResponse
from orbyte.server.features.join_link.models import JoinLinkRedeemRequest
from orbyte.server.features.join_link.models import JoinLinkRedeemResponse
from orbyte.server.features.join_link.models import JoinLinkSnapshot

router = APIRouter(prefix="/manage")
public_router = APIRouter(prefix="/join-link")


def _require_group_access(
    db_session: Session, user: User, group_id: int
) -> None:
    """Admins may manage join links for any group; curators only for
    groups they curate."""
    if user.role == UserRole.ADMIN:
        return
    if not user_curates_group(db_session, user.id, group_id):
        raise HTTPException(
            status_code=403,
            detail="You do not curate this group.",
        )


@router.post("/admin/groups/{group_id}/join-links")
def create_group_join_link(
    group_id: int,
    create_request: JoinLinkCreate,
    user: User = Depends(current_curator_or_admin_user),
    db_session: Session = Depends(get_session),
) -> JoinLinkCreateResponse:
    if fetch_user_group_by_id(db_session, group_id) is None:
        raise HTTPException(
            status_code=404, detail=f"User group {group_id} does not exist"
        )
    _require_group_access(db_session, user, group_id)

    expires_at = (
        datetime.now(timezone.utc)
        + timedelta(hours=create_request.expires_in_hours)
        if create_request.expires_in_hours is not None
        else None
    )
    link, token = create_join_link(
        db_session=db_session,
        user_group_id=group_id,
        created_by=user.id,
        is_reusable=create_request.is_reusable,
        expires_at=expires_at,
    )
    return JoinLinkCreateResponse.from_model(link, token)


@router.get("/admin/groups/{group_id}/join-links")
def list_group_join_links(
    group_id: int,
    user: User = Depends(current_curator_or_admin_user),
    db_session: Session = Depends(get_session),
) -> list[JoinLinkSnapshot]:
    if fetch_user_group_by_id(db_session, group_id) is None:
        raise HTTPException(
            status_code=404, detail=f"User group {group_id} does not exist"
        )
    _require_group_access(db_session, user, group_id)

    links = fetch_join_links_for_group(db_session, group_id)
    return [JoinLinkSnapshot.from_model(link) for link in links]


@router.delete("/admin/groups/{group_id}/join-links/{link_id}")
def revoke_group_join_link(
    group_id: int,
    link_id: int,
    user: User = Depends(current_curator_or_admin_user),
    db_session: Session = Depends(get_session),
) -> None:
    _require_group_access(db_session, user, group_id)

    link = fetch_join_link_by_id(db_session, link_id)
    if link is None or link.user_group_id != group_id:
        raise HTTPException(status_code=404, detail="Join link not found")
    revoke_join_link(db_session, link)


@public_router.get("/{token}")
def lookup_join_link(
    token: str,
    db_session: Session = Depends(get_session),
) -> JoinLinkLookupResponse:
    link = resolve_join_link(db_session, token)
    if link is None:
        return JoinLinkLookupResponse(valid=False)

    group = fetch_user_group_by_id(db_session, link.user_group_id)
    if group is None:
        return JoinLinkLookupResponse(valid=False)

    return JoinLinkLookupResponse(valid=True, group_name=group.name)


@public_router.post("/{token}/redeem")
async def redeem_join_link(
    token: str,
    redeem_request: JoinLinkRedeemRequest,
    user_manager: UserManager = Depends(get_user_manager),
    db_session: Session = Depends(get_session),
) -> JoinLinkRedeemResponse:
    link = resolve_join_link(db_session, token)
    if link is None:
        raise HTTPException(
            status_code=410, detail="This join link is invalid or has expired."
        )

    user_create = UserCreate(
        email=redeem_request.email,
        password=redeem_request.password,
    )
    new_user = await user_manager.create(
        user_create, safe=True, join_token=token
    )
    await user_manager.on_after_register(new_user)

    # Additive + idempotent: a join link targeting a default group (e.g.
    # "Basic") would otherwise collide with the membership row
    # on_after_register's default-group assignment just created.
    add_users_to_user_group(db_session, link.user_group_id, [new_user.id])
    record_join_link_use__no_commit(link)
    db_session.commit()

    return JoinLinkRedeemResponse(id=str(new_user.id), email=new_user.email)
