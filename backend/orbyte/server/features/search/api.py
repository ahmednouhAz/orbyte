"""Search API endpoint (POST /api/search).

Runs the full SearchTool.run() pipeline — the same multi-stage search that
powers chat mode. Returns ranked results without generating an LLM answer.

Intended for programmatic consumers (orbyte-cli, Craft sandbox, integrations).

Not the same as the Orbyte Search UI backend at /api/search/send-search-message
(ee/orbyte/server/query_and_chat/search_backend.py), which calls search_pipeline()
directly — a lighter-weight flow with optional query expansion.
"""

import json
from typing import cast

from fastapi import APIRouter
from fastapi import Depends
from sqlalchemy.orm import Session

from orbyte.auth.permissions import require_permission
from orbyte.auth.schemas import UserRole
from orbyte.chat.emitter import NullEmitter
from orbyte.configs.constants import MessageType
from orbyte.context.search.models import BaseFilters
from orbyte.context.search.models import PersonaSearchInfo
from orbyte.context.search.models import TimeRange
from orbyte.db.engine.sql_engine import get_session
from orbyte.db.enums import Permission
from orbyte.db.llm import can_user_access_llm_provider
from orbyte.db.llm import fetch_existing_llm_provider
from orbyte.db.llm import fetch_user_group_ids
from orbyte.db.models import User
from orbyte.db.persona import get_persona_by_id
from orbyte.db.search_settings import get_current_search_settings
from orbyte.db.tools import get_tools
from orbyte.document_index.factory import get_default_document_index
from orbyte.error_handling.error_codes import OrbyteErrorCode
from orbyte.error_handling.exceptions import OrbyteError
from orbyte.llm.factory import get_default_llm
from orbyte.llm.factory import get_llm_for_persona
from orbyte.llm.factory import llm_from_provider
from orbyte.server.features.search.models import SearchRequest
from orbyte.server.features.search.models import SearchResponse
from orbyte.server.features.search.models import SearchResult
from orbyte.server.manage.llm.models import LLMProviderView
from orbyte.server.query_and_chat.placement import Placement
from orbyte.server.settings.store import load_settings
from orbyte.server.usage_limits import check_llm_cost_limit_for_provider
from orbyte.server.utils_vector_db import require_vector_db
from orbyte.tools.constants import SEARCH_TOOL_ID
from orbyte.tools.models import ChatMinimalTextMessage
from orbyte.tools.models import SearchToolOverrideKwargs
from orbyte.tools.tool_implementations.search.search_tool import SearchTool
from shared_configs.contextvars import get_current_tenant_id

router = APIRouter(prefix="/search")


@router.post("", dependencies=[Depends(require_vector_db)])
def search(
    request: SearchRequest,
    user: User = Depends(require_permission(Permission.READ_SEARCH)),
    db_session: Session = Depends(get_session),
) -> SearchResponse:
    # 1. Load persona
    persona = None
    if request.persona_id is not None:
        try:
            persona = get_persona_by_id(
                persona_id=request.persona_id,
                user=user,
                db_session=db_session,
                is_for_edit=False,
            )
        except ValueError:
            raise OrbyteError(OrbyteErrorCode.PERSONA_NOT_FOUND)

        persona_search_info = PersonaSearchInfo(
            document_set_names=[ds.name for ds in persona.document_sets],
            search_start_date=persona.search_start_date,
            attached_document_ids=[doc.id for doc in persona.attached_documents],
            hierarchy_node_ids=[node.id for node in persona.hierarchy_nodes],
        )
    else:
        persona_search_info = PersonaSearchInfo(
            document_set_names=[],
            search_start_date=None,
            attached_document_ids=[],
            hierarchy_node_ids=[],
        )

    # 2. Get LLM
    if request.provider:
        provider_model = fetch_existing_llm_provider(request.provider, db_session)
        if not provider_model:
            raise OrbyteError(
                OrbyteErrorCode.NOT_FOUND,
                f"LLM provider '{request.provider}' not found",
            )
        user_group_ids = fetch_user_group_ids(db_session, user)
        if not can_user_access_llm_provider(
            provider_model,
            user_group_ids,
            persona,
            user.role == UserRole.ADMIN,
        ):
            raise OrbyteError(OrbyteErrorCode.UNAUTHORIZED)

        llm_provider_view = LLMProviderView.from_model(provider_model)
        llm = llm_from_provider(
            model_name=cast(str, request.model),
            llm_provider=llm_provider_view,
        )
    elif persona is not None:
        llm = get_llm_for_persona(persona, user)
    else:
        llm = get_default_llm()

    # Since the agentic search flow requires multiple LLM calls
    # we should check the tenant usage limits before continuing
    check_llm_cost_limit_for_provider(
        db_session=db_session,
        tenant_id=get_current_tenant_id(),
        llm_provider_api_key=llm.config.api_key,
    )

    # 3. Build filters. The public time_cutoff maps onto the internal
    # updated_at_range lower bound; TimeRange coerces naive bounds to UTC.
    base_filters = BaseFilters(
        source_type=request.sources,
        document_set=request.document_sets,
        updated_at_range=(
            TimeRange(start=request.time_cutoff)
            if request.time_cutoff is not None
            else None
        ),
        tags=request.tags,
    )

    # 4. Get document index
    search_settings = get_current_search_settings(db_session)
    document_index = get_default_document_index(search_settings, None, db_session)

    # 5. Get tool_id
    all_tools = get_tools(db_session)
    tool_id = next(
        (tool.id for tool in all_tools if tool.in_code_tool_id == SEARCH_TOOL_ID),
        None,
    )
    if tool_id is None:
        raise OrbyteError(
            OrbyteErrorCode.NOT_FOUND,
            "Search tool not found in database",
        )

    # 6. Construct SearchTool
    search_tool = SearchTool(
        tool_id=tool_id,
        emitter=NullEmitter(),
        user=user,
        persona_search_info=persona_search_info,
        llm=llm,
        document_index=document_index,
        user_selected_filters=base_filters,
        project_id_filter=None,
        persona_id_filter=None,
        bypass_acl=False,
        slack_context=None,
        enable_slack_search=True,
        auto_detect_filters=load_settings().auto_detect_search_filters is not False,
    )

    # 7. Run search
    tool_response = search_tool.run(
        placement=Placement(turn_index=0),
        override_kwargs=SearchToolOverrideKwargs(
            starting_citation_num=1,
            original_query=request.query,
            skip_query_expansion=request.skip_query_expansion,
            include_link=True,
            message_history=request.message_history
            or [
                ChatMinimalTextMessage(
                    message=request.query,
                    message_type=MessageType.USER,
                ),
            ],
        ),
        queries=[request.query],
    )

    # 8. Map LLM-facing JSON entries to SearchResults (one per merged section).
    llm_facing_text = tool_response.llm_facing_response
    entries = json.loads(llm_facing_text)["results"] if llm_facing_text else []
    return SearchResponse(
        results=[
            SearchResult(
                citation_id=entry["document"],
                title=entry["title"],
                content=entry["content"],
                link=entry.get("url"),
                source_type=entry["source_type"],
                updated_at=entry.get("updated_at"),
            )
            for entry in entries
        ],
    )
