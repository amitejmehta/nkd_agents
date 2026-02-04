"""Test utils module functionality."""

import logging
import os
from typing import List, Literal

import pytest

from nkd_agents.utils import display_diff, extract_function_params, load_env


class TestExtractFunctionParams:
    """Test extract_function_params functionality."""

    @pytest.mark.asyncio
    async def test_basic_types(self):
        """All basic types map correctly."""

        async def func(name: str, count: int, temp: float, enabled: bool, unannotated):
            pass

        params, _ = extract_function_params(func)
        assert params["name"]["type"] == "string"
        assert params["count"]["type"] == "integer"
        assert params["temp"]["type"] == "number"
        assert params["enabled"]["type"] == "boolean"
        assert params["unannotated"]["type"] == "string"

    @pytest.mark.asyncio
    async def test_required_vs_optional(self):
        """Required params lack defaults, optional have them."""

        async def func(required: str, a: str = "x", b: int = 1, c: str = "y"):
            pass

        params, required_list = extract_function_params(func)
        assert required_list == ["required"]
        assert "default" not in params["required"]
        assert params["a"]["default"] == "x"
        assert params["b"]["default"] == 1
        assert params["c"]["default"] == "y"

    @pytest.mark.asyncio
    async def test_literals(self):
        """Literals of all types create enum constraints."""

        async def func(
            mode: Literal["fast", "slow"],
            level: Literal[1, 2, 3],
            temp: Literal[1.5, 2.5],
            optional: Literal["a", "b"] = "a",
        ):
            pass

        params, required_list = extract_function_params(func)
        assert params["mode"]["enum"] == ["fast", "slow"]
        assert params["level"]["enum"] == [1, 2, 3]
        assert params["temp"]["enum"] == [1.5, 2.5]
        assert "optional" not in required_list

    @pytest.mark.asyncio
    async def test_lists(self):
        """Lists of all types create array schemas."""

        async def func(
            items: list[str],
            numbers: list[int],
            values: list[float],
            flags: list[bool],
            optional: list[str] = None,
        ):
            pass

        params, required_list = extract_function_params(func)
        assert params["items"]["items"]["type"] == "string"
        assert params["numbers"]["items"]["type"] == "integer"
        assert params["values"]["items"]["type"] == "number"
        assert params["flags"]["items"]["type"] == "boolean"
        assert "optional" not in required_list

    @pytest.mark.asyncio
    async def test_bare_list_error(self):
        """Bare list without type parameter raises error."""

        async def func(items: list):
            pass

        with pytest.raises(ValueError) as exc:
            extract_function_params(func)
        assert "must have type parameter" in str(exc.value)

    @pytest.mark.asyncio
    async def test_bare_List_error(self):
        """Bare List (uppercase) raises error."""

        async def func(items: List):
            pass

        with pytest.raises(ValueError) as exc:
            extract_function_params(func)
        assert "list" in str(exc.value).lower()

    @pytest.mark.asyncio
    async def test_invalid_list_item_type(self):
        """list[UnsupportedType] raises error."""

        class Custom:
            pass

        async def func(items: list[Custom]):
            pass

        with pytest.raises(ValueError) as exc:
            extract_function_params(func)
        assert "Unsupported list item type" in str(exc.value)

    @pytest.mark.asyncio
    async def test_unsupported_types(self):
        """Dict and custom classes raise errors."""

        async def func(data: dict):
            pass

        with pytest.raises(ValueError) as exc:
            extract_function_params(func)
        assert "Unsupported type" in str(exc.value)

    @pytest.mark.asyncio
    async def test_mixed_literal_types(self):
        """Literal with mixed types is rejected."""

        async def func(val: Literal["string", 123]):
            pass

        with pytest.raises(ValueError) as exc:
            extract_function_params(func)
        assert "mixed" in str(exc.value).lower()

    @pytest.mark.asyncio
    async def test_unsupported_literal_type(self):
        """Literal with unsupported types raises error."""

        async def func(data: Literal[b"bytes"]):
            pass

        with pytest.raises(ValueError) as exc:
            extract_function_params(func)
        assert "Unsupported Literal type" in str(exc.value)

    @pytest.mark.asyncio
    async def test_empty_literal_error(self):
        """Empty Literal raises error (line 29)."""
        # Tests the error path in _handle_literal_annotation
        from nkd_agents.utils import _handle_literal_annotation

        with pytest.raises(ValueError) as exc:
            _handle_literal_annotation((), "func.param", {})
        assert "Empty Literal" in str(exc.value)

    @pytest.mark.asyncio
    async def test_optional_type(self):
        """T | None unions are supported and extract the base type."""

        async def func(a: int, b: int | None = None, c: str | None = None):
            pass

        params, required_list = extract_function_params(func)
        assert params["a"]["type"] == "integer"
        assert params["b"]["type"] == "integer"
        assert params["c"]["type"] == "string"
        assert required_list == ["a"]
        assert "default" not in params["a"]
        assert params["b"]["default"] is None
        assert params["c"]["default"] is None

    @pytest.mark.asyncio
    async def test_non_optional_union_error(self):
        """Unions other than T | None raise error."""

        async def func(val: int | str):
            pass

        with pytest.raises(ValueError) as exc:
            extract_function_params(func)
        assert "Only T | None unions supported" in str(exc.value)

    @pytest.mark.asyncio
    async def test_no_parameters(self):
        """Function with no parameters."""

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


