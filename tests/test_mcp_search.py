from leocoder.mcp.search import (
    MCP_TOOL_SEARCH_LIMIT,
    McpSearchEntry,
    create_mcp_tool_search,
    search_mcp_tools,
)
from leocoder.providers.types import ToolDefinition

def _entry(server: str, tool: str, description: str) -> McpSearchEntry:
    return McpSearchEntry(
        server=server,
        tool=tool,
        definition=ToolDefinition(
            name=f"mcp__{server}__{tool}",
            description=description,
            parameters={"type": "object", "properties": {}},
        ),
    )


def test_search_mcp_tools_prefers_exact_name_then_name_server_and_description() -> None:
    entries = (
        _entry("github", "get_pull_request", "Read one pull request."),
        _entry("github", "search_pull_requests", "Search pull requests."),
        _entry("tracker", "lookup", "Get a GitHub pull request."),
    )

    matches = search_mcp_tools(entries, "get pull request")

    assert [item.tool for item in matches] == [
        "get_pull_request",
        "search_pull_requests",
        "lookup",
    ]


def test_search_mcp_tools_is_stable_and_limited() -> None:
    entries = tuple(
        _entry("demo", f"lookup_{index:02d}", "Lookup records.")
        for index in reversed(range(20))
    )

    matches = search_mcp_tools(entries, "lookup")

    assert len(matches) == MCP_TOOL_SEARCH_LIMIT == 8
    assert [item.definition.name for item in matches] == sorted(
        item.definition.name for item in matches
    )


def test_mcp_tool_search_returns_activated_names_without_executing_mcp() -> None:
    entries = (_entry("github", "get_issue", "Read one issue."),)
    tool = create_mcp_tool_search(entries)

    result = tool.executor(query="read github issue")

    assert result.ok is True
    assert result.data["mcp_tool_search"]["activated_tools"] == [
        "mcp__github__get_issue"
    ]
    assert "mcp__github__get_issue" in result.content
    assert tool.permission is None
    assert tool.definition.parameters["required"] == ["query"]
    assert tool.definition.parameters["additionalProperties"] is False


def test_mcp_tool_search_blank_query_lists_all_tools() -> None:
    tool = create_mcp_tool_search(
        (
            _entry("github", "get_issue", "Read one issue."),
            _entry("github", "close_issue", "Close one issue."),
        )
    )

    blank = tool.executor(query="   ")

    assert blank.ok is True
    assert blank.data["mcp_tool_search"]["activated_tools"] == [
        "mcp__github__get_issue",
        "mcp__github__close_issue",
    ]
    assert "Connected MCP tools (2)" in blank.content
    assert "mcp__github__get_issue" in blank.content
    assert "mcp__github__close_issue" in blank.content


def test_mcp_tool_search_list_query_lists_all_tools() -> None:
    tool = create_mcp_tool_search(
        (_entry("github", "get_issue", "Read one issue."),)
    )

    result = tool.executor(query="list")

    assert result.ok is True
    assert result.data["mcp_tool_search"]["activated_tools"] == [
        "mcp__github__get_issue"
    ]
    assert "Connected MCP tools (1)" in result.content


def test_mcp_tool_search_lists_only_first_limit_schemas() -> None:
    entries = tuple(
        _entry("demo", f"lookup_{index:02d}", "Lookup records.")
        for index in range(12)
    )
    tool = create_mcp_tool_search(entries)

    result = tool.executor(query="all")

    assert result.ok is True
    assert len(result.data["mcp_tool_search"]["activated_tools"]) == MCP_TOOL_SEARCH_LIMIT
    assert "Connected MCP tools (12)" in result.content
    assert "共 12 个" in result.content


def test_mcp_tool_search_empty_catalog_lists_nothing() -> None:
    tool = create_mcp_tool_search(())

    result = tool.executor(query="")

    assert result.ok is True
    assert result.data["mcp_tool_search"]["activated_tools"] == []
    assert result.content == "No connected MCP tools."


def test_mcp_tool_search_no_match_reports_connected_names() -> None:
    tool = create_mcp_tool_search(
        (_entry("github", "get_issue", "Read one issue."),)
    )

    missing = tool.executor(query="calendar event")

    assert missing.ok is True
    assert missing.data["mcp_tool_search"]["activated_tools"] == []
    assert "No matching MCP tools found" in missing.content
    assert "Connected tools: mcp__github__get_issue" in missing.content


def test_mcp_tool_search_list_like_query_still_searches() -> None:
    """包含 list 但不等于触发词的查询仍走能力匹配，避免误判为列举。"""

    tool = create_mcp_tool_search(
        (_entry("github", "get_issue", "Read one issue."),)
    )

    result = tool.executor(query="list available MCP tools")

    assert result.ok is True
    assert result.data["mcp_tool_search"]["activated_tools"] == []
    assert "No matching MCP tools found" in result.content
    assert "Connected tools: mcp__github__get_issue" in result.content
