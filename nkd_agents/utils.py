import difflib
import inspect
import logging
import os
from pathlib import Path
from typing import Any, Awaitable, Callable, Literal, get_args, get_origin

from .logging import GREEN, RED, RESET

logger = logging.getLogger(__name__)


def load_env(path: str = ".env") -> None:
    """Load environment variables from a file."""
    if not Path(path).exists():
        return
    for line in Path(path).read_text().splitlines():
        if not line or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ[k] = v


def process_param_annotation(annotation: Any, param_sig: str) -> dict[str, Any]:
    """Process a parameter annotation and return its schema."""
    type_map = {str: "string", int: "integer", float: "number", bool: "boolean"}

    if get_origin(annotation) is Literal:
        literal_values = list(get_args(annotation))
        if not literal_values:
            raise ValueError(f"Empty Literal in {param_sig}")
        first_type = type(literal_values[0])
        if first_type not in type_map:
            raise ValueError(f"Unsupported Literal type: {param_sig}")
        if not all(type(v) == first_type for v in literal_values):
            raise ValueError(f"Literal cannot have mixed types: {param_sig}")

        return {"type": type_map[first_type], "enum": literal_values}
    elif annotation is not inspect._empty and annotation not in type_map:
        raise ValueError(f"Unsupported type: {param_sig}")
    else:
        return {"type": type_map.get(annotation, "string")}


def extract_function_params(
    func: Callable[..., Awaitable[Any]],
) -> tuple[dict[str, str], list[str]]:
    """Extract parameter schema and required list from a function signature.
    Supports core types: str, int, float, bool and Literal of core types.

    Returns:
        tuple: (params_dict, required_list)
            - params_dict: Maps parameter names to their type definitions
            - required_list: List of required parameter names (no defaults)
    """
    params, required_params = {}, []

    for param in inspect.signature(func).parameters.values():
        param_sig = f"{func.__name__}.{param.name}: {param.annotation}"
        params[param.name] = process_param_annotation(param.annotation, param_sig)

        if param.default is inspect._empty:
            required_params.append(param.name)

    return params, required_params


def display_diff(old: str, new: str, path: str) -> None:
    """Display a colorized unified diff in the console."""
    diff = difflib.unified_diff(old.splitlines(), new.splitlines(), lineterm="")

    lines = [f"\nUpdate: {path}"]
    for line in diff:
        color = GREEN if line[0] == "+" else RED if line[0] == "-" else ""
        lines.append(f"{color}{line}{RESET}")

    logger.info("\n".join(lines))
