"""Test sandbox_ctx functionality."""

import tempfile
from pathlib import Path

import pytest

from nkd_agents.tools import edit_file, execute_bash, read_file, sandbox_ctx


@pytest.fixture
def sandbox_dir():
    """Create a temporary sandbox directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture(autouse=True)
def reset_sandbox():
    """Ensure sandbox_ctx is reset after each test."""
    yield
    sandbox_ctx.set(None)


class TestSandboxBasicBehavior:
    """Test basic sandbox functionality."""

    @pytest.mark.asyncio
    async def test_default_no_sandbox(self):
        """Without sandbox set, operations use cwd."""
        result = await execute_bash("pwd")
        assert "STDOUT:" in result
        assert "EXIT CODE: 0" in result

    @pytest.mark.asyncio
    async def test_sandbox_relative_paths(self, sandbox_dir):
        """With sandbox set, relative paths work in sandbox."""
        sandbox_ctx.set(sandbox_dir)

        # Create file
        result = await edit_file("test.txt", "", "Hello sandbox!")
        assert "Success: Updated" in result
        assert sandbox_dir in result

        # Read file
        result = await read_file("test.txt")
        assert result == "Hello sandbox!"

        # Bash in sandbox
        result = await execute_bash("cat test.txt")
        assert "Hello sandbox!" in result

    @pytest.mark.asyncio
    async def test_sandbox_resets(self, sandbox_dir):
        """Sandbox can be set and reset."""
        # Set sandbox
        sandbox_ctx.set(sandbox_dir)
        result = await execute_bash("pwd")
        assert sandbox_dir in result

        # Reset
        sandbox_ctx.set(None)
        result = await execute_bash("pwd")
        assert sandbox_dir not in result


class TestSandboxSecurity:
    """Test sandbox security features."""

    @pytest.mark.asyncio
    async def test_absolute_paths_rejected(self, sandbox_dir):
        """Absolute paths are rejected when sandbox is set."""
        sandbox_ctx.set(sandbox_dir)

        result = await read_file("/etc/passwd")
        assert "Error: Absolute paths not allowed" in result

        result = await edit_file("/tmp/test.txt", "", "data")
        assert "Error: Absolute paths not allowed" in result

    @pytest.mark.asyncio
    async def test_path_traversal_blocked(self, sandbox_dir):
        """Path traversal attacks (../) that escape sandbox are blocked."""
        sandbox_ctx.set(sandbox_dir)

        result = await read_file("../../etc/passwd")
        assert "Error: Path escapes sandbox" in result

        result = await edit_file("../../../tmp/escape.txt", "", "data")
        assert "Error: Path escapes sandbox" in result

    @pytest.mark.asyncio
    async def test_path_traversal_within_sandbox_allowed(self, sandbox_dir):
        """Path traversal (../) within sandbox is allowed."""
        sandbox_ctx.set(sandbox_dir)

        # Create nested structure
        await edit_file("subdir/nested.txt", "", "nested")
        await edit_file("root.txt", "", "root")

        # Use ../ but stay in sandbox
        result = await read_file("subdir/../root.txt")
        assert result == "root"


class TestSandboxSymlinks:
    """Test symlink handling in sandbox."""

    @pytest.mark.asyncio
    async def test_symlink_inside_sandbox_allowed(self, sandbox_dir):
        """Symlinks pointing inside sandbox are allowed."""
        sandbox_ctx.set(sandbox_dir)
        sandbox_path = Path(sandbox_dir)

        # Create real file
        real_file = sandbox_path / "real.txt"
        real_file.write_text("real content")

        # Create symlink inside sandbox
        link = sandbox_path / "link.txt"
        link.symlink_to("real.txt")

        # Should work
        result = await read_file("link.txt")
        assert result == "real content"

    @pytest.mark.asyncio
    async def test_symlink_outside_sandbox_blocked(self, sandbox_dir):
        """Symlinks pointing outside sandbox are blocked."""
        sandbox_ctx.set(sandbox_dir)
        sandbox_path = Path(sandbox_dir)

        # Create malicious symlink pointing outside
        link = sandbox_path / "evil.txt"
        link.symlink_to("/etc/passwd")

        # Should be blocked
        result = await read_file("evil.txt")
        assert "Error: Path escapes sandbox" in result

    @pytest.mark.asyncio
    async def test_symlink_chain_inside_sandbox(self, sandbox_dir):
        """Chain of symlinks inside sandbox works."""
        sandbox_ctx.set(sandbox_dir)
        sandbox_path = Path(sandbox_dir)

        # Create chain: link1 → link2 → real
        real = sandbox_path / "real.txt"
        real.write_text("final content")

        link2 = sandbox_path / "link2.txt"
        link2.symlink_to("real.txt")

        link1 = sandbox_path / "link1.txt"
        link1.symlink_to("link2.txt")

        # Should follow chain and work
        result = await read_file("link1.txt")
        assert result == "final content"


class TestPathResolutionEdgeCases:
    """Test edge cases in path resolution."""

    @pytest.mark.asyncio
    async def test_dot_paths_in_sandbox(self, sandbox_dir):
        """Paths with . are handled correctly."""
        sandbox_ctx.set(sandbox_dir)

        await edit_file("./test.txt", "", "content")
        result = await read_file("./test.txt")
        assert result == "content"

    @pytest.mark.asyncio
    async def test_nested_directories(self, sandbox_dir):
        """Deep nested paths work."""
        sandbox_ctx.set(sandbox_dir)

        await edit_file("a/b/c/d/file.txt", "", "deep")
        result = await read_file("a/b/c/d/file.txt")
        assert result == "deep"

    @pytest.mark.asyncio
    async def test_empty_relative_path_components(self, sandbox_dir):
        """Paths like a//b are normalized."""
        sandbox_ctx.set(sandbox_dir)

        await edit_file("test.txt", "", "content")
        # Double slash should normalize to single
        result = await read_file("./test.txt")
        assert result == "content"
