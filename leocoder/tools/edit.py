"""`edit` 工具。"""

from __future__ import annotations

from pathlib import Path

from leocoder.permissions.types import PermissionAction
from leocoder.tools.types import Tool, ToolPermissionSpec, ToolResult, make_error_result, make_text_result
from leocoder.utils.introspection import tool_from_function
from leocoder.utils.sandbox import PathSandbox
from leocoder.utils.sandbox_access import SandboxAccess
from leocoder.utils.text import safe_read_text


def create_edit_tool(root: str | Path, *, access: SandboxAccess | None = None) -> Tool:
    """创建替换文本片段的工具。"""

    sandbox = PathSandbox(root, access=access)

    def edit(path: str, old: str, new: str, replace_all: bool = False) -> ToolResult:
        """替换项目内 UTF-8 文本片段；默认只替换唯一匹配。

        Args:
            path: 目标文件路径，相对项目根；必须是已存在的文本文件。
            old: 要被替换的原文片段，不能为空。
            new: 替换后的新文本。
            replace_all: 为 true 时替换全部匹配，否则要求 old 只匹配一次。
        """

        try:
            target = sandbox.resolve_validated(path, expect="file")
        except ValueError as exc:
            return make_error_result("edit", str(exc))
        if old == "":
            return make_error_result("edit", "old 不能为空")

        try:
            text = safe_read_text(target)
        except UnicodeDecodeError:
            return make_error_result("edit", f"文件不是 UTF-8 文本或无法作为文本读取：{path}")

        count = text.count(old)
        if count == 0:
            return make_error_result("edit", "没有找到匹配内容")
        if count > 1 and not replace_all:
            return make_error_result("edit", f"匹配内容出现 {count} 次；请提供更精确的 old，或启用 replace_all")

        new_text = text.replace(old, new) if replace_all else text.replace(old, new, 1)
        replacements = count if replace_all else 1
        target.write_text(new_text, encoding="utf-8")

        return make_text_result(
            "edit",
            f"已编辑文件：{sandbox.relative(target)}",
            path=sandbox.relative(target),
            replacements=replacements,
        )

    tool = tool_from_function(edit)
    tool.permission = ToolPermissionSpec(
        action=PermissionAction.WRITE_PATH,
        target_arg="path",
        reason="编辑文件需要用户确认。",
    )
    return tool
