from pathlib import Path

import pytest

from nkd_agents.tools import _sandbox_dir, edit_file, read_file


@pytest.mark.asyncio
async def test_read_file_success(tmp_path: Path) -> None:
    """Test successful file read within sandbox."""
    # Set up sandbox
    sandbox_token = _sandbox_dir.set(tmp_path)

    try:
        # Create test file with known content
        test_file = tmp_path / "test.txt"
        test_content = "Hello, World!"
        test_file.write_text(test_content, encoding="utf-8")

        # Read the file using relative path
        result = await read_file("test.txt")

        # Verify content matches
        assert result == test_content
    finally:
        # Clean up sandbox context
        _sandbox_dir.reset(sandbox_token)


@pytest.mark.asyncio
async def test_read_file_not_found(tmp_path: Path) -> None:
    """Test read_file returns error string when file doesn't exist."""
    sandbox_token = _sandbox_dir.set(tmp_path)

    try:
        result = await read_file("nonexistent.txt")
        assert result.startswith("Error reading file 'nonexistent.txt':")
        assert "No such file or directory" in result
    finally:
        _sandbox_dir.reset(sandbox_token)


@pytest.mark.asyncio
async def test_read_file_sandbox_escape_attempt(tmp_path: Path) -> None:
    """Test read_file blocks path that escapes sandbox."""
    sandbox_token = _sandbox_dir.set(tmp_path)

    try:
        result = await read_file("../outside.txt")
        assert result.startswith("Error reading file '../outside.txt':")
        assert "outside sandbox directory" in result
    finally:
        _sandbox_dir.reset(sandbox_token)


@pytest.mark.asyncio
async def test_edit_file_success(tmp_path: Path) -> None:
    """Test successful edit of existing file."""
    sandbox_token = _sandbox_dir.set(tmp_path)

    try:
        # Create initial file
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!", encoding="utf-8")

        # Edit the file
        result = await edit_file("test.txt", "World", "Python")

        # Verify success message
        assert "Success: Updated" in result
        assert "test.txt" in result

        # Verify content was updated
        updated_content = test_file.read_text(encoding="utf-8")
        assert updated_content == "Hello, Python!"
    finally:
        _sandbox_dir.reset(sandbox_token)


@pytest.mark.asyncio
async def test_edit_file_create_new_file(tmp_path: Path) -> None:
    """Test creating new file with old_str=''."""
    sandbox_token = _sandbox_dir.set(tmp_path)

    try:
        # Create new file using empty old_str
        result = await edit_file("new.txt", "", "New content")

        # Verify success message
        assert "Success: Updated" in result

        # Verify file was created with correct content
        new_file = tmp_path / "new.txt"
        assert new_file.exists()
        assert new_file.read_text(encoding="utf-8") == "New content"
    finally:
        _sandbox_dir.reset(sandbox_token)


@pytest.mark.asyncio
async def test_edit_file_old_str_not_found(tmp_path: Path) -> None:
    """Test error when old_str doesn't exist in file."""
    sandbox_token = _sandbox_dir.set(tmp_path)

    try:
        # Create file with known content
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!", encoding="utf-8")

        # Try to replace non-existent string
        result = await edit_file("test.txt", "Python", "Java")

        # Verify error message
        assert result == "Error: old_str not found in file content"
    finally:
        _sandbox_dir.reset(sandbox_token)


@pytest.mark.asyncio
async def test_edit_file_nonexistent_with_old_str(tmp_path: Path) -> None:
    """Test error when trying to edit non-existent file with non-empty old_str."""
    sandbox_token = _sandbox_dir.set(tmp_path)

    try:
        # Try to edit a file that doesn't exist (not creating, editing)
        result = await edit_file("missing.txt", "old", "new")

        # Verify error message
        assert result == "Error: File 'missing.txt' not found"
    finally:
        _sandbox_dir.reset(sandbox_token)


@pytest.mark.asyncio
async def test_edit_file_sandbox_escape_attempt(tmp_path: Path) -> None:
    """Test edit_file blocks path that escapes sandbox."""
    sandbox_token = _sandbox_dir.set(tmp_path)

    try:
        result = await edit_file("../outside.txt", "", "content")
        assert result.startswith("Error editing file '../outside.txt':")
        assert "outside sandbox directory" in result
    finally:
        _sandbox_dir.reset(sandbox_token)


@pytest.mark.asyncio
async def test_edit_file_same_strings(tmp_path: Path) -> None:
    """Test error when old_str equals new_str."""
    sandbox_token = _sandbox_dir.set(tmp_path)

    try:
        result = await edit_file("test.txt", "same", "same")
        assert result == "Error: old_str and new_str must be different"
    finally:
        _sandbox_dir.reset(sandbox_token)
