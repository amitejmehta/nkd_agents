from functools import partial

import pytest

from nkd_agents.llm import parse_signature, to_json


def test_to_json_without_docstring():
    """Test that parse_signature raises ValueError when a function has no docstring."""
    with pytest.raises(ValueError) as excinfo:

        def add(a: int, b: int):
            return a + b

        to_json(add)

    assert "must have a description" in str(excinfo.value)


def test_to_json_not_callable():
    with pytest.raises(ValueError) as excinfo:
        to_json(1)

    assert "must be a function" in str(excinfo.value)


def test_parse_signature_callable_with_type_hint_and_docstring():
    def add(a: int, b: int) -> int:
        """Add two numbers."""
        return a + b

    params, required = parse_signature(add)
    assert params == {"a": {"type": "integer"}, "b": {"type": "integer"}}
    assert required == ["a", "b"]


def test_parse_signature_without_type_hint_a():
    def add(a, b: int):
        """Add two numbers."""
        return a + b

    with pytest.raises(ValueError) as excinfo:
        parse_signature(add)

    assert "Parameter a must have a type hint" in str(excinfo.value)


def test_parse_signature_without_type_hint_b():
    def add(a: int, b):
        """Add two numbers."""
        return a + b

    with pytest.raises(ValueError) as excinfo:
        parse_signature(add)

    assert "Parameter b must have a type hint" in str(excinfo.value)


def test_parse_signature_with_partial():
    def add(a: int, b: int) -> int:
        """Add two numbers."""
        return a + b

    params, required = parse_signature(add)
    assert params == {"a": {"type": "integer"}, "b": {"type": "integer"}}
    assert required == ["a", "b"]

    add_5 = partial(add, 5)
    assert add_5(10) == 15
    params, required = parse_signature(add_5)
    assert params == {"b": {"type": "integer"}}
    assert required == ["b"]
