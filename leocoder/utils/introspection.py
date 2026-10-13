"""根据 Python 函数签名生成工具定义。"""

from __future__ import annotations

import inspect
import re
import types
from collections.abc import Callable
from enum import Enum
from typing import TYPE_CHECKING, Any, Literal, Union, get_args, get_origin, get_type_hints

from leocoder.utils.schema import object_schema, property_schema
from leocoder.providers.types import ToolDefinition

if TYPE_CHECKING:
    from leocoder.tools.types import Tool, ToolResult


PYTHON_TYPE_TO_JSON_TYPE: dict[Any, str] = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    list: "array",
    dict: "object",
    type(None): "null",
}

_ARGS_SECTION_HEADERS = {"args", "arguments", "parameters"}
_SECTION_HEADER_PATTERN = re.compile(r"^\w[\w ]*:\s*$")
_ARG_LINE_PATTERN = re.compile(r"^\s+(\w+)\s*(?:\([^)]*\))?\s*:\s*(.*)$")


def function_to_parameters(func: Callable[..., "ToolResult"]) -> dict[str, Any]:
    """根据函数签名生成工具参数 JSON Schema。

    除了类型映射，还会：
    - 递归展开泛型容器，生成 `items` / `additionalProperties`；
    - 把 `Literal` 与 `Enum` 映射成 `enum` 约束；
    - `Optional[X]` 归一成 `X`，多分支 `Union` 生成 `anyOf`；
    - 把 JSON 兼容的默认值写进 `default`；
    - 从 Google 风格 `Args:` 段提取参数级 description。
    """

    signature = inspect.signature(func)
    type_hints = get_type_hints(func)
    param_descriptions = _parse_docstring_params(func)
    properties: dict[str, dict[str, Any]] = {}
    required: list[str] = []

    for parameter in signature.parameters.values():
        if parameter.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
            raise ValueError(f"不支持可变参数：{parameter.name}")

        if parameter.name in {"self", "cls"}:
            continue

        annotation = type_hints.get(parameter.name, parameter.annotation)
        schema = _annotation_to_schema(annotation)
        description = param_descriptions.get(parameter.name)
        if description:
            schema["description"] = description
        if parameter.default is inspect.Signature.empty:
            required.append(parameter.name)
        elif _is_json_compatible_default(parameter.default):
            schema["default"] = parameter.default
        properties[parameter.name] = schema

    return object_schema(properties, required=required)


def tool_from_function(
    func: Callable[..., "ToolResult"],
    *,
    name: str | None = None,
    description: str | None = None,
) -> "Tool":
    """根据函数自动创建模型可调用工具。"""

    tool_name = name or func.__name__
    tool_description = description if description is not None else _tool_description(func)

    from leocoder.tools.types import Tool

    return Tool(
        definition=ToolDefinition(
            name=tool_name,
            description=tool_description,
            parameters=function_to_parameters(func),
        ),
        executor=func,
    )


def _tool_description(func: Callable[..., Any]) -> str:
    """工具描述取 docstring 中 `Args:` 段之前的正文部分。"""

    doc = inspect.getdoc(func) or ""
    for line in doc.splitlines():
        stripped = line.strip().lower().rstrip(":")
        if stripped in _ARGS_SECTION_HEADERS:
            return doc.split(line, 1)[0].strip()
    return doc


def _annotation_to_schema(annotation: Any) -> dict[str, Any]:
    """把 Python 类型注解递归转换成 JSON Schema 片段。"""

    if annotation is inspect.Signature.empty or annotation is Any:
        return property_schema("string")

    origin = get_origin(annotation)

    if origin is Literal:
        values = list(get_args(annotation))
        return property_schema(_value_json_type(values[0]), enum=values)

    if isinstance(annotation, type) and issubclass(annotation, Enum):
        values = [member.value for member in annotation]
        if values:
            return property_schema(_value_json_type(values[0]), enum=values)
        return property_schema("string")

    if origin is Union or origin is types.UnionType:
        branches = [arg for arg in get_args(annotation) if arg is not type(None)]
        if len(branches) == 1:
            # Optional[X] 与 X 对模型等价；是否必填由默认值推导负责。
            return _annotation_to_schema(branches[0])
        return {"anyOf": [_annotation_to_schema(branch) for branch in branches]}

    if origin in PYTHON_TYPE_TO_JSON_TYPE:
        base = PYTHON_TYPE_TO_JSON_TYPE[origin]
        args = get_args(annotation)
        if base == "array":
            schema = property_schema("array")
            if args:
                schema["items"] = _annotation_to_schema(args[0])
            return schema
        if base == "object":
            schema = property_schema("object")
            if len(args) == 2 and args[1] is not Any:
                schema["additionalProperties"] = _annotation_to_schema(args[1])
            return schema
        return property_schema(base)

    if annotation in PYTHON_TYPE_TO_JSON_TYPE:
        return property_schema(PYTHON_TYPE_TO_JSON_TYPE[annotation])

    # 未知类型保守映射成 string，避免生成 provider 拒绝的 schema。
    return property_schema("string")


def _value_json_type(value: Any) -> str:
    return PYTHON_TYPE_TO_JSON_TYPE.get(type(value), "string")


def _is_json_compatible_default(value: Any) -> bool:
    """只有可被 json.dumps 原样表达的默认值才写进 schema。

    `None` 默认值刻意跳过：它只表示参数可选，写进 `default` 反而会让模型
    主动传 null。
    """

    if value is None:
        return False
    return isinstance(value, (str, int, float, bool))


def _parse_docstring_params(func: Callable[..., Any]) -> dict[str, str]:
    """解析 Google 风格 docstring 的 `Args:` 段，返回参数名到描述的映射。

    没有 `Args:` 段的 docstring（例如现有单行风格工具）返回空 dict，
    行为与之前完全一致。
    """

    doc = inspect.getdoc(func) or ""
    params: dict[str, str] = {}
    in_args_section = False
    current: str | None = None

    for line in doc.splitlines():
        if not line.strip():
            continue
        header = _SECTION_HEADER_PATTERN.match(line)
        if header:
            section_name = header.group(0).strip().rstrip(":").lower()
            in_args_section = section_name in _ARGS_SECTION_HEADERS
            current = None
            continue
        if not in_args_section:
            continue
        arg_match = _ARG_LINE_PATTERN.match(line)
        if arg_match:
            current = arg_match.group(1)
            params[current] = arg_match.group(2).strip()
        elif current is not None:
            params[current] = f"{params[current]} {line.strip()}".strip()

    return params
