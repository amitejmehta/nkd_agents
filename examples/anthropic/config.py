"""Shared client and model settings for Anthropic examples."""

import os
from functools import cache

from anthropic import AsyncAnthropic

from nkd_agents.utils import load_env

load_env()


@cache
def client() -> AsyncAnthropic:
    """Cached Anthropic client (API key from ANTHROPIC_API_KEY env var)."""
    return AsyncAnthropic()


KWARGS = {"model": os.getenv("MODEL", "claude-haiku-4-5-20251001"), "max_tokens": 4096}
