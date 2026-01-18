"""Test extract_function_params functionality."""

from typing import Literal

import pytest

from nkd_agents.utils import extract_function_params


@pytest.fixture
def basic_types():
    """Standard JSON-compatible types."""
    return {str: "string", int: "integer", float: "number", bool: "boolean"}


class TestBasicTypeMapping:
    """Test basic type annotations map to correct JSON schema types."""

    @pytest.mark.asyncio
    async def test_string_parameter(self):
        """String type maps to 'string'."""

        async def func(name: str):
            pass

        params, _ = extract_function_params(func)
        assert params["name"]["type"] == "string"

    @pytest.mark.asyncio
    async def test_integer_parameter(self):
        """Integer type maps to 'integer'."""

        async def func(count: int):
            pass

        params, _ = extract_function_params(func)
        assert params["count"]["type"] == "integer"

    @pytest.mark.asyncio
    async def test_float_parameter(self):
        """Float type maps to 'number'."""

        async def func(temp: float):
            pass

        params, _ = extract_function_params(func)
        assert params["temp"]["type"] == "number"

    @pytest.mark.asyncio
    async def test_boolean_parameter(self):
        """Boolean type maps to 'boolean'."""

        async def func(enabled: bool):
            pass

        params, _ = extract_function_params(func)
        assert params["enabled"]["type"] == "boolean"

    @pytest.mark.asyncio
    async def test_multiple_parameters(self):
        """Multiple parameters are all extracted."""

        async def func(name: str, count: int, enabled: bool):
            pass

        params, _ = extract_function_params(func)
        assert len(params) == 3
        assert "name" in params
        assert "count" in params
        assert "enabled" in params

    @pytest.mark.asyncio
    async def test_unannotated_parameter_defaults_to_string(self):
        """Parameters without type hints default to 'string'."""

        async def func(value):
            pass

        params, _ = extract_function_params(func)
        assert params["value"]["type"] == "string"


class TestRequiredParameters:
    """Test required vs optional parameter detection."""

    @pytest.mark.asyncio
    async def test_parameter_without_default_is_required(self):
        """Parameters without defaults are marked required."""

        async def func(required: str):
            pass

        _, required_list = extract_function_params(func)
        assert "required" in required_list

    @pytest.mark.asyncio
    async def test_parameter_with_default_is_optional(self):
        """Parameters with defaults are not required."""

        async def func(optional: str = "default"):
            pass

        _, required_list = extract_function_params(func)
        assert "optional" not in required_list

    @pytest.mark.asyncio
    async def test_mixed_required_and_optional(self):
        """Mix of required and optional parameters."""

        async def func(required: str, optional: int = 10):
            pass

        _, required_list = extract_function_params(func)
        assert "required" in required_list
        assert "optional" not in required_list
        assert len(required_list) == 1

    @pytest.mark.asyncio
    async def test_all_optional_parameters(self):
        """All optional parameters results in empty required list."""

        async def func(a: str = "x", b: int = 1):
            pass

        _, required_list = extract_function_params(func)
        assert len(required_list) == 0

    @pytest.mark.asyncio
    async def test_all_required_parameters(self):
        """All required parameters are listed."""

        async def func(a: str, b: int, c: bool):
            pass

        _, required_list = extract_function_params(func)
        assert len(required_list) == 3
        assert set(required_list) == {"a", "b", "c"}


