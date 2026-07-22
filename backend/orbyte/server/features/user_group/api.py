from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from sqlalchemy.orm import Session

from orbyte.auth.permissions import require_permission
from orbyte.auth.users import current_curator_or_admin_user
from orbyte.db.engine.sql_engine import get_session
from orbyte.db.enums import Permission
from orbyte.db.models import User
from orbyte.db.models import UserRole
from orbyte.db.user_group import add_users_to_user_group
from orbyte.db.user_group import delete_user_group
from orbyte.db.user_group import fetch_minimal_user_groups
from orbyte.db.user_group import fetch_user_group_by_id
from orbyte.db.user_group import fetch_user_groups
from orbyte.db.user_group import insert_user_group
from orbyte.db.user_group import rename_user_group
from orbyte.db.user_group import update_group_agent_sharing
from orbyte.db.user_group import update_user_group
from orbyte.server.features.user_group.models import AddUsersToUserGroupRequest
from orbyte.server.features.user_group.models import MinimalUserGroupSnapshot
from orbyte.server.features.user_group.models import UpdateGroupAgentsRequest
from orbyte.server.features.user_group.models import UserGroupCreate
from orbyte.server.features.user_group.models import UserGroupRename
from orbyte.server.features.user_group.models import UserGroupSnapshot
from orbyte.server.features.user_group.models import UserGroupUpdate

router = APIRouter(prefix="/manage")


@router.post("/admin/groups")
def create_user_group(
    user_group_create_request: UserGroupCreate,
    _: User = Depends(require_permission(Permission.FULL_ADMIN_PANEL_ACCESS)),
    db_session: Session = Depends(get_session),
) -> UserGroupSnapshot:
    try:
        group = insert_user_group(
            db_session=db_session,
            name=user_group_create_request.name,
            user_ids=user_group_create_request.user_ids,
            cc_pair_ids=user_group_create_request.cc_pair_ids,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return UserGroupSnapshot.from_model(group)


@router.get("/admin/groups")
def list_user_groups(
    _: User = Depends(current_curator_or_admin_user),
    db_session: Session = Depends(get_session),
) -> list[UserGroupSnapshot]:
    groups = fetch_user_groups(db_session=db_session)
    return [UserGroupSnapshot.from_model(group) for group in groups]


@router.get("/groups/minimal")
def list_minimal_user_groups(
    _: User = Depends(require_permission(Permission.BASIC_ACCESS)),
    db_session: Session = Depends(get_session),
) -> list[MinimalUserGroupSnapshot]:
    groups = fetch_minimal_user_groups(db_session=db_session)
    return [MinimalUserGroupSnapshot.from_model(group) for group in groups]


@router.patch("/admin/groups/rename")
def rename_group(
    rename_request: UserGroupRename,
    _: User = Depends(require_permission(Permission.FULL_ADMIN_PANEL_ACCESS)),
    db_session: Session = Depends(get_session),
) -> UserGroupSnapshot:
    try:
        group = rename_user_group(
            db_session=db_session,
            group_id=rename_request.id,
            new_name=rename_request.name,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return UserGroupSnapshot.from_model(group)


@router.patch("/admin/groups/{user_group_id}")
def patch_user_group(
    user_group_id: int,
    user_group_update_request: UserGroupUpdate,
    user: User = Depends(current_curator_or_admin_user),
    db_session: Session = Depends(get_session),
) -> UserGroupSnapshot:
    # Granting/revoking curator status is an admin-only action — curators can
    # update their own group's membership/resources, but not promote others.
    curator_ids = (
        user_group_update_request.curator_ids if user.role == UserRole.ADMIN else None
    )
    try:
        group = update_user_group(
            db_session=db_session,
            group_id=user_group_id,
            user_ids=user_group_update_request.user_ids,
            cc_pair_ids=user_group_update_request.cc_pair_ids,
            curator_ids=curator_ids,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return UserGroupSnapshot.from_model(group)


@router.post("/admin/groups/{user_group_id}/add-users")
def add_users_to_group(
    user_group_id: int,
    add_users_request: AddUsersToUserGroupRequest,
    _: User = Depends(current_curator_or_admin_user),
    db_session: Session = Depends(get_session),
) -> UserGroupSnapshot:
    try:
        group = add_users_to_user_group(
            db_session=db_session,
            group_id=user_group_id,
            user_ids=add_users_request.user_ids,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return UserGroupSnapshot.from_model(group)


@router.delete("/admin/groups/{user_group_id}")
def delete_group(
    user_group_id: int,
    _: User = Depends(require_permission(Permission.FULL_ADMIN_PANEL_ACCESS)),
    db_session: Session = Depends(get_session),
) -> None:
    group = fetch_user_group_by_id(db_session=db_session, group_id=user_group_id)
    if group is None:
        raise HTTPException(
            status_code=404, detail=f"User group {user_group_id} does not exist"
        )

    try:
        delete_user_group(db_session=db_session, group=group)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/admin/groups/{user_group_id}/agents")
def patch_group_agents(
    user_group_id: int,
    update_request: UpdateGroupAgentsRequest,
    _: User = Depends(require_permission(Permission.FULL_ADMIN_PANEL_ACCESS)),
    db_session: Session = Depends(get_session),
) -> None:
    update_group_agent_sharing(
        db_session=db_session,
        group_id=user_group_id,
        added_agent_ids=update_request.added_agent_ids,
        removed_agent_ids=update_request.removed_agent_ids,
    )
