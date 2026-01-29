"""Test sandbox_ctx functionality."""

import asyncio
import tempfile
from pathlib import Path

import pytest

from nkd_agents.tools import bash, edit_file, read_file, sandbox_ctx


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
        result = await bash("pwd")
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
        assert isinstance(result, list)
        assert result[0]["type"] == "text"
        assert result[0]["text"] == "Hello sandbox!"

        # Bash in sandbox
        result = await bash("cat test.txt")
        assert "Hello sandbox!" in result

    @pytest.mark.asyncio
    async def test_sandbox_resets(self, sandbox_dir):
        """Sandbox can be set and reset."""
        # Set sandbox
        sandbox_ctx.set(sandbox_dir)
        result = await bash("pwd")
        assert sandbox_dir in result

        # Reset
        sandbox_ctx.set(None)
        result = await bash("pwd")
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
        assert isinstance(result, list)
        assert result[0]["text"] == "root"


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
        assert isinstance(result, list)
        assert result[0]["text"] == "real content"

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
        assert isinstance(result, list)
        assert result[0]["text"] == "final content"


class TestPathResolutionEdgeCases:
    """Test edge cases in path resolution."""

    @pytest.mark.asyncio
    async def test_dot_paths_in_sandbox(self, sandbox_dir):
        """Paths with . are handled correctly."""
        sandbox_ctx.set(sandbox_dir)

        await edit_file("./test.txt", "", "content")
        result = await read_file("./test.txt")
        assert isinstance(result, list)
        assert result[0]["text"] == "content"

    @pytest.mark.asyncio
    async def test_nested_directories(self, sandbox_dir):
        """Deep nested paths work."""
        sandbox_ctx.set(sandbox_dir)

        await edit_file("a/b/c/d/file.txt", "", "deep")
        result = await read_file("a/b/c/d/file.txt")
        assert isinstance(result, list)
        assert result[0]["text"] == "deep"

    @pytest.mark.asyncio
    async def test_empty_relative_path_components(self, sandbox_dir):
        """Paths like a//b are normalized."""
        sandbox_ctx.set(sandbox_dir)

        await edit_file("test.txt", "", "content")
        # Double slash should normalize to single
        result = await read_file("./test.txt")
        assert isinstance(result, list)
        assert result[0]["text"] == "content"


