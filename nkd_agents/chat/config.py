import logging
import os

from anthropic.types import MessageParam
from prompt_toolkit import PromptSession, key_binding, styles
from rich.console import Console

logger = logging.getLogger(__name__)
console = Console()

HELP = """
[dim][bold]Anthropic API Key:[/bold] {masked_key}

Keyboard Shortcuts:
- '?': show this help message
- 'Esc'+'Esc': clear input while typing
- 'Tab': toggle thinking w/ `2048` token budget
- 'Ctrl+L': clear message history

Coming Soon:
- 'Shift+Tab': toggle edit approval

[/dim]"""


def get_help() -> str:
    """Generate help text with current API key."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    masked_key = "*" * (len(api_key) - 4) + api_key[-4:] if api_key else "Not Set"
    return HELP.format(masked_key=masked_key)


msg_history: list[MessageParam] = []
thinking = {"budget": 2048}
kb = key_binding.KeyBindings()


@kb.add("escape", "escape")
def _(event):
    buffer = event.app.current_buffer
    buffer.text = ""
    buffer.cursor_position = 0


# @kb.add("s-tab")
# def _(event):
#     current = os.getenv("ACCEPT_EDITS", "false").lower() == "true"
#     os.environ["ACCEPT_EDITS"] = str(not current).lower()
#     logger.info(f"[dim][Accept Edits: {'✓' if not current else '✗'}][/dim]")


@kb.add("?")
def _(event):
    buffer = event.app.current_buffer
    if buffer.text == "":
        logger.info(get_help())
        buffer.text = ""
    else:
        buffer.insert_text("?")


@kb.add("tab")
def _(event):
    current = int(os.getenv("ANTHROPIC_THINKING_BUDGET", "0")) > 0
    os.environ["ANTHROPIC_THINKING_BUDGET"] = "2048" if not current else "0"
    logger.info(f"[dim]\nThinking: {'✓' if not current else '✗'}\n[/dim]")


@kb.add("c-l")
def _(event):
    length = len(msg_history)
    logger.info(f"[dim]\n{msg_history}\n[/dim]")
    msg_history.clear()
    logger.info(f"[dim]\nCleared {length} messages from history\n[/dim]")


styles = styles.Style.from_dict({"": "ansibrightblack"})
session = PromptSession(key_bindings=kb, style=styles)
