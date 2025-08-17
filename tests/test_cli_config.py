"""
Test suite for CLI completer functionality.

Tests the SlashCommandCompleter to ensure it only suggests commands
at the beginning of input and doesn't interfere with normal conversation.
Also tests FileCompleter and CombinedCompleter functionality.
"""

import os
import tempfile
from pathlib import Path

import pytest
from prompt_toolkit.document import Document

from nkd_agents.cli_config import (
    CombinedCompleter,
    FileCompleter,
    SlashCommandCompleter,
)


@pytest.fixture
def completer():
    """Fixture providing a fresh SlashCommandCompleter instance."""
    return SlashCommandCompleter()


class TestSlashCommandCompleter:
    """Test suite for the SlashCommandCompleter class."""

    def test_suggests_commands_with_slash_prefix(self, completer):
        """Test that commands are suggested when input starts with '/'."""
        doc = Document("/h", 2)
        completions = list(completer.get_completions(doc, None))
        suggestions = [c.text for c in completions]

        assert "/help" in suggestions
        assert len(suggestions) == 1

    def test_suggests_all_commands_with_bare_slash(self, completer):
        """Test that all commands are suggested when input is just '/'."""
        doc = Document("/", 1)
        completions = list(completer.get_completions(doc, None))
        suggestions = [c.text for c in completions]

        expected_commands = ["/clear", "/edit_mode", "/help"]
        assert suggestions == expected_commands
        assert len(suggestions) == 3

    def test_no_suggestions_without_slash_prefix(self, completer):
        """Test that no commands are suggested when input doesn't start with '/'."""
        doc = Document("help", 4)
        completions = list(completer.get_completions(doc, None))

        assert list(completions) == []

    def test_no_suggestions_in_middle_of_sentence(self, completer):
        """Test that no commands are suggested when slash appears mid-sentence."""
        doc = Document("I want to /clear this", 21)
        completions = list(completer.get_completions(doc, None))

        assert list(completions) == []

    def test_no_suggestions_when_cursor_not_at_end(self, completer):
        """Test that no suggestions appear when cursor is not at end of input."""
        # Cursor at position 1 in "/help" (between / and h)
        doc = Document("/help", 1)
        completions = list(completer.get_completions(doc, None))

        assert list(completions) == []

    def test_case_insensitive_matching(self, completer):
        """Test that command matching is case-insensitive."""
        doc = Document("/Clear", 6)
        completions = list(completer.get_completions(doc, None))
        suggestions = [c.text for c in completions]

        assert "/clear" in suggestions
        assert len(suggestions) == 1

    def test_exact_command_match(self, completer):
        """Test suggestions when typing an exact command."""
        doc = Document("/help", 5)
        completions = list(completer.get_completions(doc, None))
        suggestions = [c.text for c in completions]

        assert "/help" in suggestions
        assert len(suggestions) == 1

    def test_partial_command_matching(self, completer):
        """Test that partial commands return appropriate suggestions."""
        doc = Document("/e", 2)
        completions = list(completer.get_completions(doc, None))
        suggestions = [c.text for c in completions]

        assert "/edit_mode" in suggestions
        assert len(suggestions) == 1

    def test_no_suggestions_for_non_matching_prefix(self, completer):
        """Test that non-matching prefixes return no suggestions."""
        doc = Document("/xyz", 4)
        completions = list(completer.get_completions(doc, None))

        assert list(completions) == []

    def test_completion_start_position(self, completer):
        """Test that completions have correct start position for replacement."""
        doc = Document("/h", 2)
        completions = list(completer.get_completions(doc, None))

        for completion in completions:
            assert completion.start_position == -2  # Should replace the "/h"

    def test_bare_slash_suggests_all_commands(self, completer):
        """Test bare slash suggests all commands."""
        doc = Document("/", 1)
        completions = list(completer.get_completions(doc, None))
        assert len(completions) == 3

    def test_h_prefix_suggests_help(self, completer):
        """Test /h prefix suggests help."""
        doc = Document("/h", 2)
        completions = list(completer.get_completions(doc, None))
        assert len(completions) == 1

    def test_c_prefix_suggests_clear(self, completer):
        """Test /c prefix suggests clear."""
        doc = Document("/c", 2)
        completions = list(completer.get_completions(doc, None))
        assert len(completions) == 1

    def test_e_prefix_suggests_edit_mode(self, completer):
        """Test /e prefix suggests edit_mode."""
        doc = Document("/e", 2)
        completions = list(completer.get_completions(doc, None))
        assert len(completions) == 1

    def test_unknown_command_suggests_nothing(self, completer):
        """Test unknown command suggests nothing."""
        doc = Document("/unknown", 8)
        completions = list(completer.get_completions(doc, None))
        assert len(completions) == 0

    def test_no_slash_prefix_suggests_nothing(self, completer):
        """Test no slash prefix suggests nothing."""
        doc = Document("help", 4)
        completions = list(completer.get_completions(doc, None))
        assert len(completions) == 0

    def test_slash_in_middle_suggests_nothing(self, completer):
        """Test slash in middle suggests nothing."""
        doc = Document("I want /help", 12)
        completions = list(completer.get_completions(doc, None))
        assert len(completions) == 0


