"""Shared type definitions used across the nkd_agents package."""

from typing import TypeVar

from pydantic import BaseModel

# Type variable for structured output models
TModel = TypeVar("TModel", bound=BaseModel)
