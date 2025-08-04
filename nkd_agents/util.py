from pathlib import Path
from typing import Any, Dict

from jinja2 import Environment

from .config import logger


def jinja_required(var, msg):
    if not var:
        raise ValueError(msg)
    return var


env = Environment()
env.filters["required"] = jinja_required


def render(template: Path | str, vars: Dict[str, Any]) -> str:
    template_str = template if isinstance(template, str) else template.read_text()
    rendered = env.from_string(template_str).render(**vars)
    logger.info(f"Rendered template:\n{template}")
    return rendered
