import logging
from pathlib import Path
from typing import Any, Dict

from jinja2 import Environment

logger = logging.getLogger(__name__)


def jinja_required(var, msg):
    if not var:
        raise ValueError(msg)
    return var


env = Environment()
env.filters["required"] = jinja_required


def render(template: Path, vars: Dict[str, Any]) -> str:
    rendered = env.from_string(template.read_text()).render(**vars)
    logger.info(f"Rendered template:\n{template}")
    return rendered
