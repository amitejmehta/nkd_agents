import asyncio
import logging
from typing import Any, Callable, Coroutine, overload

from ._providers import PROVIDERS, Messages
from ._types import TModel

logger = logging.getLogger(__name__)


def _parse_models(models: list[str]) -> tuple[Any, list[str]]:
    """Parse model strings and return (provider, model_names)."""
    providers = [m.split(":", 1)[0] for m in models]

    if len(set(providers)) > 1:
        raise ValueError("All fallback models must use same provider")

    provider_name = providers[0]
    model_names = [m.split(":", 1)[1] for m in models]

    return PROVIDERS[provider_name], model_names


async def _call_with_fallback(
    provider: Any,
    models: list[str],
    msgs: Messages,
    tool_defs: list[Any],
    text_format: type[TModel] | None,
    client: Any,
    **settings: Any,
) -> Any:
    """Try each model in fallback list until one succeeds."""
    for m in models:
        try:
            return await provider.call(
                msgs, m, tool_defs, text_format, client=client, **settings
            )
        except Exception as e:
            logger.warning(f"Model {m} failed: {e}, trying fallback...")
    raise Exception(f"All models failed: {models}")


@overload
async def llm(
    msgs: Messages,
    *,
    model: list[str] = ...,
    tools: list[Callable[..., Coroutine[Any, Any, Any]]] = ...,
    text_format: type[TModel],
    client: Any = ...,
    **settings: Any,
) -> TModel: ...
@overload
async def llm(
    msgs: Messages,
    *,
    model: list[str] = ...,
    tools: list[Callable[..., Coroutine[Any, Any, Any]]] = ...,
    text_format: type[TModel] | None = ...,
    client: Any = ...,
    **settings: Any,
) -> str: ...


async def llm(
    msgs: Messages,
    *,
    model: list[str] = ["anthropic:claude-sonnet-4-5-20250929"],
    tools: list[Callable[..., Coroutine[Any, Any, Any]]] = [],
    text_format: type[TModel] | None = None,
    client: Any = None,
    **settings: Any,
) -> str | TModel:
    """Run LLM in agentic loop, executing tools until final response.

    Tools must be async functions with type-annotated parameters and docstrings.
    Model is a list of model strings for same-provider fallback.
    """
    if isinstance(msgs, str):
        msgs = [{"role": "user", "content": msgs}]

    provider, model_names = _parse_models(model)
    tool_defs = [provider.to_json(t) for t in tools]

    while True:
        content = await _call_with_fallback(
            provider, model_names, msgs, tool_defs, text_format, client, **settings
        )

        msgs.extend(provider.format_assistant_message(content))
        text, tool_calls = provider.extract_text_and_tools(content)

        if not tool_calls:
            return text_format.model_validate_json(text) if text_format else text

        try:
            results = await asyncio.gather(
                *[provider.execute_tool(tc, tools) for tc in tool_calls]
            )
            msgs.extend(provider.format_tool_results_message(tool_calls, results))
        except asyncio.CancelledError:
            results = ["Interrupted"] * len(tool_calls)
            msgs.extend(provider.format_tool_results_message(tool_calls, results))
            raise
