"""LeoCoder 自带的参考 MCP server（stdio 传输）。

存在的理由是：让 MCP 链路在**没有网络、没有第三方进程**的前提下也能被端到端验证。
在配置里写一段 ``[mcp.devtools]`` 指向 ``python -m leocoder.mcp.example_server``，
就能观察完整流程：连接握手 → list_tools → mcp_tool_search 激活 → 权限确认 →
call_tool → 结果投影。没有可验证的 server，MCP 实现就只是纸面能力。

工具刻意只做纯计算：不读写文件、不访问网络、不起子进程，并对输入长度和输出规模设
上限。这样它既能当 self-check 底座，也不会因为一个模型构造的正则表达式把宿主进程
拖进灾难性回溯。
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import re
import uuid
from typing import Literal

from mcp.server.fastmcp import FastMCP

# 单次输入上限：足够覆盖真实使用，同时给 stdio 管道一个确定的边界。
MAX_TEXT_CHARS = 64 * 1024
MAX_UUID_COUNT = 32
MAX_REGEX_MATCHES = 200

mcp = FastMCP("devtools")

TOOL_NAMES = ("server_info", "hash_text", "base64_codec", "regex_find", "uuid_generate")


@mcp.tool()
def server_info() -> str:
    """返回本 server 的身份与能力，用于连接自检。"""

    return "\n".join(
        [
            "name: devtools",
            "transport: stdio",
            "capabilities: tools",
            f"tools: {', '.join(TOOL_NAMES)}",
        ]
    )


@mcp.tool()
def hash_text(
    text: str,
    algorithm: Literal["md5", "sha1", "sha256", "sha512"] = "sha256",
) -> str:
    """计算文本的密码学摘要。

    Args:
        text: 待计算摘要的文本，按 UTF-8 编码，最长 64 KiB。
        algorithm: 摘要算法，默认 sha256。
    """

    _require_text(text)
    digest = hashlib.new(algorithm, text.encode("utf-8")).hexdigest()
    return f"{algorithm}:{digest}"


@mcp.tool()
def base64_codec(
    data: str,
    mode: Literal["encode", "decode"] = "encode",
    url_safe: bool = False,
) -> str:
    """Base64 编码或解码。

    Args:
        data: 编码时为原始文本，解码时为 base64 字符串，最长 64 KiB。
        mode: ``encode`` 或 ``decode``，默认 ``encode``。
        url_safe: 是否使用 URL 安全字母表（``-`` 和 ``_``），默认 False。
    """

    _require_text(data)
    if mode == "encode":
        raw = base64.urlsafe_b64encode(data.encode("utf-8")) if url_safe else base64.b64encode(data.encode("utf-8"))
        return raw.decode("ascii")
    try:
        decoded = base64.urlsafe_b64decode(data) if url_safe else base64.b64decode(data, validate=True)
    except (binascii.Error, ValueError) as error:
        raise ValueError(f"base64 解码失败：{error}") from error
    return decoded.decode("utf-8", errors="replace")


@mcp.tool()
def regex_find(
    pattern: str,
    text: str,
    max_matches: int = 20,
) -> str:
    """列出正则在文本中的全部匹配及其位置，用于快速核对正则行为。

    Args:
        pattern: Python ``re`` 语法，非法时返回错误结果而不是抛异常。
        text: 待匹配的文本，最长 64 KiB。
        max_matches: 最多返回多少条匹配，默认 20，上限 200。
    """

    _require_text(text)
    if not 1 <= max_matches <= MAX_REGEX_MATCHES:
        raise ValueError(f"max_matches 必须在 1 到 {MAX_REGEX_MATCHES} 之间")
    try:
        compiled = re.compile(pattern)
    except re.error as error:
        raise ValueError(f"无效正则：{error}") from error

    found: list[str] = []
    for index, match in enumerate(compiled.finditer(text)):
        if index >= max_matches:
            found.append(f"…（已截断，只展示前 {max_matches} 条）")
            break
        found.append(f"{index}: [{match.start()},{match.end()}) {match.group(0)!r}")
    return "\n".join(found) if found else "无匹配"


@mcp.tool()
def uuid_generate(count: int = 1) -> str:
    """生成随机 UUID v4，每行一个。

    Args:
        count: 生成个数，默认 1，上限 32。
    """

    if not 1 <= count <= MAX_UUID_COUNT:
        raise ValueError(f"count 必须在 1 到 {MAX_UUID_COUNT} 之间")
    return "\n".join(str(uuid.uuid4()) for _ in range(count))


def _require_text(value: str) -> None:
    if len(value) > MAX_TEXT_CHARS:
        raise ValueError(f"输入超过 {MAX_TEXT_CHARS} 字符上限")


def main() -> None:
    """以 stdio 传输启动 server，供 ``python -m leocoder.mcp.example_server`` 调用。"""

    mcp.run()


if __name__ == "__main__":
    main()
