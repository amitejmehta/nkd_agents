import difflib
import logging
import subprocess
from pathlib import Path

from .llm import llm
from .logging import GREEN, RED, RESET, logging_context

logger = logging.getLogger(__name__)


def _display_diff(old: str, new: str, path: str) -> None:
    """Display a colorized unified diff in the console."""
    diff = difflib.unified_diff(old.splitlines(), new.splitlines(), lineterm="")

    lines = [f"\nUpdate: {path}"]
    for line in diff:
        color = GREEN if line[0] == "+" else RED if line[0] == "-" else ""
        lines.append(f"{color}{line}{RESET}")

    logger.info("\n".join(lines))


async def read_file(path: str) -> str:
    """Read and return the contents of a file at the given path. Only works with files, not directories."""
    try:
        resolved_path = Path(path).resolve()
        content = resolved_path.read_text(encoding="utf-8")
        logger.info(f"\nRead: {GREEN}{resolved_path}{RESET}\n")
        return content
    except Exception as e:
        logger.info(f"Error reading file '{path}': {str(e)}")
        return f"Error reading file '{path}': {str(e)}"


async def edit_file(path: str, old_str: str, new_str: str, count: int = 1) -> str:
    """Create or edit an existing file.
    For creation: provide the new path and set old_str=""
    For editing: Replaces occurrences of old_str with new_str in the file at the provided path.
    By default, only the first occurrence is replaced. Set count=-1 to replace all occurrences.
    For multiple edits to the same file, call this function multiple times with smaller edits rather than one large edit.

    Args:
        path: Path to the file
        old_str: String to search for (use "" for file creation)
        new_str: String to replace with
        count: Maximum number of occurrences to replace (default: 1, use -1 for all)

    Returns one of the following strings:
    - "Success: Updated {path}"
    - "Error: old_str not found in file content"
    - "Error: old_str and new_str must be different"
    - "Error: File '{path}' not found"
    - "Error editing file '{path}': {error description}" (for other failures)
    """
    if old_str == new_str:
        return "Error: old_str and new_str must be different"

    try:
        resolved_path = Path(path).resolve()

        if resolved_path.exists():
            content = resolved_path.read_text(encoding="utf-8")
            if old_str != "" and old_str not in content:
                return "Error: old_str not found in file content"
            edited_content = content.replace(old_str, new_str, count)
        else:
            if old_str != "":
                return f"Error: File '{path}' not found"
            content, edited_content = "", new_str

        _display_diff(content, edited_content, str(resolved_path))
        resolved_path.parent.mkdir(parents=True, exist_ok=True)
        resolved_path.write_text(edited_content, encoding="utf-8")
        return f"Success: Updated {resolved_path}"
    except Exception as e:
        logger.info(f"Error editing file '{path}': {str(e)}")
        return f"Error editing file '{path}': {str(e)}"


async def execute_bash(command: str) -> str:
    """Execute a bash command and return the results.

    Returns one of the following strings:
    - "STDOUT:\n{stdout}\nSTDERR:\n{stderr}\nEXIT CODE: {returncode}"
    - "Error executing command: {str(e)}"
    """
    logger.info(f"Executing Bash: {GREEN}{command}{RESET}")
    try:
        result = subprocess.run(
            ["bash", "-c", command], capture_output=True, text=True, cwd=Path.cwd()
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
