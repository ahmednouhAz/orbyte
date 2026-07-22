from pydantic import BaseModel
from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from sqlalchemy.orm import Session

from orbyte.auth.users import current_curator_or_admin_user
from orbyte.db.engine.sql_engine import get_session
from orbyte.db.enums import Permission
from orbyte.auth.permissions import require_permission
from orbyte.db.models import User
from orbyte.db.tools import get_tool_by_id
from orbyte.db.tools import get_tools
from orbyte.db.tools import get_tools_by_ids
from orbyte.server.features.tool.models import ToolSnapshot
from orbyte.server.features.tool.tool_visibility import should_expose_tool_to_fe
from orbyte.tools.built_in_tools import get_built_in_tool_by_id

router = APIRouter(prefix="/tool")
admin_router = APIRouter(prefix="/admin/tool")


class ToolStatusUpdateRequest(BaseModel):
    tool_ids: list[int]
    enabled: bool


class ToolStatusUpdateResponse(BaseModel):
    updated_count: int
    tool_ids: list[int]


@admin_router.patch("/status")
def update_tools_status(
    update_data: ToolStatusUpdateRequest,
    db_session: Session = Depends(get_session),
    user: User = Depends(current_curator_or_admin_user),  # noqa: ARG001
) -> ToolStatusUpdateResponse:
    """Enable or disable one or more tools.

    Pass a single tool ID in the list to update one tool, or multiple IDs for
    bulk updates.
    """
    if not update_data.tool_ids:
        raise HTTPException(status_code=400, detail="No tool IDs provided")

    tools = get_tools_by_ids(update_data.tool_ids, db_session)
    tools_by_id = {tool.id: tool for tool in tools}

    updated_tools = []
    missing_tools = []

    for tool_id in update_data.tool_ids:
        tool = tools_by_id.get(tool_id)
        if tool:
            tool.enabled = update_data.enabled
            updated_tools.append(tool_id)
        else:
            missing_tools.append(tool_id)

    if missing_tools:
        raise HTTPException(
            status_code=404, detail=f"Tools with IDs {missing_tools} not found"
        )

    db_session.commit()

    return ToolStatusUpdateResponse(
        updated_count=len(updated_tools),
        tool_ids=updated_tools,
    )


@router.get("/{tool_id}")
def get_custom_tool(
    tool_id: int,
    db_session: Session = Depends(get_session),
    _: User = Depends(require_permission(Permission.BASIC_ACCESS)),
) -> ToolSnapshot:
    try:
        tool = get_tool_by_id(tool_id, db_session)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return ToolSnapshot.from_model(tool)


@router.get("")
def list_tools(
    db_session: Session = Depends(get_session),
    _: User = Depends(require_permission(Permission.BASIC_ACCESS)),
) -> list[ToolSnapshot]:
    tools = get_tools(db_session, only_enabled=True, only_connected_mcp=True)

    filtered_tools: list[ToolSnapshot] = []
    for tool in tools:
        if not should_expose_tool_to_fe(tool):
            continue

        # Check if it's a built-in tool and if it's available
        if tool.in_code_tool_id:
            try:
                tool_cls = get_built_in_tool_by_id(tool.in_code_tool_id)
                if not tool_cls.is_available(db_session):
                    continue
            except KeyError:
                # If tool ID not found in registry, include it by default
                pass

        filtered_tools.append(ToolSnapshot.from_model(tool))

    return filtered_tools