class TestLoadEnv:
    """Test load_env functionality."""

    def test_missing_file(self, tmp_path):
        """load_env silently returns if file doesn't exist (early return on line 15)."""
        # This test exercises the early return path in load_env
        load_env(str(tmp_path / "nonexistent.env"))

    def test_populates_environ(self, tmp_path):
        """load_env reads file and populates os.environ."""
        env_file = tmp_path / ".env"
        env_file.write_text("TEST_VAR=test_value\nANOTHER=value123")
        load_env(str(env_file))
        assert os.environ.get("TEST_VAR") == "test_value"
        assert os.environ.get("ANOTHER") == "value123"
        del os.environ["TEST_VAR"]
        del os.environ["ANOTHER"]

    def test_skips_invalid_lines(self, tmp_path):
        """load_env skips blank lines and lines without '='."""
        env_file = tmp_path / ".env"
        env_file.write_text("VALID=yes\n\ninvalid_no_equals\nANOTHER=val")
        load_env(str(env_file))
        assert os.environ.get("VALID") == "yes"
        assert os.environ.get("ANOTHER") == "val"
        del os.environ["VALID"]
        del os.environ["ANOTHER"]


class TestDisplayDiff:
    """Test display_diff functionality."""

    def test_logs_diff(self, caplog):
        """display_diff logs colored diff output."""
        caplog.set_level(logging.INFO)
        display_diff("old\nline1\nline2", "new\nline1\nline3", "test.txt")
        assert "Update: test.txt" in caplog.text


class TestCwdContext:
    """Test cwd_ctx with relative paths in tools."""

    @pytest.mark.asyncio
    async def test_read_file_relative_path(self, tmp_path):
        """read_file resolves relative paths against cwd_ctx."""
        from nkd_agents.tools import cwd_ctx, read_file

        subdir = tmp_path / "subdir"
        subdir.mkdir()
        test_file = subdir / "test.txt"
        test_file.write_text("content")

        token = cwd_ctx.set(subdir)
        try:
            result = await read_file("test.txt")
            assert result == [{"type": "text", "text": "content"}]
        finally:
            cwd_ctx.reset(token)

    @pytest.mark.asyncio
    async def test_edit_file_relative_path(self, tmp_path):
        """edit_file resolves relative paths against cwd_ctx."""
        from nkd_agents.tools import cwd_ctx, edit_file

        subdir = tmp_path / "subdir"
        subdir.mkdir()

        token = cwd_ctx.set(subdir)
        try:
            result = await edit_file("new.txt", "", "created")
            assert "Success" in result
            assert (subdir / "new.txt").read_text() == "created"
        finally:
            cwd_ctx.reset(token)

    @pytest.mark.asyncio
    async def test_bash_cwd_context(self, tmp_path):
        """bash executes in cwd_ctx directory."""
        from nkd_agents.tools import bash, cwd_ctx

        subdir = tmp_path / "workdir"
        subdir.mkdir()

        token = cwd_ctx.set(subdir)
        try:
            result = await bash("pwd")
            assert str(subdir) in result
        finally:
            cwd_ctx.reset(token)

    @pytest.mark.asyncio
    async def test_cwd_isolation(self, tmp_path):
        """cwd_ctx changes don't affect other contexts."""
        from nkd_agents.tools import cwd_ctx, read_file

        dir1 = tmp_path / "dir1"
        dir2 = tmp_path / "dir2"
        dir1.mkdir()
        dir2.mkdir()
        (dir1 / "file.txt").write_text("dir1_content")
        (dir2 / "file.txt").write_text("dir2_content")

        token1 = cwd_ctx.set(dir1)
        result1 = await read_file("file.txt")
        cwd_ctx.reset(token1)

        token2 = cwd_ctx.set(dir2)
        result2 = await read_file("file.txt")
        cwd_ctx.reset(token2)

        assert result1 == [{"type": "text", "text": "dir1_content"}]
        assert result2 == [{"type": "text", "text": "dir2_content"}]
