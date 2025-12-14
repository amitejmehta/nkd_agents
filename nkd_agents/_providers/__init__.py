"""Provider implementations for different LLM APIs."""

from .anthropic import AnthropicLLM
from .base import LLM
from .openai import OpenAILLM

# Provider registry mapping prefixes to provider instances
PROVIDERS: dict[str, LLM] = {
    "anthropic": AnthropicLLM(),
    "openai": OpenAILLM(),
}

__all__ = ["AnthropicLLM", "OpenAILLM", "PROVIDERS", "LLM"]
