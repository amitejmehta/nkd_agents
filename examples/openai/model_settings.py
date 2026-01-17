"""Common model settings for OpenAI examples."""

import os

from nkd_agents.utils import load_env

load_env()
MODEL = os.getenv("MODEL", "gpt-5.2")
