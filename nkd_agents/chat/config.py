import logging
import os

from anthropic.types import MessageParam
from prompt_toolkit import PromptSession, key_binding, styles
from rich.console import Console

logger = logging.getLogger(__name__)
console = Console()

HELP = """
[dim]In sandbox mode, cwd is mounted at /workspace in the container.

Anthropic API Key: {masked_key}

Keyboard Shortcuts:
- '?': show this help message
- 'Esc'+'Esc': clear input while typing
- 'Shift+Tab': toggle edit approval
- 'Ctrl+L': clear message history
[/dim]"""


def get_help() -> str:
    """Generate help text with current API key."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    masked_key = "*" * (len(api_key) - 4) + api_key[-4:] if api_key else "Not set"
    return HELP.format(masked_key=masked_key)


msg_history: list[MessageParam] = []
kb = key_binding.KeyBindings()


@kb.add("escape", "escape")
def _(event):
    buffer = event.app.current_buffer
    buffer.text = ""
    buffer.cursor_position = 0


@kb.add("s-tab")
def _(event):
    current = os.getenv("ACCEPT_EDITS", "false").lower() == "true"
    os.environ["ACCEPT_EDITS"] = str(not current).lower()
    logger.info(f"[dim][Accept Edits: {'✓' if not current else '✗'}][/dim]")


@kb.add("?")
def _(event):
    buffer = event.app.current_buffer
    if buffer.text == "":
        logger.info(get_help())
        buffer.text = ""
    else:
        buffer.insert_text("?")


@kb.add("c-l")
def _(event):
    msg_history.clear()
    logger.info("[dim]Message history cleared[/dim]")


styles = styles.Style.from_dict({"": "ansibrightblack"})
session = PromptSession(key_bindings=kb, style=styles)
