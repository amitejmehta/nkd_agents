import asyncio
import logging
from pathlib import Path

from anthropic import AsyncAnthropic, omit
from anthropic.types.beta import BetaMessageParam
from prompt_toolkit import PromptSession, key_binding, styles
from prompt_toolkit.key_binding.key_processor import KeyPressEvent

from . import anthropic
from .anthropic import llm, user
from .logging import DIM, GREEN, RED, RESET, configure_logging
from .tools import bash, edit_file, read_file, subtask
from .utils import load_env

configure_logging()
load_env()
logger = logging.getLogger(__name__)
anthropic.client = AsyncAnthropic()
MODELS = ["claude-haiku-4-5", "claude-sonnet-4-5", "claude-opus-4-5"]
# mutable state
model_idx = 1
model_settings = {"model": MODELS[model_idx], "max_tokens": 20000, "thinking": omit}
fns = [read_file, edit_file, bash, subtask]
msgs: list[BetaMessageParam] = []
q: asyncio.Queue[BetaMessageParam] = asyncio.Queue()
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

    @kb.add("c-j")
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

    @kb.add("escape")
    def interrupt(event: KeyPressEvent) -> None:
        if llm_task and not llm_task.done():
            logger.info(f"{RED}...Interrupted. What now?{RESET}")
            llm_task.cancel()
            event.app.exit()

    @kb.add("escape", "escape")
    def clear_input(event: KeyPressEvent) -> None:
        event.app.current_buffer.reset()

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
            fns = [read_file, edit_file, bash, subtask]
        else:
            fns = [read_file]
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
        "'esc':       interrupt\n"
        "'esc esc':   clear input\n"
        "'ctrl+j':    next model\n"
        "'ctrl+k':    clear history\n"
        "'ctrl+u':    clear inline input\n"
        f"'ctrl+c':    exit{RESET}\n",
    )

    try:
        _ = asyncio.create_task(llm_loop())
        await user_input()

    except (KeyboardInterrupt, EOFError):
        logger.info(f"{DIM}Exiting...{RESET}")
    finally:
        assert anthropic.client
        await anthropic.client.close()


def main() -> None:
    asyncio.run(main_async())
