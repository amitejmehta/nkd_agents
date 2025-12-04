from pathlib import Path
from typing import Any, Callable, Coroutine, TypeVar, overload

from anthropic.types.beta import BetaMessageParam
from pydantic import BaseModel

from .context import Context

TModel = TypeVar("TModel", bound=BaseModel)

def render(template: Path, vars: dict[str, Any]) -> str: ...
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
