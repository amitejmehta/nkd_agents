import asyncio
import base64
import hashlib
import logging
import tempfile
from contextvars import ContextVar
from pathlib import Path
from typing import Literal

import httpx
import trafilatura
from anthropic.types.beta import BetaBase64ImageSourceParam, BetaBase64PDFSourceParam
from anthropic.types.beta.beta_tool_result_block_param import Content
from playwright.async_api import async_playwright

from .anthropic import llm, user
from .logging import GREEN, RESET, logging_ctx
from .utils import display_diff

logger = logging.getLogger(__name__)

# Context variable for sandbox directory - when set, all file operations (read_file,
# edit_file, bash) are restricted to this directory. Only relative paths are
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


async def read_file(
    path: str,
    media_type: Literal[
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp",
        "application/pdf",
        "text/plain",
    ] = "text/plain",
) -> str | list[Content]:
    """Read and return the contents of a file at the given path. Only works with files, not directories.
    Supports image (jpg, jpeg, png, gif, webp), PDF, and all text files."""
    try:
        resolved_path = resolve_path(path)
        if isinstance(resolved_path, str):  # Error message
            return resolved_path

        logger.info(f"\nReading: {GREEN}{resolved_path}{RESET}\n")
        bytes = resolved_path.read_bytes()

        if media_type in ("image/jpeg", "image/png", "image/gif", "image/webp"):
            source = BetaBase64ImageSourceParam(
                type="base64",
                media_type=media_type,
                data=base64.standard_b64encode(bytes).decode("utf-8"),
            )
            return [{"type": "image", "source": source}]
        elif media_type == "application/pdf":
            source = BetaBase64PDFSourceParam(
                type="base64",
                media_type="application/pdf",
                data=base64.standard_b64encode(bytes).decode("utf-8"),
            )
            return [{"type": "document", "source": source}]
        else:
            text = bytes.decode("utf-8", errors="ignore").strip()
            return [{"type": "text", "text": text}]
    except Exception as e:
        logger.warning(f"Error reading file '{path}': {str(e)}")
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
    try:
        if old_str == new_str:
            return "Error: old_str and new_str must be different"

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
        logger.warning(f"Error editing file '{path}': {str(e)}")
        return f"Error editing file '{path}': {str(e)}"


async def bash(command: str) -> str:
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
        logger.warning(f"Error executing bash command: {str(e)}")
        return f"Error executing bash command: {str(e)}"


async def web_search(query: str, max_results: int = 5) -> str:
    """Search the web using DuckDuckGo via headless browser.

    Args:
        query: Search query string
        max_results: Maximum number of results to return (default: 5)

    Returns:
        Search results as text, or error message.
        Use fetch_url to get full content of interesting URLs.
    """
    try:
        logger.info(f"Searching: {GREEN}{query}{RESET}")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, channel="chrome")
            ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            ctx = await browser.new_context(user_agent=ua)
            page = await ctx.new_page()
            await page.goto(f"https://duckduckgo.com/?q={query}&ia=web")
            await page.wait_for_selector("article", timeout=10000)
            results = await page.eval_on_selector_all(
                "article",
                """els => els.slice(0, %d).map(el => {
                    const a = el.querySelector('a[data-testid="result-title-a"]');
                    const snippet = el.querySelector('div[data-result="snippet"]');
                    return {
                        title: a?.innerText || '',
                        url: a?.href || '',
                        snippet: snippet?.innerText || ''
                    };
                }).filter(r => r.url)"""
                % max_results,
            )
            await browser.close()

        if not results:
            return "No results found"
        output = "\n\n".join(
            f"Title: {r['title']}\nURL: {r['url']}\nSnippet: {r['snippet']}"
            for r in results
        )
        logger.info(f"Found {len(results)} results:\n{output}")
        return output
    except Exception as e:
        logger.warning(f"Error searching '{query}': {str(e)}")
        return f"Error searching '{query}': {str(e)}"


async def fetch_url(url: str) -> str:
    """Fetch a webpage, extract main content, and save to a temp file.

    Args:
        url: The URL to fetch

    Returns:
        Path to temp file containing extracted text, or error message.
        Use bash with grep/head/tail to explore the content.
    """
    try:
        logger.info(f"Fetching: {GREEN}{url}{RESET}")
        async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
            response = await client.get(url)
            response.raise_for_status()

        text = trafilatura.extract(response.text) or response.text[:50000]
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        filepath = Path(tempfile.gettempdir()) / f"fetch_{url_hash}.txt"
        filepath.write_text(text, encoding="utf-8")
        logger.info(f"Saved {len(text)} chars to {filepath}")
        return f"Saved {len(text)} chars to {filepath}"
    except Exception as e:
        logger.warning(f"Error fetching '{url}': {str(e)}")
        return f"Error fetching '{url}': {str(e)}"


async def subtask(
    prompt: str, task_label: str, model: Literal["haiku", "sonnet"]
) -> str:
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
        model: model to use for the subtask. use haiku for all simple tasks, otherwise sonnet.
    Returns:
        Response from the sub-agent
    """
    try:
        logging_ctx.set({"subtask": task_label})
        tools = [read_file, edit_file, bash, fetch_url, web_search]
        kwargs = {"model": f"claude-{model}-4-5", "max_tokens": 20000}
        response = await llm([user(prompt)], fns=tools, **kwargs)
        logger.info(f"✓ subtask '{task_label}' complete: {response}\n")
        return f"subtask '{task_label}' complete: {response}"
    except Exception as e:
        logger.warning(f"Error executing subtask '{task_label}': {str(e)}")
        return f"Error executing subtask '{task_label}': {str(e)}"
