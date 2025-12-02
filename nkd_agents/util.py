import inspect
import logging
from pathlib import Path
from typing import Any, Coroutine, Dict

from jinja2 import Environment

logger = logging.getLogger(__name__)


def parse_signature(func: Coroutine) -> tuple[dict[str, str], list[str]]:
    """Extract parameter schema and required fields from async function signature.

    Converts Python type hints to JSON schema types for Anthropic tool definitions.
    Excludes 'ctx' parameter from schema generation.

    Returns:
        tuple[dict[str, str], list[str]]: Parameter schema and list of required parameter names

    Raises:
        ValueError: If function is not async, missing docstring, or has invalid type hints
    """
    if not inspect.iscoroutinefunction(func):
        raise ValueError(f"Tool {func} must be a coroutine.")

    if not func.__doc__:
        raise ValueError(f"Tool {func.__name__} must have a description")

    type_map = {
        str: "string",
        int: "integer",
        float: "number",
        bool: "boolean",
        list: "array",
        dict: "object",
    }

    signature = inspect.signature(func)
    parameters, required = {}, []
    for param in signature.parameters.values():
        if param.annotation is inspect._empty:
            raise ValueError(f"Parameter {param.name} must have a type hint")
        if param.annotation not in type_map:
            raise ValueError(f"Unsupported parameter type: {param.annotation}")
        if param.name != "ctx":
            parameters[param.name] = {"type": type_map[param.annotation]}
        if param.default is inspect._empty:
            required.append(param.name)

    return parameters, required


def jinja_required(var: Any, msg: str) -> Any:
    """Jinja2 filter to enforce required variables in templates.

    Raises:
        ValueError: If variable is falsy
    Returns:
        Any: The variable if it is truthy
    """
    if not var:
        raise ValueError(msg)
    return var


env = Environment()
env.filters["required"] = jinja_required


def render(template: Path, vars: Dict[str, Any]) -> str:
    """Render a Jinja2 template file with provided variables.

    Args:
        template: Path to template file
        vars: Variables to pass to template

    Returns:
        str: Rendered template content
    """
    rendered = env.from_string(template.read_text()).render(**vars)
    logger.info(f"Rendered template:\n{template}")
    return rendered
