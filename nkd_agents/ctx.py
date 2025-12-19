from contextlib import contextmanager
from contextvars import ContextVar
from typing import TypeVar

T = TypeVar("T")


@contextmanager
def ctx(context_var: ContextVar[T], value: T):
    """
    Context manager that temporarily sets a context variable to a value.

    Args:
        context_var: The ContextVar to modify
        value: The value to set

    Usage:
        my_var = ContextVar('my_var', default='default')

        with ctx(my_var, 'new_value'):
            print(my_var.get())  # prints 'new_value'

        print(my_var.get())  # prints 'default' (or previous value)
    """
    token = context_var.set(value)
    try:
        yield
    finally:
        context_var.reset(token)
