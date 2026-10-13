"""模型 provider 抽象和实现入口。"""

from leocoder.providers.anthropic_provider import AnthropicProvider
from leocoder.providers.base import ChatProvider
from leocoder.providers.factory import ProviderConfigError, create_provider_for_model
from leocoder.providers.openai_compatible import OpenAICompatibleProvider
from leocoder.providers.tool_adapters import to_anthropic_tool, to_openai_tool
from leocoder.providers.types import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    ChatStreamEvent,
    ProviderCapabilities,
    ProviderDiagnostics,
    StreamEventKind,
    TokenUsage,
    ToolChoiceFunction,
    ToolCall,
    ToolDefinition,
)

__all__ = [
    "AnthropicProvider",
    "ChatMessage",
    "ChatProvider",
    "ChatRequest",
    "ChatResponse",
    "ChatStreamEvent",
    "OpenAICompatibleProvider",
    "ProviderCapabilities",
    "ProviderConfigError",
    "ProviderDiagnostics",
    "StreamEventKind",
    "TokenUsage",
    "ToolChoiceFunction",
    "ToolCall",
    "ToolDefinition",
    "create_provider_for_model",
    "to_anthropic_tool",
    "to_openai_tool",
]
