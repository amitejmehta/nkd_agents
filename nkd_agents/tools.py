import difflib
import logging
import subprocess
from pathlib import Path

from .llm import llm
from .logging import logging_context

logger = logging.getLogger(__name__)


def _display_diff(old: str, new: str, path: str) -> None:
    """Display a colorized unified diff in the console."""
    logger.info(f"\n[bold]Update({path})[/bold]")

    diff = difflib.unified_diff(
        old.splitlines(),
        new.splitlines(),
        lineterm="",
        n=3,
    )

    for line in diff:
        color = "[red]" if line[0] == "-" else "[green]" if line[0] == "+" else "[dim]"
        logger.info(f"{color}{line}[/{color.strip('[')}]")


async def read_file(path: str) -> str:
    """Read and return the contents of a file at the given path. Only works with files, not directories.

    Returns one of the following strings:
    - File contents on success
    - "Error: File '{path}' not found"
    - "Error: Permission denied accessing '{path}'"
    """
    try:
        content = Path(path).read_text(encoding="utf-8")
        logger.info(f"\n[bold]Read({path})[/bold]\n")
        return content
    except FileNotFoundError:
        return f"Error: File '{path}' not found"
    except PermissionError:
        return f"Error: Permission denied accessing '{path}'"
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
    """
    try:
        content = Path(path).read_text(encoding="utf-8")
        if content == "":
            return f"Error: File '{path}' is empty"
        if old_str not in content:
            return "Error: old_str not found in file content"
        if old_str == new_str:
            return "Error: old_str and new_str must be different"

        edited_content = content.replace(old_str, new_str)
        _display_diff(content, edited_content, path)
        Path(path).write_text(edited_content, encoding="utf-8")
        logger.info(f"\n[bold]Updated {path}[/bold]\n")
        return f"Success: Updated {path}"
    except FileNotFoundError:
        return f"Error: File '{path}' not found"
    except PermissionError:
        return f"Error: Permission denied accessing '{path}'"
    except Exception as e:
        return f"Error editing file '{path}': {str(e)}"


async def execute_bash(command: str) -> str:
    """Execute a bash command and return the results.

    Returns one of the following strings:
    - "STDOUT:\n{stdout}\nSTDERR:\n{stderr}\nEXIT CODE: {returncode}"
    - "Error executing command: {str(e)}"
    """
    try:
        input = ["bash", "-c", command]
        result = subprocess.run(
            input, capture_output=True, text=True, timeout=10, cwd=Path.cwd()
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
