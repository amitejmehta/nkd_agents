"""LLM provider implementations.

## Adding a New Provider

1. Create `nkd_agents/_providers/your_provider.py`
2. Add to PROVIDERS dict: `"your_provider": your_provider`
3. Implement six functions (see anthropic.py or openai.py as reference):

Required functions:
- `call()` - Make API call, return raw response
- `to_json()` - Convert Python function → provider's tool schema
- `execute_tool()` - Execute tool call, return formatted result
- `extract_text_and_tools()` - Parse response → (text: str, tool_calls: list)
- `format_assistant_message()` - Response → message(s) to append to conversation
- `format_tool_result_messages()` - Tool results → message(s) to append to conversation

The key: handle provider-specific formatting while maintaining consistent data flow.
"""

from . import anthropic, openai
from typing import Any

from anthropic.types.beta import BetaMessageParam
from openai.types.responses.response_input_param import ResponseInputParam

# Provider registry mapping prefixes to provider modules
PROVIDERS: dict[str, Any] = {
    "anthropic": anthropic,
    "openai": openai,
}

# Union of all provider message types
Messages = str | list[BetaMessageParam] | ResponseInputParam

__all__ = ["anthropic", "openai", "PROVIDERS", "Messages"]
