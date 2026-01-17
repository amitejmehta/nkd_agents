"""Model settings for Anthropic example tests."""

import os

from nkd_agents.utils import load_env

load_env()
KWARGS = {"model": os.getenv("MODEL", "claude-haiku-4-5-20251001"), "max_tokens": 4096}
