"""`write` 工具。"""

from __future__ import annotations

from pathlib import Path

from leocoder.permissions.types import PermissionAction
from leocoder.tools.types import Tool, ToolPermissionSpec, ToolResult, make_error_result, make_text_result
from leocoder.utils.introspection import tool_from_function
from leocoder.utils.sandbox import PathSandbox
from leocoder.utils.sandbox_access import SandboxAccess


def create_write_tool(root: str | Path, *, access: SandboxAccess | None = None) -> Tool:
    """创建写入文本文件的工具。"""

    sandbox = PathSandbox(root, access=access)

    def write(path: str, content: str, create_dirs: bool = True, overwrite: bool = True) -> ToolResult:
        """写入项目内 UTF-8 文本文件；可创建目录或覆盖文件。

        Args:
            path: 目标文件路径，相对项目根。
            content: 要写入的完整 UTF-8 文本内容。
            create_dirs: 父目录不存在时是否自动创建。
            overwrite: 目标已存在时是否允许覆盖。
        """

        target = sandbox.resolve(path)
        if target.exists() and target.is_dir():
            return make_error_result("write", f"路径是目录，不能写入文件：{path}")
        if target.exists() and not overwrite:
            return make_error_result("write", f"文件已存在且 overwrite 为 False：{path}")

        parent = target.parent
        if not parent.exists():
            if not create_dirs:
                return make_error_result("write", f"父目录不存在：{sandbox.relative(parent)}")
            parent.mkdir(parents=True, exist_ok=True)

        created = not target.exists()
        target.write_text(content, encoding="utf-8")
        return make_text_result(
            "write",
            f"已写入文件：{sandbox.relative(target)}",
            path=sandbox.relative(target),
            bytes_written=len(content.encode("utf-8")),
            created=created,
        )

    tool = tool_from_function(write)
    tool.permission = ToolPermissionSpec(
        action=PermissionAction.WRITE_PATH,
        target_arg="path",
        reason="写入文件需要用户确认。",
    )
    return tool
