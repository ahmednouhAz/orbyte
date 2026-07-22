from uuid import UUID

from pydantic import BaseModel
from sqlalchemy.orm import Session

from orbyte.chat.emitter import Emitter
from orbyte.configs.app_configs import DISABLE_VECTOR_DB
from orbyte.context.search.models import BaseFilters
from orbyte.context.search.models import PersonaSearchInfo
from orbyte.db.engine.sql_engine import get_session_with_current_tenant_if_none
from orbyte.db.models import Persona
from orbyte.db.models import User
from orbyte.db.search_settings import get_current_search_settings
from orbyte.db.tools import get_builtin_tool
from orbyte.document_index.factory import get_default_document_index
from orbyte.llm.interfaces import LLM
from orbyte.orbytebot.slack.models import SlackContext
from orbyte.tools.built_in_tools import get_built_in_tool_by_id
from orbyte.tools.interface import Tool
from orbyte.tools.models import SearchToolUsage
from orbyte.tools.tool_implementations.coding_agent.coding_agent_tool import (
    CodingAgentTool,
)
from orbyte.tools.tool_implementations.file_reader.file_reader_tool import FileReaderTool
from orbyte.tools.tool_implementations.memory.memory_tool import MemoryTool
from orbyte.tools.tool_implementations.open_url.open_url_tool import OpenURLTool
from orbyte.tools.tool_implementations.search.search_tool import SearchTool
from orbyte.tools.tool_implementations.web_search.web_search_tool import WebSearchTool
from orbyte.utils.logger import setup_logger

logger = setup_logger()


class SearchToolConfig(BaseModel):
    user_selected_filters: BaseFilters | None = None
    # Vespa metadata filters for overflowing user files.  These are NOT the
    # IDs of the current project/persona — they are only set when the
    # project's/persona's user files didn't fit in the LLM context window and
    # must be found via vector DB search instead.
    project_id_filter: int | None = None
    persona_id_filter: int | None = None
    bypass_acl: bool = False
    additional_context: str | None = None
    slack_context: SlackContext | None = None
    enable_slack_search: bool = True
    auto_detect_filters: bool = True


class FileReaderToolConfig(BaseModel):
    # IDs from the ``user_file`` table (project / persona-attached files).
    user_file_ids: list[UUID] = []
    # IDs from the ``file_record`` table (chat-attached files).
    chat_file_ids: list[UUID] = []


def construct_tools(
    persona: Persona,
    emitter: Emitter,
    user: User,
    llm: LLM,
    db_session: Session | None = None,
    search_tool_config: SearchToolConfig | None = None,
    file_reader_tool_config: FileReaderToolConfig | None = None,
    allowed_tool_ids: list[int] | None = None,
    search_usage_forcing_setting: SearchToolUsage = SearchToolUsage.AUTO,
) -> dict[int, list[Tool]]:
    """Constructs tools based on persona configuration and available APIs.

    Will simply skip tools that are not allowed/available.

    Callers must supply a persona with ``tools``, ``document_sets``,
    ``attached_documents``, and ``hierarchy_nodes`` already eager-loaded
    (e.g. via ``eager_load_persona=True`` or ``eager_load_for_tools=True``)
    to avoid lazy SQL queries after the session may have been flushed."""
    with get_session_with_current_tenant_if_none(db_session) as db_session:
        return _construct_tools_impl(
            persona=persona,
            db_session=db_session,
            emitter=emitter,
            user=user,
            llm=llm,
            search_tool_config=search_tool_config,
            file_reader_tool_config=file_reader_tool_config,
            allowed_tool_ids=allowed_tool_ids,
            search_usage_forcing_setting=search_usage_forcing_setting,
        )


