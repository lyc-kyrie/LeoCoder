"""`get_time` 工具。"""

from __future__ import annotations

import time

from leocoder.tools.types import Tool, ToolResult, make_error_result, make_text_result
from leocoder.utils.introspection import tool_from_function


def create_get_time_tool() -> Tool:
    """创建获取当前时间工具。"""

    def get_time() -> ToolResult:
        """返回当前日期时间；当需要知道今天是几号时使用。"""
        try:
            content = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        except Exception as exc:
            return make_error_result("get_time", str(exc))
        return make_text_result("get_time", content, iso=content)

    return tool_from_function(get_time)