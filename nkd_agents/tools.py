import contextvars
import difflib
import logging
import shutil
import subprocess
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from .llm import llm
from .logging import GREEN_TTY, RED_TTY, RESET_TTY, logging_context

logger = logging.getLogger(__name__)
_sandbox_dir: contextvars.ContextVar[Path | None] = contextvars.ContextVar(
    "sandbox_dir", default=None
)


def _display_diff(old: str, new: str, path: str) -> None:
    """Display a colorized unified diff in the console."""
    diff = difflib.unified_diff(old.splitlines(), new.splitlines(), lineterm="")

    lines = [f"\nUpdate: {path}"]
    for line in diff:
        color = GREEN_TTY if line[0] == "+" else RED_TTY if line[0] == "-" else ""
        lines.append(f"{color}{line}{RESET_TTY}")

    logger.info("\n".join(lines))


def _resolve_path(path: str) -> Path:
    """Resolve a path, enforcing sandbox restrictions if active."""
    sd = _sandbox_dir.get()
    sd = sd.resolve() if sd is not None else None

    if sd is not None and Path(path).is_absolute():
        raise ValueError(f"Absolute paths not allowed, use relative paths: '{path}'")

    resolved = Path(path).resolve() if sd is None else (sd / path).resolve()
    if sd and not resolved.is_relative_to(sd):
        raise ValueError(f"Error: Path '{path}' is outside sandbox directory")
    return resolved


@asynccontextmanager
async def sandbox() -> AsyncGenerator[Path, None]:
    """Async context manager that restricts file operations to a temporary directory.

    When active, all file paths are resolved relative to the sandbox directory
    and cannot escape it. The temporary directory is cleaned up on exit.
    """
    sandbox_path = Path(tempfile.mkdtemp())
    token = _sandbox_dir.set(sandbox_path)
    try:
        yield sandbox_path
    finally:
        _sandbox_dir.reset(token)
        shutil.rmtree(sandbox_path, ignore_errors=True)


async def read_file(path: str) -> str:
    """Read and return the contents of a file at the given path. Only works with files, not directories."""
    try:
        resolved_path = _resolve_path(path)
        content = resolved_path.read_text(encoding="utf-8")
        logger.info(f"\nRead: {GREEN_TTY}{resolved_path}{RESET_TTY}\n")
        return content
    except Exception as e:
        logger.error(f"Error reading file '{path}': {str(e)}")
        return f"Error reading file '{path}': {str(e)}"


async def edit_file(path: str, old_str: str, new_str: str) -> str:
    """Create or edit an existing file.
    For creation: provide the new path and set old_str=""
    For editing: Replaces old_str with new_str in the file at the provided path.
    For multiple edits to the same file, call this function multiple times with smaller edits rather than one large edit.

    Returns one of the following strings:
    - "Success: Updated {path}"
    - "Error: File '{path}' is empty"
    - "Error: old_str not found in file content"
    - "Error: old_str and new_str must be different"
    - "Error: File '{path}' not found"
    - "Error editing file '{path}': {error description}" (for other failures)
    """
    if old_str == new_str:
        return "Error: old_str and new_str must be different"

    try:
        resolved_path = _resolve_path(path)

        if resolved_path.exists():
            content = resolved_path.read_text(encoding="utf-8")
            if old_str != "" and old_str not in content:
                return "Error: old_str not found in file content"
            edited_content = content.replace(old_str, new_str)
        else:
            if old_str != "":
                return f"Error: File '{path}' not found"
            content, edited_content = "", new_str

        _display_diff(content, edited_content, str(resolved_path))
        resolved_path.write_text(edited_content, encoding="utf-8")
        return f"Success: Updated{resolved_path}"
    except Exception as e:
        logger.error(f"Error editing file '{path}': {str(e)}")
        return f"Error editing file '{path}': {str(e)}"


async def execute_bash(command: str) -> str:
    """Execute a bash command and return the results.

    When sandbox is active, the command runs with cwd set to the sandbox directory.

    Returns one of the following strings:
    - "STDOUT:\n{stdout}\nSTDERR:\n{stderr}\nEXIT CODE: {returncode}"
    - "Error executing command: {str(e)}"
    """
    logger.info(f"Executing Bash: {GREEN_TTY}{command}{RESET_TTY}")
    try:
        sandbox_dir = _sandbox_dir.get()
        cwd = sandbox_dir if sandbox_dir is not None else Path.cwd()

        input = ["bash", "-c", command]
        result = subprocess.run(
            input, capture_output=True, text=True, timeout=10, cwd=cwd
        )
        result_str = f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}\nEXIT CODE: {result.returncode}"
        logger.info(result_str)
        return result_str
    except Exception as e:
        return f"Error executing command: {str(e)}"


async def subtask(prompt: str, task_label: str) -> str:
    """Spawn a sub-agent to work on a specific task autonomously.

    The sub-agent will work on the given task with access to file read/edit and bash execution tools.
    Use this for complex, multi-step tasks that benefit from focused attention.

    Args:
        prompt: Detailed description of what the sub-agent should accomplish. Be specific about:
            - What the task is and why it's needed
            - What files or resources might be relevant
            - What the expected output or outcome should be
            - Any constraints or requirements
        task_label: Short 3-5 word summary of the task for progress tracking

    Returns:
        Response from the sub-agent
    """
    logging_context.set({"subtask": task_label})

    try:
        tools = [read_file, edit_file, execute_bash]
        thinking = {"type": "enabled", "budget_tokens": 2048}
        response = await llm(prompt, tools=tools, thinking=thinking, max_tokens=20000)
        logger.info(f"✓ subtask '{task_label}' complete: {response}\n")
        return f"subtask '{task_label}' complete: {response}"

    except Exception as e:
        logger.exception(f"\n✗ subtask '{task_label}' failed: {str(e)}\n", exc_info=e)
        return f"subtask '{task_label}' failed: {str(e)}"