def _construct_tools_impl(
    persona: Persona,
    db_session: Session,
    emitter: Emitter,
    user: User,
    llm: LLM,
    search_tool_config: SearchToolConfig | None = None,
    file_reader_tool_config: FileReaderToolConfig | None = None,
    allowed_tool_ids: list[int] | None = None,
    search_usage_forcing_setting: SearchToolUsage = SearchToolUsage.AUTO,
) -> dict[int, list[Tool]]:
    tool_dict: dict[int, list[Tool]] = {}

    # Log which tools are attached to the persona for debugging
    persona_tool_names = [t.name for t in persona.tools]
    logger.debug(
        "Constructing tools for persona '%s' (id=%s): %s",
        persona.name,
        persona.id,
        persona_tool_names,
    )

    search_settings = get_current_search_settings(db_session)
    # This flow is for search so we do not get all indices.
    document_index = get_default_document_index(search_settings, None, db_session)

    def _build_search_tool(tool_id: int, config: SearchToolConfig) -> SearchTool:
        persona_search_info = PersonaSearchInfo(
            document_set_names=[ds.name for ds in persona.document_sets],
            search_start_date=persona.search_start_date,
            attached_document_ids=[doc.id for doc in persona.attached_documents],
            hierarchy_node_ids=[node.id for node in persona.hierarchy_nodes],
        )
        return SearchTool(
            tool_id=tool_id,
            emitter=emitter,
            user=user,
            persona_search_info=persona_search_info,
            llm=llm,
            document_index=document_index,
            user_selected_filters=config.user_selected_filters,
            project_id_filter=config.project_id_filter,
            persona_id_filter=config.persona_id_filter,
            bypass_acl=config.bypass_acl,
            slack_context=config.slack_context,
            enable_slack_search=config.enable_slack_search,
            auto_detect_filters=config.auto_detect_filters,
        )

    added_search_tool = False
    for db_tool_model in persona.tools:
        # If allowed_tool_ids is specified, skip tools not in the allowed list
        if allowed_tool_ids is not None and db_tool_model.id not in allowed_tool_ids:
            continue

        if not db_tool_model.in_code_tool_id:
            # Custom/OpenAPI tools and MCP tools have been removed from this
            # deployment — any persisted persona tool that isn't a built-in
            # (in-code) tool is silently skipped.
            continue

        try:
            tool_cls = get_built_in_tool_by_id(db_tool_model.in_code_tool_id)
        except KeyError:
            # This persona (often a pre-existing seeded/default one) still has
            # a DB row referencing a built-in tool that has since been removed
            # from this deployment (e.g. ImageGenerationTool, PythonTool,
            # KnowledgeGraphTool). Skip it rather than crash the whole chat
            # turn — the persona simply loses access to that specific tool.
            logger.debug(
                "Skipping unknown/removed built-in tool id %s on persona %s",
                db_tool_model.in_code_tool_id,
                persona.id,
            )
            continue

        try:
            tool_is_available = tool_cls.is_available(db_session)
        except Exception:
            logger.exception(
                "Failed checking availability for tool %s", tool_cls.__name__
            )
            tool_is_available = False

        if not tool_is_available:
            logger.debug(
                "Skipping tool %s because it is not available",
                tool_cls.__name__,
            )
            continue

        # Handle Internal Search Tool
        if tool_cls.__name__ == SearchTool.__name__:
            added_search_tool = True
            if search_usage_forcing_setting == SearchToolUsage.DISABLED:
                continue

            if not search_tool_config:
                search_tool_config = SearchToolConfig()

            tool_dict[db_tool_model.id] = [
                _build_search_tool(db_tool_model.id, search_tool_config)
            ]

        # Handle Web Search Tool
        elif tool_cls.__name__ == WebSearchTool.__name__:
            try:
                tool_dict[db_tool_model.id] = [
                    WebSearchTool(tool_id=db_tool_model.id, emitter=emitter)
                ]
            except ValueError as e:
                logger.error("Failed to initialize Internet Search Tool: %s", e)
                raise ValueError(
                    "Internet search tool requires a search provider API key, please contact your Orbyte admin to get it added!"
                )

        # Handle Open URL Tool
        elif tool_cls.__name__ == OpenURLTool.__name__:
            try:
                tool_dict[db_tool_model.id] = [
                    OpenURLTool(
                        tool_id=db_tool_model.id,
                        emitter=emitter,
                        document_index=document_index,
                        user=user,
                    )
                ]
            except RuntimeError as e:
                logger.error("Failed to initialize Open URL Tool: %s", e)
                raise ValueError(
                    "Open URL tool requires a web content provider, please contact your Orbyte admin to get it configured!"
                )

        # Handle Coding Agent Tool
        elif tool_cls.__name__ == CodingAgentTool.__name__:
            tool_dict[db_tool_model.id] = [
                CodingAgentTool(
                    tool_id=db_tool_model.id,
                    emitter=emitter,
                    llm=llm,
                )
            ]

        # Handle File Reader Tool
        elif tool_cls.__name__ == FileReaderTool.__name__:
            cfg = file_reader_tool_config or FileReaderToolConfig()
            tool_dict[db_tool_model.id] = [
                FileReaderTool(
                    tool_id=db_tool_model.id,
                    emitter=emitter,
                    user_file_ids=cfg.user_file_ids,
                    chat_file_ids=cfg.chat_file_ids,
                )
            ]

    if (
        not added_search_tool
        and search_usage_forcing_setting == SearchToolUsage.ENABLED
        and not DISABLE_VECTOR_DB
    ):
        # Get the database tool model for SearchTool
        search_tool_db_model = get_builtin_tool(db_session, SearchTool)

        if not search_tool_config:
            search_tool_config = SearchToolConfig()

        tool_dict[search_tool_db_model.id] = [
            _build_search_tool(search_tool_db_model.id, search_tool_config)
        ]

    # Always inject MemoryTool when the user has the memory tool enabled,
    # bypassing persona tool associations and allowed_tool_ids filtering
    if user.enable_memory_tool:
        try:
            memory_tool_db_model = get_builtin_tool(db_session, MemoryTool)
            memory_tool = MemoryTool(
                tool_id=memory_tool_db_model.id,
                emitter=emitter,
                llm=llm,
            )
            tool_dict[memory_tool_db_model.id] = [memory_tool]
        except RuntimeError:
            logger.warning(
                "MemoryTool not found in the database. Run the latest alembic migration to seed it."
            )

    return tool_dict
