import asyncio
import logging
import os
import random
import subprocess
from typing import List

from anthropic.types import TextBlockParam, ToolResultBlockParam, ToolUseBlock

from nkd_agents.llm import LLM
from nkd_agents.logging import setup_logging
from nkd_agents.tools import edit_file, execute_bash, read_file, spawn_subagent

from .config import HELP, INTRO, STATUS, cmds, console, session, style

setup_logging()

logger = logging.getLogger(__name__)


async def user_input(llm: LLM) -> List[TextBlockParam]:
    """Enhanced user input with command handling and history support"""
    while True:
        x = (await session.prompt_async("> ", style=style)).strip().lower()

        if x not in cmds and not x.startswith("!") and not x.startswith("! "):
            return [{"text": x, "type": "text"}]

        if x.startswith("!"):
            cmd = ["bash", "-c", x.replace("!", "! ")]
            subprocess.run(cmd, timeout=10, env=os.environ)
        if x == "/clear":
            llm.messages.clear()
            logger.info("[dim]\nMessage history cleared.\n[/dim]")
        elif x == "/edit_mode":
            current_setting = os.getenv("EDIT_APPROVAL", "enabled").lower()
            new_setting = "disabled" if current_setting == "enabled" else "enabled"
            os.environ["EDIT_APPROVAL"] = new_setting
            logger.info(f"[dim]Edit approval {new_setting}.[/dim]")
        elif x == "/help":
            logger.info(HELP)


async def execute_tool(llm: LLM, tc: ToolUseBlock) -> ToolResultBlockParam:
    try:
        return await llm.execute_tool(tc)
    except (KeyboardInterrupt, asyncio.CancelledError):
        text = "Tool execution cancelled by user."
        block = ToolResultBlockParam(
            content=[TextBlockParam(text=text, type="text")],
            type="tool_result",
            tool_use_id=tc.id,
        )
        llm.messages.append({"role": "user", "content": [block]})
        raise


async def loop(llm: LLM) -> None:
    """Main CLI loop with enhanced status and user input"""
    msg = await user_input(llm)
    while True:
        try:
            with console.status(random.choice(STATUS)):
                output, tool_calls = await llm(msg)
            logger.info(f"\n○: {output}\n")
            if tool_calls:
                msg = await asyncio.gather(
                    *[execute_tool(llm, tc) for tc in tool_calls]
                )
                continue
        except (KeyboardInterrupt, asyncio.CancelledError):
            logger.info("\n[dim]Interrupted. What would you like me to do?[/dim]")
        msg = await user_input(llm)


async def chat(llm: LLM) -> None:
    """Main entry point with enhanced error handling"""
    try:
        logger.info(INTRO)
        await loop(llm)
    except (KeyboardInterrupt, EOFError):
        logger.info("\n\n[bold blue]Exiting... Goodbye![/bold blue]")
    except Exception:
        logger.exception("Exception in chat function")


if __name__ == "__main__":
    asyncio.run(chat(LLM(tools=[read_file, edit_file, execute_bash, spawn_subagent])))
