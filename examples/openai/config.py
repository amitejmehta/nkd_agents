"""Shared client and model settings for OpenAI examples."""

import os

KWARGS = {"model": os.getenv("MODEL", "gpt-5.2"), "max_output_tokens": 4096}
