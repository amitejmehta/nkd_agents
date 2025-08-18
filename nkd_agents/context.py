from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass
class ContextWrapper(Generic[T]):
    """Wrapper for type safe safe access to dependencies"""

    def __init__(self, ctx: T):
        self._ctx = ctx

    @property
    def ctx(self) -> T:
        return self._ctx