class TestLiteralTypes:
    """Test Literal type handling with enum values."""

    @pytest.mark.asyncio
    async def test_string_literal(self):
        """String literals create enum constraint."""

        async def func(mode: Literal["fast", "slow"]):
            pass

        params, _ = extract_function_params(func)
        assert params["mode"]["type"] == "string"
        assert params["mode"]["enum"] == ["fast", "slow"]

    @pytest.mark.asyncio
    async def test_integer_literal(self):
        """Integer literals create integer enum."""

        async def func(level: Literal[1, 2, 3]):
            pass

        params, _ = extract_function_params(func)
        assert params["level"]["type"] == "integer"
        assert params["level"]["enum"] == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_float_literal(self):
        """Float literals create number enum."""

        async def func(temp: Literal[1.5, 2.5]):
            pass

        params, _ = extract_function_params(func)
        assert params["temp"]["type"] == "number"
        assert params["temp"]["enum"] == [1.5, 2.5]

    @pytest.mark.asyncio
    async def test_boolean_literal(self):
        """Boolean literals create boolean enum."""

        async def func(flag: Literal[True, False]):
            pass

        params, _ = extract_function_params(func)
        assert params["flag"]["type"] == "boolean"
        assert set(params["flag"]["enum"]) == {True, False}

    @pytest.mark.asyncio
    async def test_literal_with_default_is_optional(self):
        """Literal with default value is optional."""

        async def func(mode: Literal["a", "b"] = "a"):
            pass

        params, required_list = extract_function_params(func)
        assert "mode" not in required_list
        assert params["mode"]["enum"] == ["a", "b"]

    @pytest.mark.asyncio
    async def test_multiple_literals(self):
        """Multiple Literal parameters are handled independently."""

        async def func(mode: Literal["on", "off"], level: Literal[1, 2, 3]):
            pass

        params, _ = extract_function_params(func)
        assert params["mode"]["enum"] == ["on", "off"]
        assert params["level"]["enum"] == [1, 2, 3]


class TestListTypes:
    """Test list type handling with array schema."""

    @pytest.mark.asyncio
    async def test_list_of_strings(self):
        """list[str] creates array of strings."""

        async def func(items: list[str]):
            pass

        params, _ = extract_function_params(func)
        assert params["items"]["type"] == "array"
        assert params["items"]["items"]["type"] == "string"

    @pytest.mark.asyncio
    async def test_list_of_integers(self):
        """list[int] creates array of integers."""

        async def func(numbers: list[int]):
            pass

        params, _ = extract_function_params(func)
        assert params["numbers"]["type"] == "array"
        assert params["numbers"]["items"]["type"] == "integer"

    @pytest.mark.asyncio
    async def test_list_of_floats(self):
        """list[float] creates array of numbers."""

        async def func(values: list[float]):
            pass

        params, _ = extract_function_params(func)
        assert params["values"]["type"] == "array"
        assert params["values"]["items"]["type"] == "number"

    @pytest.mark.asyncio
    async def test_list_of_booleans(self):
        """list[bool] creates array of booleans."""

        async def func(flags: list[bool]):
            pass

        params, _ = extract_function_params(func)
        assert params["flags"]["type"] == "array"
        assert params["flags"]["items"]["type"] == "boolean"

    @pytest.mark.asyncio
    async def test_list_with_default_is_optional(self):
        """List with default value is optional."""

        async def func(items: list[str] = None):
            pass

        params, required_list = extract_function_params(func)
        assert "items" not in required_list
        assert params["items"]["type"] == "array"

    @pytest.mark.asyncio
    async def test_multiple_list_parameters(self):
        """Multiple list parameters are handled independently."""

        async def func(names: list[str], counts: list[int]):
            pass

        params, _ = extract_function_params(func)
        assert params["names"]["items"]["type"] == "string"
        assert params["counts"]["items"]["type"] == "integer"

    @pytest.mark.asyncio
    async def test_untyped_list_raises_error(self):
        """Bare list without type parameter raises error."""

        async def func(items: list):
            pass

        with pytest.raises(ValueError) as exc_info:
            extract_function_params(func)
        assert "must have type parameter" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_untyped_List_raises_error(self):
        """Bare List (uppercase) without type parameter raises error."""
        from typing import List

        async def func(items: List):
            pass

        with pytest.raises(ValueError) as exc_info:
            extract_function_params(func)
        error_msg = str(exc_info.value).lower()
        assert "list" in error_msg and (
            "empty" in error_msg or "must have type parameter" in error_msg
        )

    @pytest.mark.asyncio
    async def test_list_of_unsupported_type_raises_error(self):
        """list[UnsupportedType] raises error."""

        class Custom:
            pass

        async def func(items: list[Custom]):
            pass

        with pytest.raises(ValueError) as exc_info:
            extract_function_params(func)
        assert "Unsupported list item type" in str(exc_info.value)


