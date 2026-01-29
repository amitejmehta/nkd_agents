"""Shared client and model settings for OpenAI examples."""

import os
from functools import cache

from openai import AsyncOpenAI

from nkd_agents.utils import load_env

load_env()


@cache
def client() -> AsyncOpenAI:
    """Cached OpenAI client (API key from OPENAI_API_KEY env var)."""
    return AsyncOpenAI()


MODEL = os.getenv("MODEL", "gpt-5.2")