class TestCommandList:
    """Test the command list is complete and correctly formatted."""

    def test_all_expected_commands_present(self, completer):
        """Test that all expected commands are in the completer."""
        expected_commands = {"/clear", "/edit_mode", "/help"}
        actual_commands = set(completer.commands)

        assert actual_commands == expected_commands

    def test_commands_are_properly_formatted(self, completer):
        """Test that all commands start with '/' and are lowercase."""
        for command in completer.commands:
            assert command.startswith("/"), f"Command '{command}' should start with '/'"
            assert (
                command.islower() or "_" in command
            ), f"Command '{command}' should be lowercase"


class TestFileCompleter:
    """Test suite for the FileCompleter class."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory with test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            # Create test files
            (tmppath / "config.py").touch()
            (tmppath / "README.md").touch()
            (tmppath / "test_file.txt").touch()
            (tmppath / "subdir").mkdir()
            (tmppath / ".hidden").touch()
            yield tmppath

    @pytest.fixture
    def file_completer(self, temp_dir):
        """Fixture providing FileCompleter in test directory."""
        try:
            original_cwd = os.getcwd()
        except FileNotFoundError:
            # If current directory doesn't exist, use a safe fallback
            original_cwd = str(Path.home())

        os.chdir(temp_dir)
        try:
            completer = FileCompleter()
            yield completer
        finally:
            try:
                os.chdir(original_cwd)
            except (FileNotFoundError, OSError):
                # If original directory no longer exists, go to home
                os.chdir(Path.home())

    def test_suggests_files_with_at_prefix(self, file_completer):
        """Test that files are suggested when input contains @."""
        doc = Document("@", 1)
        completions = list(file_completer.get_completions(doc, None))
        suggestions = [c.text for c in completions]

        assert "@config.py" in suggestions
        assert "@README.md" in suggestions
        assert "@test_file.txt" in suggestions
        assert "@subdir" in suggestions
        assert "@.hidden" in suggestions
        assert len(suggestions) == 5

    def test_fuzzy_matching_works(self, file_completer):
        """Test that fuzzy matching works for file completion."""
        doc = Document("@conf", 5)
        completions = list(file_completer.get_completions(doc, None))
        suggestions = [c.text for c in completions]

        assert "@config.py" in suggestions

    def test_no_suggestions_without_at_symbol(self, file_completer):
        """Test that no files are suggested when @ is not present."""
        doc = Document("config", 6)
        completions = list(file_completer.get_completions(doc, None))

        assert list(completions) == []

    def test_partial_file_matching(self, file_completer):
        """Test partial file name matching."""
        doc = Document("@test", 5)
        completions = list(file_completer.get_completions(doc, None))
        suggestions = [c.text for c in completions]

        assert "@test_file.txt" in suggestions

    def test_directory_included_in_suggestions(self, file_completer):
        """Test that directories are included in suggestions."""
        doc = Document("@sub", 4)
        completions = list(file_completer.get_completions(doc, None))
        suggestions = [c.text for c in completions]

        assert "@subdir" in suggestions

    def test_hidden_files_included(self, file_completer):
        """Test that hidden files (starting with .) are included."""
        doc = Document("@.", 2)
        completions = list(file_completer.get_completions(doc, None))
        suggestions = [c.text for c in completions]

        assert "@.hidden" in suggestions

    def test_at_symbol_in_middle_of_text(self, file_completer):
        """Test completion when @ symbol appears in middle of text."""
        doc = Document("please read @conf and tell me about it", 17)
        completions = list(file_completer.get_completions(doc, None))
        suggestions = [c.text for c in completions]

        # Should still work when @ is in middle
        assert "@config.py" in suggestions

    def test_multiple_at_symbols(self, file_completer):
        """Test behavior with multiple @ symbols."""
        doc = Document("compare @config.py and @README", 30)
        completions = list(file_completer.get_completions(doc, None))
        suggestions = [c.text for c in completions]

        # Should complete from the last @ symbol
        assert "@README.md" in suggestions

    def test_cwd_change_refreshes_files(self, temp_dir):
        """Test that changing directory refreshes the file list."""
        # Start in temp_dir
        os.chdir(temp_dir)
        completer = FileCompleter()

        # Get initial completions
        doc = Document("@", 1)
        initial_completions = list(completer.get_completions(doc, None))
        initial_suggestions = [c.text for c in initial_completions]

        # Create subdirectory with different files
        subdir = temp_dir / "subdir2"
        subdir.mkdir()
        (subdir / "different.py").touch()

        # Change to subdirectory
        os.chdir(subdir)

        # Get new completions (should refresh automatically)
        new_completions = list(completer.get_completions(doc, None))
        new_suggestions = [c.text for c in new_completions]

        # Should now show files from new directory
        assert "@different.py" in new_suggestions
        assert "@config.py" not in new_suggestions  # From parent dir

    def test_gitignore_filtering_works(self, temp_dir):
        """Test that files listed in .gitignore are excluded from completions."""
        # Create .gitignore file
        gitignore_content = """
