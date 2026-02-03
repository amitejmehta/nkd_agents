import asyncio
import logging
import os
from pathlib import Path

from anthropic import AsyncAnthropic, omit
from anthropic.types import MessageParam
from prompt_toolkit import PromptSession, key_binding, styles
from prompt_toolkit.key_binding.key_processor import KeyPressEvent

from . import anthropic
from .anthropic import llm, user
from .logging import DIM, GREEN, RED, RESET, configure_logging
from .tools import bash, edit_file, fetch_url, read_file, subtask
from .utils import load_env

configure_logging(int(os.environ.get("LOG_LEVEL", logging.INFO)))
logger = logging.getLogger(__name__)


def ensure_api_key() -> None:
    """Ensure ANTHROPIC_API_KEY is available. Save to config if in environ."""
    config_dir = Path.home() / ".nkd_agents"
    config_file = config_dir / ".env"

    if key := os.environ.get("NKD_AGENTS_ANTHROPIC_API_KEY"):
        config_dir.mkdir(exist_ok=True)
        config_file.write_text(f"NKD_AGENTS_ANTHROPIC_API_KEY={key}\n")
    else:
        load_env(config_file.as_posix())

    if key := os.environ.get("NKD_AGENTS_ANTHROPIC_API_KEY"):
        os.environ["ANTHROPIC_API_KEY"] = key
    else:
        raise ValueError(
            "ANTHROPIC_API_KEY not found.\nSet once via: NKD_AGENTS_ANTHROPIC_API_KEY=sk-... nkd_agents"
        )


ensure_api_key()
anthropic.client.set(AsyncAnthropic())
MODELS = ["claude-haiku-4-5", "claude-sonnet-4-5", "claude-opus-4-5"]
# mutable state
model_idx = 1
model_settings = {"model": MODELS[model_idx], "max_tokens": 20000, "thinking": omit}
fns = [read_file, edit_file, bash, subtask, fetch_url]
msgs: list[MessageParam] = []
q: asyncio.Queue[MessageParam] = asyncio.Queue()
llm_task: asyncio.Task | None = None
starting_phrase = "Be brief and exacting."
if Path("CLAUDE.md").exists():  # fetches file from cwd at runtime
    model_settings["system"] = Path("CLAUDE.md").read_text(encoding="utf-8")


async def llm_loop() -> None:
    """Run agentic loop for each msg in queue. A run is cancelled when the user interrupts."""
    global llm_task
    while True:
        msgs.append(await q.get())  # q.get hangs here forever until msg added to queue
        llm_task = asyncio.create_task(llm(msgs, fns=fns, **model_settings))


async def user_input() -> None:
    """Configure then launch user chat CLI"""
    kb = key_binding.KeyBindings()

    @kb.add("c-l")
    def switch_model(event: KeyPressEvent) -> None:
        global model_idx
        model_idx = (model_idx + 1) % len(MODELS)
        model_settings["model"] = MODELS[model_idx]
        logger.info(f"{DIM}Switched to {GREEN}{model_settings['model']}{RESET}")

    @kb.add("c-k")
    def clear_history(event: KeyPressEvent) -> None:
        length = len(msgs)
        msgs.clear()
        logger.info(f"{DIM}Cleared {length} msgs{RESET}")

    @kb.add("escape", "escape")
    def interrupt(event: KeyPressEvent) -> None:
        if llm_task and not llm_task.done():
            logger.info(f"{RED}...Interrupted. What now?{RESET}")
            llm_task.cancel()
            event.app.exit()

    @kb.add("tab")
    def toggle_thinking(event: KeyPressEvent) -> None:
        current = model_settings["thinking"] != omit
        model_settings["thinking"] = (
            omit if current else {"type": "enabled", "budget_tokens": 2048}
        )
        logger.info(f"{DIM}Thinking: {'✓' if not current else '✗'}{RESET}")

    @kb.add("s-tab")
    def toggle_plan_mode(event: KeyPressEvent) -> None:
        global fns
        plan_mode = edit_file not in fns and bash not in fns
        if plan_mode:
            fns = [read_file, edit_file, bash, subtask, fetch_url]
        else:
            fns = [read_file, fetch_url]
        logger.info(f"{DIM}Plan mode: {'✓' if not plan_mode else '✗'}{RESET}")

    style = styles.Style.from_dict({"": "ansibrightblack"})
    session = PromptSession(key_bindings=kb, style=style)

    while True:
        text: str = await session.prompt_async("> ")
        if text and text.strip():
            await q.put(user(f"{starting_phrase} {text.strip()}"))


async def main_async() -> None:
    """Launch user input and LLM loops in parallel."""
    logger.info(
        f"\n\n{DIM}nkd_agents\n\n"
        "'tab':       toggle thinking\n"
        "'shift+tab': toggle plan mode\n"
        "'esc esc':   interrupt\n"
        "'ctrl+u':    clear input\n"
        "'ctrl+k':    clear history\n"
        "'ctrl+l':    next model\n"
        f"'ctrl+c':    exit{RESET}\n",
    )

    try:
        _ = asyncio.create_task(llm_loop())
        await user_input()

    except (KeyboardInterrupt, EOFError):
        logger.info(f"{DIM}Exiting...{RESET}")


def main() -> None:
    asyncio.run(main_async())
