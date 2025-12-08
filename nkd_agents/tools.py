import contextvars
import difflib
import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

from .llm import llm
from .logging import IS_TTY, logging_context

logger = logging.getLogger(__name__)


def _display_diff(old: str, new: str, path: str) -> None:
    """Display a colorized unified diff in the console."""
    logger.info(f"\nUpdate: {path}")

    diff = difflib.unified_diff(old.splitlines(), new.splitlines(), lineterm="")

    for line in diff:
        color = ""
        if IS_TTY:
            red, green = "\033[31m", "\033[32m"
            color = green if line[0] == "+" else red if line[0] == "-" else ""
        logger.info(f"{color}{line}\033[0m")


_sandbox_dir: contextvars.ContextVar[Path | None] = contextvars.ContextVar(
    "sandbox_dir", default=None
)


def _resolve_path(path: str) -> Path:
    """Resolve a path, enforcing sandbox restrictions if active.

    When sandbox is active, treats all paths as relative to the sandbox directory
    and prevents escaping via .. or absolute paths.

    Returns:
        Resolved Path object

    Raises:
        ValueError: If path attempts to escape sandbox when sandbox is active
    """
    sandbox_dir = _sandbox_dir.get()

    if sandbox_dir is None:
        return Path(path).resolve()

    resolved = (sandbox_dir / path).resolve()

    try:
        resolved.relative_to(sandbox_dir)
    except ValueError:
        raise ValueError(f"Error: Path '{path}' is outside sandbox directory")

    return resolved


async def sandbox():
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
    """Read and return the contents of a file at the given path. Only works with files, not directories.

    Returns one of the following strings:
    - File contents on success
    - "Error: File '{path}' not found"
    - "Error: Permission denied accessing '{path}'"
    - "Error: Path '{path}' is outside sandbox directory" (when sandbox is active)
    """
    try:
        resolved_path = _resolve_path(path)
        content = resolved_path.read_text(encoding="utf-8")
        logger.info(f"\nRead: {resolved_path}\n")
        return content
    except FileNotFoundError:
        return f"Error: File '{path}' not found"
    except PermissionError:
        return f"Error: Permission denied accessing '{path}'"
    except ValueError as e:
        return str(e)
    except Exception as e:
        return f"Error reading file '{path}': {str(e)}"


async def edit_file(path: str, old_str: str, new_str: str) -> str:
    """Replace old_str with new_str in the file at path. For multiple edits to the same file,
    call this function multiple times with smaller edits rather than one large edit.

    Returns one of the following strings:
    - "Success: Updated {path}"
    - "Error: File '{path}' is empty"
    - "Error: old_str not found in file content"
    - "Error: old_str and new_str must be different"
    - "Error: File '{path}' not found"
    - "Error: Permission denied accessing '{path}'"
    - "Error: Path '{path}' is outside sandbox directory" (when sandbox is active)
    """
    try:
        resolved_path = _resolve_path(path)
        content = resolved_path.read_text(encoding="utf-8")
        if content == "":
            return f"Error: File '{path}' is empty"
        if old_str not in content:
            return "Error: old_str not found in file content"
        if old_str == new_str:
            return "Error: old_str and new_str must be different"

        edited_content = content.replace(old_str, new_str)
        _display_diff(content, edited_content, str(resolved_path))
        resolved_path.write_text(edited_content, encoding="utf-8")
        logger.info(f"\nUpdated: {resolved_path}\n")
        return f"Success: Updated {resolved_path}"
    except FileNotFoundError:
        return f"Error: File '{path}' not found"
    except PermissionError:
        return f"Error: Permission denied accessing '{path}'"
    except ValueError as e:
        return str(e)
    except Exception as e:
        return f"Error editing file '{path}': {str(e)}"


async def execute_bash(command: str) -> str:
    """Execute a bash command and return the results.

    When sandbox is active, the command runs with cwd set to the sandbox directory.

    Returns one of the following strings:
    - "STDOUT:\n{stdout}\nSTDERR:\n{stderr}\nEXIT CODE: {returncode}"
    - "Error executing command: {str(e)}"
    """
    logger.info(f"Executing Bash: { '\033[32m' if IS_TTY else '' } {command} \033[0m")
    try:
        sandbox_dir = _sandbox_dir.get()
        cwd = sandbox_dir if sandbox_dir is not None else Path.cwd()

        input = ["bash", "-c", command]
        result = subprocess.run(
            input, capture_output=True, text=True, timeout=10, cwd=cwd
        )
        logger.info(
            f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}\nEXIT CODE: {result.returncode}"
        )
        return f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}\nEXIT CODE: {result.returncode}"
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
        Summary of what the sub-agent accomplishedRe
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
