"""Utilities for example tests."""

import asyncio
import logging
import traceback
from collections.abc import Coroutine
from typing import Any, Callable, TypeVar

from nkd_agents._utils import load_env
from nkd_agents.logging import GREEN, RED, RESET, configure_logging, logging_context

logger = logging.getLogger(__name__)

T = TypeVar("T")


def test_runner(test_name: str) -> Callable[[Callable[..., Coroutine[Any, Any, T]]], Callable[..., T]]:
    """Decorator that sets up test environment and handles errors."""

    def decorator(func: Callable[..., Coroutine[Any, Any, T]]) -> Callable[..., T]:
        def wrapper(*args: Any, **kwargs: Any) -> T:
            load_env()
            configure_logging()
            logging_context.set({"test": test_name})

            try:
                result = asyncio.run(func(*args, **kwargs))
                logger.info(f"{GREEN}✓ Test passed!{RESET}")
                return result
            except Exception:
                logger.error(f"{RED}{traceback.format_exc()}{RESET}")
                raise

        return wrapper

    return decorator
