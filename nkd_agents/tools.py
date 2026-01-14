import asyncio
import base64
import logging
from contextvars import ContextVar
from pathlib import Path
from typing import Literal

from anthropic import AsyncAnthropic
from anthropic.types.beta import BetaImageBlockParam
from anthropic.types.beta.beta_base64_image_source_param import (
    BetaBase64ImageSourceParam,
)

from .anthropic import llm
from .logging import GREEN, RESET, logging_ctx
from .utils import display_diff

logger = logging.getLogger(__name__)

# Context variable for sandbox directory - when set, all file operations (read_file,
# edit_file, execute_bash) are restricted to this directory. Only relative paths are
# allowed when sandbox is active (absolute paths will error). This prevents escaping the sandbox.
sandbox_ctx = ContextVar[str | None]("sandbox_ctx", default=None)


def resolve_path(path: str) -> Path | str:
    """Resolve a path respecting sandbox_ctx if set.

    Returns:
        Path object if path is valid and allowed
        Error string if path violates sandbox rules
    """
    # When sandbox is set, only allow relative paths inside sandbox
    sandbox_dir = sandbox_ctx.get()
    if sandbox_dir:
        if Path(path).is_absolute():
            return f"Error: Absolute paths not allowed when sandbox is set. Use relative path: {path}"
        sandbox_path = Path(sandbox_dir).resolve()
        resolved_path = (sandbox_path / path).resolve()
        # Prevent escaping sandbox with ../
        if not str(resolved_path).startswith(str(sandbox_path)):
            return f"Error: Path escapes sandbox: {path}"
        return resolved_path
    else:
        return Path(path).resolve()


async def read_file(path: str) -> str:
    """Read and return the contents of a file at the given path. Only works with files, not directories."""
    try:
        resolved_path = resolve_path(path)
        if isinstance(resolved_path, str):  # Error message
            return resolved_path

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
        resolved_path = resolve_path(path)
        if isinstance(resolved_path, str):  # Error message
            return resolved_path

        if resolved_path.exists():
            content = resolved_path.read_text(encoding="utf-8")
            if old_str != "" and old_str not in content:
                return "Error: old_str not found in file content"
            edited_content = content.replace(old_str, new_str, count)
        else:
            if old_str != "":
                return f"Error: File '{path}' not found"
            content, edited_content = "", new_str

        display_diff(content, edited_content, str(resolved_path))
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
    process = None
    try:
        sandbox_dir = sandbox_ctx.get()
        process = await asyncio.create_subprocess_exec(
            "bash",
            "-c",
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=Path(sandbox_dir) if sandbox_dir else Path.cwd(),
        )
        stdout, stderr = await process.communicate()

        result_str = f"STDOUT:\n{stdout.decode()}\nSTDERR:\n{stderr.decode()}\nEXIT CODE: {process.returncode}"
        logger.info(result_str)
        return result_str
    except asyncio.CancelledError:
        if process is not None and process.returncode is None:
            process.kill()
            await process.wait()
        raise
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
    logging_ctx.set({"subtask": task_label})

    try:
        tools = [read_file, edit_file, execute_bash]
        async with AsyncAnthropic() as client:
            response = await llm(prompt, client, tools=tools, max_tokens=20000)
        logger.info(f"✓ subtask '{task_label}' complete: {response}\n")
        return f"subtask '{task_label}' complete: {response}"

    except Exception as e:
        logger.info(f"\n✗ subtask '{task_label}' failed: {str(e)}\n")
        return f"subtask '{task_label}' failed: {str(e)}"


async def load_image(
    path: str, media_type: Literal["image/jpeg", "image/png", "image/gif", "image/webp"]
) -> list[BetaImageBlockParam] | str:
    """Load an image from a given path. Supports jpg, jpeg, png, gif, and webp."""
    try:
        with open(path, "rb") as image_file:
            image_data = image_file.read()
        data = base64.standard_b64encode(image_data).decode("utf-8")
        source = BetaBase64ImageSourceParam(
            type="base64", media_type=media_type, data=data
        )
        return [{"type": "image", "source": source}]
    except Exception as e:
        return f"Error loading image '{path}': {str(e)}"
