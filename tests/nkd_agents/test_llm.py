from functools import partial

import pytest

from nkd_agents.llm import LLM, parse_signature


def test_to_tool_definition_without_docstring():
    """Test that parse_signature raises ValueError when a function has no docstring."""
    with pytest.raises(ValueError) as excinfo:

        async def add(a: int, b: int):
            return a + b

        LLM._to_tool_definition(add)

    assert "must have a description" in str(excinfo.value)


def test_to_tool_definition_not_callable():
    with pytest.raises(ValueError) as excinfo:
        LLM._to_tool_definition(1)

    assert "must be a coroutine" in str(excinfo.value)


def test_parse_signature_callable_with_type_hint_and_docstring():
    async def add(a: int, b: int) -> int:
        """Add two numbers."""
        return a + b

    params, required = parse_signature(add)
    assert params == {"a": {"type": "integer"}, "b": {"type": "integer"}}
    assert required == ["a", "b"]


def test_parse_signature_without_type_hint_a():
    async def add(a, b: int):
        """Add two numbers."""
        return a + b

    with pytest.raises(ValueError) as excinfo:
        parse_signature(add)

    assert "Parameter a must have a type hint" in str(excinfo.value)


def test_parse_signature_without_type_hint_b():
    async def add(a: int, b):
        """Add two numbers."""
        return a + b

    with pytest.raises(ValueError) as excinfo:
        parse_signature(add)

    assert "Parameter b must have a type hint" in str(excinfo.value)


def test_parse_signature_with_partial():
    async def add(a: int, b: int) -> int:
        """Add two numbers."""
        return a + b

    params, required = parse_signature(add)
    assert params == {"a": {"type": "integer"}, "b": {"type": "integer"}}
    assert required == ["a", "b"]

    add_5 = partial(add, 5)
    # Note: Can't directly call async partial like this, but can still parse signature
    params, required = parse_signature(add_5)
    assert params == {"b": {"type": "integer"}}
    assert required == ["b"]