class TestReadFileEdgeCases:
    """Test read_file error handling."""

    @pytest.mark.asyncio
    async def test_read_file_nonexistent(self):
        """read_file raises FileNotFoundError for nonexistent file."""
        with pytest.raises(FileNotFoundError):
            await read_file("/nonexistent/path/file.txt")

    @pytest.mark.asyncio
    async def test_read_file_directory(self):
        """read_file raises IsADirectoryError when given directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(IsADirectoryError):
                await read_file(tmpdir)

    @pytest.mark.asyncio
    async def test_read_file_image_png(self):
        """read_file handles PNG images."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            # Minimal 1x1 PNG
            png_bytes = bytes(
                [
                    0x89,
                    0x50,
                    0x4E,
                    0x47,
                    0x0D,
                    0x0A,
                    0x1A,
                    0x0A,
                    0x00,
                    0x00,
                    0x00,
                    0x0D,
                    0x49,
                    0x48,
                    0x44,
                    0x52,
                    0x00,
                    0x00,
                    0x00,
                    0x01,
                    0x00,
                    0x00,
                    0x00,
                    0x01,
                    0x08,
                    0x02,
                    0x00,
                    0x00,
                    0x00,
                    0x90,
                    0x77,
                    0x53,
                    0xDE,
                    0x00,
                    0x00,
                    0x00,
                    0x0C,
                    0x49,
                    0x44,
                    0x41,
                    0x54,
                    0x08,
                    0x99,
                    0x63,
                    0xF8,
                    0xCF,
                    0xC0,
                    0x00,
                    0x00,
                    0x03,
                    0x01,
                    0x01,
                    0x00,
                    0x18,
                    0xDD,
                    0x8D,
                    0xB4,
                    0x00,
                    0x00,
                    0x00,
                    0x00,
                    0x49,
                    0x45,
                    0x4E,
                    0x44,
                    0xAE,
                    0x42,
                    0x60,
                    0x82,
                ]
            )
            f.write(png_bytes)
            path = f.name

        try:
            result = await read_file(path, "image/png")
            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0]["type"] == "image"
            assert result[0]["source"]["type"] == "base64"
            assert result[0]["source"]["media_type"] == "image/png"
            assert result[0]["source"]["data"]
        finally:
            Path(path).unlink()

    @pytest.mark.asyncio
    async def test_read_file_image_jpeg(self):
        """read_file handles JPEG images."""
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            # Minimal JPEG header
            f.write(bytes([0xFF, 0xD8, 0xFF, 0xE0]))
            path = f.name

        try:
            result = await read_file(path, "image/jpeg")
            assert isinstance(result, list)
            assert result[0]["type"] == "image"
            assert result[0]["source"]["media_type"] == "image/jpeg"
        finally:
            Path(path).unlink()

    @pytest.mark.asyncio
    async def test_read_file_pdf(self):
        """read_file handles PDF documents."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            # Minimal PDF header
            f.write(b"%PDF-1.4\n")
            path = f.name

        try:
            result = await read_file(path, "application/pdf")
            assert isinstance(result, list)
            assert result[0]["type"] == "document"
            assert result[0]["source"]["type"] == "base64"
            assert result[0]["source"]["media_type"] == "application/pdf"
            assert result[0]["source"]["data"]
        finally:
            Path(path).unlink()


class TestEditFileEdgeCases:
    """Test edit_file error handling."""

    @pytest.mark.asyncio
    async def test_edit_file_same_str(self):
        """edit_file rejects when old_str equals new_str."""
        result = await edit_file("test.txt", "same", "same")
        assert "old_str and new_str must be different" in result

    @pytest.mark.asyncio
    async def test_edit_file_old_str_not_found(self):
        """edit_file returns error when old_str not in content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sandbox_ctx.set(tmpdir)
            await edit_file("test.txt", "", "original content")
            result = await edit_file("test.txt", "notfound", "replaced")
            assert "old_str not found in file content" in result

    @pytest.mark.asyncio
    async def test_edit_file_create_new(self):
        """edit_file creates new file when old_str is empty."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sandbox_ctx.set(tmpdir)
            result = await edit_file("newfile.txt", "", "initial content")
            assert "Success: Updated" in result
            content = await read_file("newfile.txt")
            assert isinstance(content, list)
            assert content[0]["text"] == "initial content"

    @pytest.mark.asyncio
    async def test_edit_file_replace_count(self):
        """edit_file respects count parameter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sandbox_ctx.set(tmpdir)
            await edit_file("test.txt", "", "foo bar foo bar foo")

            # Replace only first occurrence
            await edit_file("test.txt", "foo", "baz", count=1)
            content = await read_file("test.txt")
            assert isinstance(content, list)
            assert content[0]["text"] == "baz bar foo bar foo"

            # Replace all
            await edit_file("test.txt", "foo", "baz", count=-1)
            content = await read_file("test.txt")
            assert isinstance(content, list)
            assert content[0]["text"] == "baz bar baz bar baz"

    @pytest.mark.asyncio
    async def test_edit_file_create_parent_dirs(self):
        """edit_file creates parent directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sandbox_ctx.set(tmpdir)
            result = await edit_file("deep/nested/path/file.txt", "", "content")
            assert "Success: Updated" in result
            content = await read_file("deep/nested/path/file.txt")
            assert isinstance(content, list)
            assert content[0]["text"] == "content"

    @pytest.mark.asyncio
    async def test_edit_file_file_not_found_on_edit(self):
        """edit_file returns error when file doesn't exist and old_str is not empty."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sandbox_ctx.set(tmpdir)
            result = await edit_file("nonexistent.txt", "search", "replace")
            assert "Error: File" in result and "not found" in result


class TestBashEdgeCases:
    """Test bash tool error handling and edge cases."""

    @pytest.mark.asyncio
    async def test_bash_command_failure(self):
        """bash returns proper exit code on command failure."""
        result = await bash("exit 42")
        assert "EXIT CODE: 42" in result

    @pytest.mark.asyncio
    async def test_bash_with_stderr(self):
        """bash captures stderr."""
        result = await bash("echo 'stdout' && echo 'stderr' >&2")
        assert "stdout" in result
        assert "stderr" in result
        assert "STDERR:" in result

    @pytest.mark.asyncio
    async def test_bash_in_sandbox_dir(self, sandbox_dir):
        """bash executes in sandbox directory when set."""
        sandbox_ctx.set(sandbox_dir)
        await edit_file("test.txt", "", "sandbox content")
        result = await bash("cat test.txt")
        assert "sandbox content" in result

    @pytest.mark.asyncio
    async def test_bash_cancellation(self, sandbox_dir):
        """bash handles cancellation gracefully."""
        sandbox_ctx.set(sandbox_dir)

        # Create a long-running command
        task = asyncio.create_task(bash("sleep 30"))
        await asyncio.sleep(0.1)  # Let it start
        task.cancel()

        try:
            await task
            assert False, "Should have been cancelled"
        except asyncio.CancelledError:
            pass  # Expected
