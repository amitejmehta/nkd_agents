import asyncio
import os
import random
import re
from pathlib import Path
from typing import List

from anthropic.types import TextBlockParam, ToolResultBlockParam, ToolUseBlock

from .agents import pyclaude
from .cli_config import HELP_MESSAGE, INTRO_MESSAGE, STATUS_MESSAGES, console, session
from .llm import LLM


async def user_input(llm: LLM) -> List[TextBlockParam]:
    """Enhanced user input with command handling and history support"""
    while True:
        x = (await session.prompt_async("> ")).strip().lower()

        if x not in session.completer.commands:
            return [{"text": x, "type": "text"}]

        if x == "/clear":
            llm.messages.clear()
            console.print("[dim]\nMessage history cleared.\n[/dim]")
        elif x == "/edit_mode":
            current_setting = os.getenv("EDIT_APPROVAL", "enabled").lower()
            new_setting = "disabled" if current_setting == "enabled" else "enabled"
            os.environ["EDIT_APPROVAL"] = new_setting
            console.print(f"[dim]Edit approval {new_setting}.[/dim]")
        elif x == "/help":
            console.print(HELP_MESSAGE)


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
            with console.status(random.choice(STATUS_MESSAGES)):
                output, tool_calls = await llm(msg)
            console.print(f"\n[blue bold]Agent:[/blue bold] {output}\n")
            if tool_calls:
                console.print(f"\n[cyan bold]Tool calls:[/cyan bold] {tool_calls}\n")
                msg = await asyncio.gather(
                    *[execute_tool(llm, tc) for tc in tool_calls]
                )
                continue
        except (KeyboardInterrupt, asyncio.CancelledError):
            console.print("\n[dim]Interrupted. What would you like me to do?[/dim]")
        msg = await user_input(llm)


async def main(llm: LLM) -> None:
    """Main entry point with enhanced error handling"""
    try:
        console.print(INTRO_MESSAGE)
        await loop(llm)
    except (KeyboardInterrupt, EOFError):
        console.print("\n\n[bold blue]Exiting... Goodbye![/bold blue]")
    except Exception:
        console.print_exception(show_locals=True)


if __name__ == "__main__":
    asyncio.run(main(pyclaude()))