class TestInvalidTypeAnnotations:
    """Test error handling for unsupported types."""

    @pytest.mark.asyncio
    async def test_dict_type_raises_error(self):
        """Dict type is not supported."""

        async def func(data: dict):
            pass

        with pytest.raises(ValueError) as exc_info:
            extract_function_params(func)
        assert "Unsupported type" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_custom_class_raises_error(self):
        """Custom classes are not supported."""

        class CustomType:
            pass

        async def func(obj: CustomType):
            pass

        with pytest.raises(ValueError) as exc_info:
            extract_function_params(func)
        assert "Unsupported type" in str(exc_info.value)


class TestInvalidLiteralTypes:
    """Test error handling for invalid Literal usage."""

    @pytest.mark.asyncio
    async def test_mixed_type_literal_raises_error(self):
        """Literal with mixed types is rejected."""

        async def func(val: Literal["string", 123]):
            pass

        with pytest.raises(ValueError) as exc_info:
            extract_function_params(func)
        # Check for key concepts in error, not exact wording
        error_msg = str(exc_info.value).lower()
        assert "literal" in error_msg and "mixed" in error_msg

    @pytest.mark.asyncio
    async def test_bytes_literal_raises_error(self):
        """Literal with bytes type is unsupported."""

        async def func(data: Literal[b"bytes"]):
            pass

        with pytest.raises(ValueError) as exc_info:
            extract_function_params(func)
        assert "Unsupported Literal type" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_list_literal_raises_error(self):
        """Literal with list type is unsupported."""

        async def func(items: Literal[[1, 2]]):
            pass

        with pytest.raises(ValueError) as exc_info:
            extract_function_params(func)
        assert "Unsupported Literal type" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_dict_literal_raises_error(self):
        """Literal with dict type is unsupported."""

        async def func(data: Literal[{"key": "val"}]):
            pass

        with pytest.raises(ValueError) as exc_info:
            extract_function_params(func)
        assert "Unsupported Literal type" in str(exc_info.value)


class TestComplexFunctionSignatures:
    """Test realistic complex function signatures."""

    @pytest.mark.asyncio
    async def test_function_with_all_features(self):
        """Function with mix of all supported features."""

        async def complex_func(
            # Required basic types
            name: str,
            count: int,
            # Required literal
            mode: Literal["dev", "prod"],
            # Optional basic types
            threshold: float = 0.5,
            enabled: bool = True,
            # Optional literal
            log_level: Literal[1, 2, 3] = 2,
        ):
            pass

        params, required_list = extract_function_params(complex_func)

        # Check all parameters extracted
        assert len(params) == 6

        # Check required parameters
        assert set(required_list) == {"name", "count", "mode"}

        # Check basic types
        assert params["name"]["type"] == "string"
        assert params["count"]["type"] == "integer"
        assert params["threshold"]["type"] == "number"
        assert params["enabled"]["type"] == "boolean"

        # Check literals
        assert params["mode"]["enum"] == ["dev", "prod"]
        assert params["log_level"]["enum"] == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_function_with_no_parameters(self):
        """Function with no parameters returns empty dicts."""

        async def no_params():
            pass

        params, required_list = extract_function_params(no_params)
        assert len(params) == 0
        assert len(required_list) == 0

    @pytest.mark.asyncio
    async def test_parameter_names_preserved(self):
        """Parameter names are preserved exactly."""

        async def func(CamelCase: str, snake_case: int, num123: bool):
            pass

        params, _ = extract_function_params(func)
        assert "CamelCase" in params
        assert "snake_case" in params
        assert "num123" in params
