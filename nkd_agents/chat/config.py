import logging
import os

from anthropic.types import MessageParam
from prompt_toolkit import PromptSession, key_binding, styles
from prompt_toolkit.key_binding.key_processor import KeyPressEvent
from rich.console import Console

logger = logging.getLogger(__name__)
console = Console()
DIM = "\033[38;5;242m"
RESET = "\033[0m"

HELP_TEXT_TEMPLATE = f"""
{DIM}Anthropic API Key:{{masked_key}}

Commands:
- 'clear' - clear message history

Keyboard Shortcuts:
- enter - send message
- esc+esc - clear all input while typing
- ctrl+u - clear last line of typing
- ctrl+c - interrupt LLM
- ctrl+d - exit
- tab - toggle thinking w/ `2048` token budget

Coming Soon:
- shift+tab - toggle edit approval{RESET}\n"""


def display_help_text() -> str:
    """Generate help text with current API key."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    masked_key = "*" * (len(api_key) - 4) + api_key[-4:] if api_key else "Not Set"
    return HELP_TEXT_TEMPLATE.format(masked_key=masked_key)


msg_history: list[MessageParam] = []
thinking = {"budget": 2048}
kb = key_binding.KeyBindings()


@kb.add("escape", "escape")
def _(event: KeyPressEvent):
    buffer = event.app.current_buffer
    buffer.text = ""
    buffer.cursor_position = 0


# @kb.add("s-tab")
# def _(event: KeyPressEvent):
#     current = os.getenv("ACCEPT_EDITS", "false").lower() == "true"
#     os.environ["ACCEPT_EDITS"] = str(not current).lower()
#     logger.info(f"{DIM}[Accept Edits: {'✓' if not current else '✗'}] {RESET}")


@kb.add("tab")
def _(event: KeyPressEvent):
    current = (os.getenv("ANTHROPIC_THINKING_BUDGET", "false")) == "true"
    os.environ["ANTHROPIC_THINKING_BUDGET"] = str(not current).lower()
    logger.info(f"{DIM}Thinking: {'✓' if not current else '✗'}{RESET}")


styles = styles.Style.from_dict({"": "ansibrightblack"})
session = PromptSession(key_bindings=kb, style=styles)