# Python
__pycache__/
*.pyc
*.pyo
build/
dist/

# Node
node_modules/

# Specific files
secret.txt
"""
        (temp_dir / ".gitignore").write_text(gitignore_content)

        # Create files that should be ignored
        (temp_dir / "secret.txt").touch()
        (temp_dir / "regular.py").touch()  # This should NOT be ignored
        (temp_dir / "test.pyc").touch()  # This should be ignored
        (temp_dir / "__pycache__").mkdir()
        (temp_dir / "build").mkdir()
        (temp_dir / "node_modules").mkdir()

        # Change to temp directory and create completer
        try:
            original_cwd = os.getcwd()
        except FileNotFoundError:
            original_cwd = str(Path.home())

        os.chdir(temp_dir)
        try:
            completer = FileCompleter()

            # Get completions
            doc = Document("@", 1)
            completions = list(completer.get_completions(doc, None))
            suggestions = [c.text for c in completions]

            # Files that should appear
            assert "@regular.py" in suggestions
            assert "@.gitignore" in suggestions  # .gitignore itself should appear

            # Files that should be ignored
            assert "@secret.txt" not in suggestions
            assert "@test.pyc" not in suggestions
            assert "@__pycache__" not in suggestions
            assert "@build" not in suggestions
            assert "@node_modules" not in suggestions

        finally:
            try:
                os.chdir(original_cwd)
            except (FileNotFoundError, OSError):
                os.chdir(Path.home())

    def test_no_gitignore_shows_all_files(self, temp_dir):
        """Test that when no .gitignore exists, all files are shown."""
        # Create files without .gitignore
        (temp_dir / "secret.txt").touch()
        (temp_dir / "regular.py").touch()
        (temp_dir / "test.pyc").touch()

        # Change to temp directory and create completer
        try:
            original_cwd = os.getcwd()
        except FileNotFoundError:
            original_cwd = str(Path.home())

        os.chdir(temp_dir)
        try:
            completer = FileCompleter()

            # Get completions
            doc = Document("@", 1)
            completions = list(completer.get_completions(doc, None))
            suggestions = [c.text for c in completions]

            # All files should appear when no .gitignore
            assert "@secret.txt" in suggestions
            assert "@regular.py" in suggestions
            assert "@test.pyc" in suggestions

        finally:
            try:
                os.chdir(original_cwd)
            except (FileNotFoundError, OSError):
                os.chdir(Path.home())


class TestCombinedCompleter:
    """Test suite for the CombinedCompleter class."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory with test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            (tmppath / "config.py").touch()
            (tmppath / "help.md").touch()
            (tmppath / "README.md").touch()
            yield tmppath

    @pytest.fixture
    def combined_completer(self, temp_dir):
        """Fixture providing CombinedCompleter in test directory."""
        try:
            original_cwd = os.getcwd()
        except FileNotFoundError:
            # If current directory doesn't exist, use a safe fallback
            original_cwd = str(Path.home())

        os.chdir(temp_dir)
        try:
            completer = CombinedCompleter()
            yield completer
        finally:
            try:
                os.chdir(original_cwd)
            except (FileNotFoundError, OSError):
                # If original directory no longer exists, go to home
                os.chdir(Path.home())

    def test_slash_commands_work(self, combined_completer):
        """Test that slash commands still work in combined completer."""
        doc = Document("/h", 2)
        completions = list(combined_completer.get_completions(doc, None))
        suggestions = [c.text for c in completions]

        assert "/help" in suggestions

    def test_file_completion_works(self, combined_completer):
        """Test that file completion works in combined completer."""
        doc = Document("@conf", 5)
        completions = list(combined_completer.get_completions(doc, None))
        suggestions = [c.text for c in completions]

        assert "@config.py" in suggestions

    def test_both_completions_can_coexist(self, combined_completer):
        """Test that both types of completion don't interfere with each other."""
        # Test slash completion
        doc = Document("/clear", 6)
        completions = list(combined_completer.get_completions(doc, None))
        suggestions = [c.text for c in completions]
        assert "/clear" in suggestions

        # Test file completion
        doc = Document("@help", 5)
        completions = list(combined_completer.get_completions(doc, None))
        suggestions = [c.text for c in completions]
        assert "@help.md" in suggestions

    def test_no_interference_with_normal_text(self, combined_completer):
        """Test that normal text doesn't trigger any completions."""
        doc = Document("normal text without special prefixes", 36)
        completions = list(combined_completer.get_completions(doc, None))

        assert list(completions) == []

    def test_mixed_input_scenarios(self, combined_completer):
        """Test various mixed input scenarios."""
        # Text with @ but partial file match - should trigger file completion only
        doc = Document("read @conf", 10)  # Partial match for config.py
        completions = list(combined_completer.get_completions(doc, None))
        suggestions = [c.text for c in completions]

        assert "@config.py" in suggestions
        assert "/help" not in suggestions  # Slash commands shouldn't appear

        # Slash at start shouldn't trigger file completion for unrelated files
        doc = Document("/", 1)
        completions = list(combined_completer.get_completions(doc, None))
        suggestions = [c.text for c in completions]

        assert "/help" in suggestions
        assert "/clear" in suggestions
        assert "/edit_mode" in suggestions
        # File completions shouldn't appear for bare slash
        assert "@config.py" not in suggestions

    def test_completer_components_are_separate(self, combined_completer):
        """Test that the completer properly uses separate completer instances."""
        assert hasattr(combined_completer, "_slash_completer")
        assert hasattr(combined_completer, "_file_completer")
        assert isinstance(combined_completer._slash_completer, SlashCommandCompleter)
        assert isinstance(combined_completer._file_completer, FileCompleter)

    def test_bare_slash_shows_only_commands(self, combined_completer):
        """Test that bare slash shows only commands."""
        doc = Document("/", 1)
        completions = list(combined_completer.get_completions(doc, None))
        suggestions = [c.text for c in completions]

        has_slash_commands = any(s.startswith("/") for s in suggestions)
        has_file_completions = any(s.startswith("@") for s in suggestions)

        assert has_slash_commands is True
        assert has_file_completions is False

    def test_bare_at_shows_only_files(self, combined_completer):
        """Test that bare @ shows only files."""
        doc = Document("@", 1)
        completions = list(combined_completer.get_completions(doc, None))
        suggestions = [c.text for c in completions]

        has_slash_commands = any(s.startswith("/") for s in suggestions)
        has_file_completions = any(s.startswith("@") for s in suggestions)

        assert has_slash_commands is False
        assert has_file_completions is True

    def test_normal_text_shows_nothing(self, combined_completer):
        """Test that normal text shows no completions."""
        doc = Document("normal text", 11)
        completions = list(combined_completer.get_completions(doc, None))
        suggestions = [c.text for c in completions]

        has_slash_commands = any(s.startswith("/") for s in suggestions)
        has_file_completions = any(s.startswith("@") for s in suggestions)

        assert has_slash_commands is False
        assert has_file_completions is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
