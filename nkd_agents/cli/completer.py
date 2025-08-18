from pathlib import Path

import pathspec
from prompt_toolkit.completion import (
    Completer,
    Completion,
    FuzzyCompleter,
    WordCompleter,
)
from prompt_toolkit.document import Document


class SlashCommandCompleter(Completer):
    """Custom completer that only suggests slash commands at the start of input"""

    def __init__(self):
        self.commands = ["/clear", "/edit_mode", "/help"]

    def get_completions(self, document: Document, complete_event):
        # Only complete at the beginning of the line and if it starts with '/'
        if document.cursor_position == len(document.text) and document.text.startswith(
            "/"
        ):
            for cmd in self.commands:
                if cmd.startswith(document.text.lower()):
                    yield Completion(cmd, start_position=-len(document.text))


class FileCompleter(Completer):
    """Fuzzy file completer for @filename completion that respects .gitignore"""

    def __init__(self):
        self._completer = None
        self._last_cwd = None
        self._gitignore_spec = None

    def _load_gitignore(self):
        """Load and parse .gitignore file if it exists"""
        gitignore_path = Path(".gitignore")
        if gitignore_path.exists():
            self._gitignore_spec = pathspec.PathSpec.from_lines(
                "gitwildmatch", gitignore_path.read_text(encoding="utf-8").splitlines()
            )
        else:
            self._gitignore_spec = None

    def _is_ignored(self, path: Path) -> bool:
        """Check if a path should be ignored based on .gitignore"""
        if self._gitignore_spec is None:
            return False

        # Use the relative path from current directory
        path_str = str(path)

        # Check both with and without trailing slash for directories
        is_ignored = self._gitignore_spec.match_file(path_str)
        if not is_ignored and path.is_dir():
            is_ignored = self._gitignore_spec.match_file(path_str + "/")

        return is_ignored

    def _get_all_files(
        self, directory: Path | None = None, max_depth: int = 3
    ) -> list[str]:
        """Recursively get all files, respecting gitignore"""
        if directory is None:
            directory = Path(".")

        files = []

        def _walk_directory(current_dir: Path, current_depth: int = 0):
            if current_depth > max_depth:
                return

            try:
                for path in current_dir.iterdir():
                    relative_path = path.relative_to(Path("."))
                    if self._is_ignored(relative_path):
                        continue

                    files.append(f"@{relative_path}")
                    if path.is_dir():
                        _walk_directory(path, current_depth + 1)

            except PermissionError:
                # Skip directories we can't read
                pass

        _walk_directory(directory)
        return files

    def _refresh_files(self):
        """Refresh file list if CWD changed, excluding gitignored files"""
        current_cwd = Path.cwd()
        if self._completer is None or self._last_cwd != current_cwd:
            self._load_gitignore()

            files = self._get_all_files()

            self._completer = FuzzyCompleter(WordCompleter(files))
            self._last_cwd = current_cwd

    def get_completions(self, document: Document, complete_event):
        # Find the current word being typed (from cursor backwards to whitespace or start)
        text_before_cursor = document.text_before_cursor

        # Find the start of the current word
        word_start = text_before_cursor.rfind(" ") + 1
        current_word = text_before_cursor[word_start:]

        # Only complete if we're currently typing a word that starts with @
        if current_word.startswith("@"):
            self._refresh_files()
            if self._completer is not None:
                yield from self._completer.get_completions(document, complete_event)


class CombinedCompleter(Completer):
    """Combines slash command and file completion"""

    def __init__(self):
        self._slash_completer = SlashCommandCompleter()
        self._file_completer = FileCompleter()

    @property
    def commands(self):
        return self._slash_completer.commands

    def get_completions(self, document, complete_event):
        yield from self._slash_completer.get_completions(document, complete_event)
        yield from self._file_completer.get_completions(document, complete_event)
