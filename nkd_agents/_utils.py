import inspect
import os
from pathlib import Path
from typing import Any, Callable, Coroutine


def load_env(path: str = ".env") -> None:
    """Load environment variables from a file."""
    if not Path(path).exists():
        return
    for line in Path(path).read_text().splitlines():
        if not line or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ[k] = v


def extract_function_schema(
    func: Callable[..., Coroutine[Any, Any, Any]],
) -> tuple[dict[str, dict[str, str]], list[str]]:
    """Extract parameter schema and required list from a function signature.

    Returns:
        tuple: (params_dict, required_list)
            - params_dict: Maps parameter names to their type definitions
            - required_list: List of required parameter names (no defaults)
    """
    type_map = {str: "string", int: "integer", float: "number", bool: "boolean"}
    type_map |= {list: "array", dict: "object", Path: "string"}

    params, req = {}, []
    for param in inspect.signature(func).parameters.values():
        if param.annotation is not inspect._empty and param.annotation not in type_map:
            raise ValueError(f"Unsupported type in {func.__name__}: {param.annotation}")

        params[param.name] = {"type": type_map.get(param.annotation, "string")}
        if param.default is inspect._empty:
            req.append(param.name)

    return params, req
