"""内置工具集合。"""

from __future__ import annotations

from pathlib import Path

from leocoder.tools.apply_patch import create_apply_patch_tool
from leocoder.tools.ask_user import create_ask_user_tool
from leocoder.tools.edit import create_edit_tool
from leocoder.tools.delete import create_delete_tool
from leocoder.tools.diagnostics import create_diagnostics_tool
from leocoder.tools.git_diff import create_git_diff_tool
from leocoder.tools.git_log import create_git_log_tool
from leocoder.tools.git_status import create_git_status_tool
from leocoder.tools.fetch import create_fetch_tool
from leocoder.tools.glob import create_glob_tool
from leocoder.tools.grep import create_grep_tool
from leocoder.tools.ls import create_ls_tool
from leocoder.tools.python_exec import create_python_exec_tool
from leocoder.tools.read_multi import create_read_multi_tool
from leocoder.tools.registry import ToolRegistry
from leocoder.tools.think import create_think_tool
from leocoder.tools.shell import create_shell_tool
from leocoder.tools.tree import create_tree_tool
from leocoder.tools.view import create_view_tool
from leocoder.tools.web_search import create_web_search_tool
from leocoder.tools.write import create_write_tool
from leocoder.tools.descriptions import apply_agent_tool_description
from leocoder.utils.sandbox_access import SandboxAccess
from leocoder.tools.get_time import create_get_time_tool

def create_builtin_registry(
    root: str | Path,
    include_mutation_tools: bool = False,
    include_execution_tools: bool = False,
    include_network_tools: bool = False,
    access: SandboxAccess | None = None,
) -> ToolRegistry:
    """创建第一阶段默认可用工具。

    默认只注册只读工具。写入类工具必须显式启用，方便后续接确认机制。
    """

    tools = [
        create_ls_tool(root, access=access),
        create_view_tool(root, access=access),
        create_grep_tool(root, access=access),
        create_glob_tool(root, access=access),
        create_tree_tool(root, access=access),
        create_git_status_tool(root, access=access),
        create_git_diff_tool(root, access=access),
        create_git_log_tool(root, access=access),
        create_diagnostics_tool(root, access=access),
        create_think_tool(),
        create_read_multi_tool(root, access=access),
        create_ask_user_tool(),
        create_get_time_tool(),
    ]
    if include_mutation_tools:
        tools.extend(
            [
                create_write_tool(root, access=access),
                create_edit_tool(root, access=access),
                create_delete_tool(root, access=access),
                create_apply_patch_tool(root, access=access),
            ]
        )
    if include_execution_tools:
        tools.extend(
            [
                create_shell_tool(root, access=access),
                create_python_exec_tool(root, access=access),
            ]
        )
    if include_network_tools:
        tools.extend(
            [
                create_fetch_tool(),
                create_web_search_tool(),
            ]
        )
    return ToolRegistry([apply_agent_tool_description(tool) for tool in tools])
