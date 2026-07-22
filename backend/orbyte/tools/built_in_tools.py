from typing import Type
from typing import Union

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


BUILT_IN_TOOL_TYPES = Union[
    SearchTool,
    WebSearchTool,
    OpenURLTool,
    FileReaderTool,
    MemoryTool,
    CodingAgentTool,
]

BUILT_IN_TOOL_MAP: dict[str, Type[BUILT_IN_TOOL_TYPES]] = {
    SearchTool.__name__: SearchTool,
    WebSearchTool.__name__: WebSearchTool,
    OpenURLTool.__name__: OpenURLTool,
    FileReaderTool.__name__: FileReaderTool,
    MemoryTool.__name__: MemoryTool,
    CodingAgentTool.__name__: CodingAgentTool,
}

STOPPING_TOOLS_NAMES: list[str] = []
CITEABLE_TOOLS_NAMES: list[str] = [
    SearchTool.NAME,
    WebSearchTool.NAME,
    OpenURLTool.NAME,
]


def get_built_in_tool_ids() -> list[str]:
    return list(BUILT_IN_TOOL_MAP.keys())


def get_built_in_tool_by_id(in_code_tool_id: str) -> Type[BUILT_IN_TOOL_TYPES]:
    return BUILT_IN_TOOL_MAP[in_code_tool_id]


def _build_tool_name_to_class() -> dict[str, Type[BUILT_IN_TOOL_TYPES]]:
    """Build a mapping from LLM-facing tool name to tool class."""
    result: dict[str, Type[BUILT_IN_TOOL_TYPES]] = {}
    for cls in BUILT_IN_TOOL_MAP.values():
        name_attr = cls.__dict__.get("name")
        if isinstance(name_attr, property) and name_attr.fget is not None:
            tool_name = name_attr.fget(cls)
        elif isinstance(name_attr, str):
            tool_name = name_attr
        else:
            raise ValueError(
                f"Built-in tool {cls.__name__} must define a valid LLM-facing tool name"
            )
        result[tool_name] = cls
    return result


TOOL_NAME_TO_CLASS: dict[str, Type[BUILT_IN_TOOL_TYPES]] = _build_tool_name_to_class()
