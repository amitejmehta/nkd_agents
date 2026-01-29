"""Shared client and model settings for Anthropic examples."""

import os

KWARGS = {"model": os.getenv("MODEL", "claude-haiku-4-5-20251001"), "max_tokens": 4096}
