import asyncio
import logging
import os
from pathlib import Path

from anthropic import AsyncAnthropic, omit
from anthropic.types import MessageParam
from prompt_toolkit import PromptSession, key_binding, styles
from prompt_toolkit.key_binding.key_processor import KeyPressEvent
from prompt_toolkit.patch_stdout import patch_stdout

from .anthropic import llm, user
from .ctx import client_ctx
from .logging import DIM, GREEN, RED, RESET, configure_logging
from .tools import bash, edit_file, read_file, subtask
from .utils import load_env
from .web import fetch_url, web_search

logger = logging.getLogger(__name__)

# configuration
MODELS = ["claude-haiku-4-5", "claude-sonnet-4-5", "claude-opus-4-5"]
load_env((Path.home() / ".nkd-agents" / ".env").as_posix())
if not os.environ.get("NKD_AGENTS_ANTHROPIC_API_KEY"):
    raise ValueError(
        "NKD_AGENTS_ANTHROPIC_API_KEY is not set. "
        "See https://github.com/amitejmehta/nkd-agents#installation"
    )
client = AsyncAnthropic(api_key=os.environ["NKD_AGENTS_ANTHROPIC_API_KEY"])
client_ctx.set(client)  # make client available to tools (like subtask)
starting_phrase = "Be brief and exacting."  # prefixed to every user message
fns = [read_file, edit_file, bash, subtask, fetch_url, web_search]

# mutable state
input: list[MessageParam] = []
q: asyncio.Queue[MessageParam] = asyncio.Queue()
llm_task: asyncio.Task | None = None
plan_mode = False
model_idx = 1
model_settings = {"model": MODELS[model_idx], "max_tokens": 20000, "thinking": omit}
if Path("CLAUDE.md").exists():  # fetches file from cwd at runtime
    model_settings["system"] = Path("CLAUDE.md").read_text(encoding="utf-8")


async def llm_loop() -> None:
    """Run agentic loop for each msg in queue. A run is cancelled when the user interrupts."""
    global llm_task
    while True:
        input.append(await q.get())  # q.get hangs here forever until msg added to queue
        llm_task = asyncio.create_task(llm(client, input, fns, **model_settings))
        try:
            await llm_task
        except asyncio.CancelledError:
            pass  # user interrupted, ready for next message


async def user_input() -> None:
    """Configure then launch user chat CLI"""
    kb = key_binding.KeyBindings()

    @kb.add("c-l")
    def switch_model(event: KeyPressEvent) -> None:
        global model_idx
        model_idx = (model_idx + 1) % len(MODELS)
        model_settings["model"] = MODELS[model_idx]
        logger.info(f"{DIM}Switched to {GREEN}{model_settings['model']}{RESET}")

    @kb.add("escape", "escape")
    def interrupt(event: KeyPressEvent) -> None:
        if llm_task and not llm_task.done():
            logger.info(f"{RED}...Interrupted. What now?{RESET}")
            llm_task.cancel()

    @kb.add("tab")
    def toggle_thinking(event: KeyPressEvent) -> None:
        current = model_settings["thinking"] != omit
        model_settings["thinking"] = (
            omit if current else {"type": "enabled", "budget_tokens": 2048}
        )
        logger.info(f"{DIM}Thinking: {'✓' if not current else '✗'}{RESET}")

    @kb.add("s-tab")
    def toggle_plan_mode(event: KeyPressEvent) -> None:
        global plan_mode
        plan_mode = not plan_mode
        logger.info(f"{DIM}Plan mode: {'✓' if plan_mode else '✗'}{RESET}")

    @kb.add("c-k")
    def compact_history(event: KeyPressEvent) -> None:
        """Remove all tool call/result pairs"""
        kept = []
        for x in input:
            assert isinstance(x["content"], list)  # we don't accept str content inputs
            if not any(  # input is TypedDict, output is BaseModel
                (b.get("type") if isinstance(b, dict) else b.type)
                in ("tool_use", "tool_result")
                for b in x["content"]
            ):
                kept.append(x)
        removed = len(input) - len(kept)
        input[:] = kept
        logger.info(f"{DIM}Compacted: removed {removed} messages{RESET}")

    style = styles.Style.from_dict({"": "ansibrightblack"})
    session = PromptSession(key_bindings=kb, style=style)

    while True:
        text: str = await session.prompt_async("> ")
        if text and text.strip():
            prefix = ("PLAN MODE - READ ONLY. " if plan_mode else "") + starting_phrase
            await q.put(user(f"{prefix} {text.strip()}"))


async def main_async() -> None:
    """Launch user input and LLM loops in parallel."""
    with patch_stdout(raw=True):
        configure_logging(int(os.environ.get("LOG_LEVEL", logging.INFO)))
        logger.info(
            f"\n\n{DIM}nkd-agents\n\n"
            "'tab':       toggle thinking\n"
            "'shift+tab': toggle plan mode\n"
            "'esc esc':   interrupt\n"
            "'ctrl+u':    clear input\n"
            "'ctrl+l':    next model\n"
            "'ctrl+k':    compact history\n"
            f"'ctrl+c':    exit{RESET}\n",
        )

        try:
            _ = asyncio.create_task(llm_loop())
            await user_input()

        except (KeyboardInterrupt, EOFError):
            logger.info(f"{DIM}Exiting... ({len(input)} messages){RESET}")


def main() -> None:
    asyncio.run(main_async())
