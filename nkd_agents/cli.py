import asyncio
import logging
import os
from pathlib import Path

from anthropic import NOT_GIVEN, omit
from anthropic.types.beta import BetaMessageParam
from prompt_toolkit import PromptSession, key_binding, styles
from prompt_toolkit.key_binding.key_processor import KeyPressEvent

from nkd_agents._utils import load_env
from nkd_agents.llm import llm
from nkd_agents.logging import DIM, RED, RESET, configure_logging
from nkd_agents.tools import edit_file, execute_bash, read_file, subtask

logger = logging.getLogger(__name__)


class ChatSession:
    def __init__(self) -> None:
        self._msgs: list[BetaMessageParam] = []

        self._system = NOT_GIVEN
        if Path("CLAUDE.md").exists():
            self._system = Path("CLAUDE.md").read_text(encoding="utf-8")

        self._q = asyncio.Queue[BetaMessageParam]()
        self._llm_task = None
        self._kb = self._create_key_bindings()
        style = styles.Style.from_dict({"": "ansibrightblack"})
        self._session = PromptSession(key_bindings=self._kb, style=style)

    def _create_key_bindings(self) -> key_binding.KeyBindings:
        kb = key_binding.KeyBindings()

        @kb.add("c-k")
        def _(event: KeyPressEvent) -> None:
            logger.info(f"{DIM}Cleared {len(self._msgs)} msgs{RESET}")
            self._msgs.clear()

        @kb.add("escape")
        def _(event: KeyPressEvent) -> None:
            if self._llm_task and not self._llm_task.done():
                self._llm_task.cancel()
                logger.info(f"{RED}...Interrupted. What now?{RESET}")

        @kb.add("escape", "escape")
        def _(event: KeyPressEvent) -> None:
            buffer = event.app.current_buffer
            buffer.text = ""

        @kb.add("tab")
        def _(event: KeyPressEvent) -> None:
            current = os.getenv("ANTHROPIC_THINKING_BUDGET") == "true"
            os.environ["ANTHROPIC_THINKING_BUDGET"] = str(not current).lower()
            logger.info(f"{DIM}Thinking: {'✓' if not current else '✗'}{RESET}")

        return kb

    async def _llm_loop(self) -> None:
        while True:
            self._msgs.append(await self._q.get())

            settings = {"max_tokens": 20000, "thinking": omit}
            if os.getenv("ANTHROPIC_THINKING_BUDGET") == "true":
                settings["thinking"] = {"type": "enabled", "budget_tokens": 2048}

            tools = [read_file, edit_file, execute_bash, subtask]
            task = asyncio.create_task(
                llm(self._msgs, system=self._system, tools=tools, **settings)
            )
            self._llm_task = task

            try:
                _ = await self._llm_task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error(f"{RED}Error: {e}{RESET}")
            finally:
                self._llm_task = None

    async def run(self) -> None:
        """Chat loop that prompts user for input and puts it in queue."""
        _ = asyncio.create_task(self._llm_loop())

        while True:
            text: str = await self._session.prompt_async("> ")
            if text and text.strip():
                await self._q.put({"role": "user", "content": text.strip()})


async def main_async() -> None:
    load_env()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    masked_key = f"...{api_key[-4:]}" if api_key else f"{RED}Not Set{DIM}"

    configure_logging()
    logger.info(
        f"{DIM}\n\nnkd_agents\n\nAPI Key: {masked_key}\n\n"
        "'tab':     thinking\n"
        "'esc':     interrupt\n"
        "'esc esc': clear input\n"
        "'ctrl+u':  clear line\n"
        "'ctrl+k':  clear history\n"
        f"'ctrl+d':  exit{RESET}\n"
    )

    try:
        await ChatSession().run()
    except (KeyboardInterrupt, EOFError):
        logger.info(f"{DIM}Exiting...{RESET}")


def main() -> None:
    asyncio.run(main_async())
