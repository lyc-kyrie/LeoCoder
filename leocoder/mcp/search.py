"""Local discovery for MCP tools that are not exposed in the initial schema set."""

from __future__ import annotations

import re
from dataclasses import dataclass

from leocoder.providers.types import ToolDefinition
from leocoder.tools.types import Tool, ToolResult, make_error_result

MCP_TOOL_SEARCH_NAME = "mcp_tool_search"
MCP_TOOL_SEARCH_LIMIT = 8
# 精确等于这些词（归一化后）时，返回全部已连接工具目录，而不是做能力匹配。
# 只做全等匹配，避免把 "list available MCP tools" 这类真实查询误判成目录列举。
MCP_TOOL_LIST_QUERIES = frozenset(
    {"list", "all", "show", "available", "ls", "目录", "列表", "列出", "全部", "工具列表"}
)
_TOKEN = re.compile(r"[^\W_]+", re.UNICODE)


@dataclass(frozen=True, slots=True)
class McpSearchEntry:
    """A provider-visible MCP definition eligible for local search."""

    server: str
    tool: str
    definition: ToolDefinition


def search_mcp_tools(
    entries: tuple[McpSearchEntry, ...],
    query: str,
) -> tuple[McpSearchEntry, ...]:
    """Return the highest-scoring local MCP matches in deterministic order."""

    normalized_query = _normalize(query)
    query_tokens = set(_tokens(query))
    ranked: list[tuple[int, str, McpSearchEntry]] = []
    for entry in entries:
        score = _score(entry, normalized_query, query_tokens)
        if score > 0:
            ranked.append((-score, entry.definition.name, entry))
    ranked.sort(key=lambda item: (item[0], item[1]))
    return tuple(item[2] for item in ranked[:MCP_TOOL_SEARCH_LIMIT])


def create_mcp_tool_search(entries: tuple[McpSearchEntry, ...]) -> Tool:
    """Create a read-only tool that searches one MCP catalog snapshot."""

    def execute(*, query: str) -> ToolResult:
        if not isinstance(query, str):
            return make_error_result(
                MCP_TOOL_SEARCH_NAME,
                "MCP tool search query must be a string.",
                mcp_tool_search={"activated_tools": []},
            )
        normalized = query.strip().casefold()
        # 空 query 或明确的列举意图：返回全部目录，让模型先知道有哪些工具。
        if not normalized or normalized in MCP_TOOL_LIST_QUERIES:
            return _catalog_result(entries)
        matches = search_mcp_tools(entries, query)
        activated = [entry.definition.name for entry in matches]
        if not activated:
            return _no_match_result(entries)
        return ToolResult(
            name=MCP_TOOL_SEARCH_NAME,
            ok=True,
            content=_render_matches(matches),
            data={"mcp_tool_search": {"activated_tools": activated}},
        )

    return Tool(
        definition=ToolDefinition(
            name=MCP_TOOL_SEARCH_NAME,
            description=(
                "Search connected MCP tools by capability. Matching tool schemas "
                "become available for the remainder of the current user turn. "
                "Use an empty query or \"list\" / \"all\" to see every connected tool."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Describe the external capability or MCP operation needed; empty or \"list\" lists all connected tools.",
                    }
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        ),
        executor=execute,
    )


def _catalog_result(entries: tuple[McpSearchEntry, ...]) -> ToolResult:
    """返回全部已连接工具目录；激活前 MCP_TOOL_SEARCH_LIMIT 个 schema。"""

    if not entries:
        return ToolResult(
            name=MCP_TOOL_SEARCH_NAME,
            ok=True,
            content="No connected MCP tools.",
            data={"mcp_tool_search": {"activated_tools": []}},
        )
    activated = [entry.definition.name for entry in entries[:MCP_TOOL_SEARCH_LIMIT]]
    lines = [f"Connected MCP tools ({len(entries)}):"]
    lines.extend(_render_entry(entry) for entry in entries)
    if len(entries) > MCP_TOOL_SEARCH_LIMIT:
        lines.append(
            f"…（共 {len(entries)} 个，已激活前 {MCP_TOOL_SEARCH_LIMIT} 个的 schema；"
            "其余工具可用更具体的关键词搜索激活）"
        )
    return ToolResult(
        name=MCP_TOOL_SEARCH_NAME,
        ok=True,
        content="\n".join(lines),
        data={"mcp_tool_search": {"activated_tools": activated}},
    )


def _no_match_result(entries: tuple[McpSearchEntry, ...]) -> ToolResult:
    """能力词没有命中时，把目录里的真实工具名告诉模型，避免它误判「没有 MCP」。"""

    names = ", ".join(entry.definition.name for entry in entries)
    if not names:
        return ToolResult(
            name=MCP_TOOL_SEARCH_NAME,
            ok=True,
            content="No matching MCP tools found. Try a more specific capability description.",
            data={"mcp_tool_search": {"activated_tools": []}},
        )
    content = (
        "No matching MCP tools found. Connected tools: "
        f"{names}. Try one of these exact tool names or a more specific "
        "capability description."
    )
    return ToolResult(
        name=MCP_TOOL_SEARCH_NAME,
        ok=True,
        content=content,
        data={"mcp_tool_search": {"activated_tools": []}},
    )


def _score(
    entry: McpSearchEntry,
    normalized_query: str,
    query_tokens: set[str],
) -> int:
    name = _normalize(entry.tool)
    server = _normalize(entry.server)
    description = _normalize(entry.definition.description)
    visible_name = _normalize(entry.definition.name)
    score = 10_000 if normalized_query in {name, visible_name} else 0
    score += 100 * len(query_tokens.intersection(_tokens(name)))
    score += 20 * len(query_tokens.intersection(_tokens(server)))
    score += len(query_tokens.intersection(_tokens(description)))
    return score


def _normalize(value: str | None) -> str:
    return " ".join(_tokens(value or ""))


def _tokens(value: str) -> tuple[str, ...]:
    return tuple(_TOKEN.findall(value.casefold().replace("_", " ").replace("-", " ")))


def _render_matches(matches: tuple[McpSearchEntry, ...]) -> str:
    if not matches:
        return "No matching MCP tools found. Try a more specific capability description."
    lines = ["Matching MCP tools activated for this user turn:"]
    lines.extend(_render_entry(entry) for entry in matches)
    return "\n".join(lines)


def _render_entry(entry: McpSearchEntry) -> str:
    return (
        f"- {entry.definition.name}: {entry.server}/{entry.tool} — "
        f"{' '.join(entry.definition.description.split()) or 'No description provided.'}"
    )
