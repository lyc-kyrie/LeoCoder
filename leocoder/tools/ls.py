"""`ls` 工具。"""

from __future__ import annotations

from pathlib import Path

from leocoder.tools.path_permissions import with_read_permission
from leocoder.tools.types import Tool, ToolResult, make_error_result, make_text_result
from leocoder.utils.introspection import tool_from_function
from leocoder.utils.sandbox import PathSandbox
from leocoder.utils.sandbox_access import SandboxAccess


def create_ls_tool(root: str | Path, *, access: SandboxAccess | None = None) -> Tool:
    """创建列出目录内容的工具。"""

    sandbox = PathSandbox(root, access=access)

    def ls(path: str = ".", recursive: bool = False, max_entries: int = 200) -> ToolResult:
        """列出项目内目录项；只返回名称和文件/目录类型。

        Args:
            path: 目录路径，相对项目根；必须解析到目录。
            recursive: 为 true 时递归列出所有子目录内容。
            max_entries: 最多返回的条目数，必须大于 0；命中上限表示结果被截断。
        """

        try:
            target = sandbox.resolve_validated(path, expect="dir")
        except ValueError as exc:
            return make_error_result("ls", str(exc))
        if max_entries <= 0:
            return make_error_result("ls", "max_entries 必须大于 0")

        pattern = "**/*" if recursive else "*"
        entries = []
        items = sorted(target.glob(pattern), key=lambda item: sandbox.relative(item))
        for item in items:
            if len(entries) >= max_entries:
                break
            relative = sandbox.relative(item)
            entries.append({"path": relative, "type": "dir" if item.is_dir() else "file"})

        lines = [f"{entry['type']}\t{entry['path']}" for entry in entries]
        content = "\n".join(lines) if lines else "目录为空。"
        return make_text_result("ls", content, entries=entries, truncated=len(entries) >= max_entries)

    return with_read_permission(tool_from_function(ls), reason="列出目录需要权限检查。")
