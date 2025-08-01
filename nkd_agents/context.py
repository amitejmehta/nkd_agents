from dataclasses import dataclass
from typing import Generic, Optional, TypeVar

T = TypeVar("T")


@dataclass
class ContextWrapper(Generic[T]):
    """Wrapper for type safe safe access to dependencies"""

    def __init__(self, ctx: Optional[T] = None):
        self._ctx = ctx

    @property
    def ctx(self) -> T:
        return self._ctx
