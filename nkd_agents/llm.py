import asyncio
from typing import Any, Callable, Coroutine, overload

from anthropic.types.beta import BetaMessageParam

from ._providers import PROVIDERS
from ._types import TModel
from .context import Context


@overload
async def llm(
    msgs: str | list[BetaMessageParam] | list[dict[str, Any]],
    *,
    model: str = ...,
    tools: list[Callable[..., Coroutine[Any, Any, Any]]] = ...,
    text_format: type[TModel],
    ctx: Context[Any] | None = ...,
    **settings: Any,
) -> TModel: ...
@overload
async def llm(
    msgs: str | list[BetaMessageParam] | list[dict[str, Any]],
    *,
    model: str = ...,
    tools: list[Callable[..., Coroutine[Any, Any, Any]]] = ...,
    text_format: type[TModel] | None = ...,
    ctx: Context[Any] | None = ...,
    **settings: Any,
) -> str: ...


async def llm(
    msgs: str | list[BetaMessageParam] | list[dict[str, Any]],
    *,
    model: str = "anthropic:claude-sonnet-4-5-20250929",
    tools: list[Callable[..., Coroutine[Any, Any, Any]]] = [],
    text_format: type[TModel] | None = None,
    ctx: Context[Any] | None = None,
    **settings: Any,
) -> str | TModel:
    """Run LLM in agentic loop, executing tools until final response.
    Tools must be async functions with type-annotated parameters and docstrings.
    Supported parameter types: str, int, float, bool.
    """
    if isinstance(msgs, str):
        msgs = [{"role": "user", "content": msgs}]

    provider_name, model_name = model.split(":", 1)
    llm = PROVIDERS[provider_name]

    tool_defs = [llm.to_json(t) for t in tools]

    while True:
        content = await llm(model_name, msgs, tool_defs, text_format, **settings)
        msgs.extend(llm.format_response(content))
        text, tool_calls = llm.extract_text_and_tools(content)

        if not tool_calls:
            return text_format.model_validate_json(text) if text_format else text

        coros = [llm.execute_tool(tc, tools, ctx) for tc in tool_calls]
        tool_results = await asyncio.gather(*coros)
        msgs.extend(llm.format_tool_results(tool_results))
