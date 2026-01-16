from contextlib import contextmanager
from contextvars import ContextVar
from typing import TypeVar

T = TypeVar("T")


def get(context_var: ContextVar[T]) -> T:
    """Get a contextvar value, raising an error if not set.

    Args:
        context_var: The ContextVar to get

    Returns:
        The context variable's value

    Raises:
        ValueError: If the context variable is not set
    """
    try:
        return context_var.get()
    except LookupError:
        var_name = getattr(context_var, "name", "context variable")
        raise ValueError(f"{var_name} not set in context")


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
