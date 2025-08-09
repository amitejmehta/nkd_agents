import asyncio
import os
import sys
from typing import List

import pyfiglet
from anthropic.types import TextBlockParam
from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import HTML

from .agents import AGENT_MAP
from .config import console
from .llm import LLM

# NOTE: multiline=False is important (https://github.com/prompt-toolkit/python-prompt-toolkit/issues/1894
session = PromptSession(multiline=False)
PROMPT = HTML("<b><ansiyellow>You:</ansiyellow></b> ")


async def loop(llm: LLM) -> None:
    msg = await user_input(llm)
    while True:
        with console.status("Thinking..."):
            output, tool_calls = await llm(msg)
        console.print(f"\n[blue bold]Agent:[/blue bold] {output}\n")
        if tool_calls:
            console.print(f"\n[cyan bold]Tool calls:[/cyan bold] {tool_calls}\n")
            msg = await asyncio.gather(*[llm.execute_tool(tc) for tc in tool_calls])
        else:
            msg = await user_input(llm)


async def user_input(llm: LLM) -> List[TextBlockParam]:
    """Continuously prompt, handling exit/clear/empty, and yield messages."""
    while True:
        x = (await session.prompt_async(PROMPT)).strip().lower()

        if x == "clear":
            llm.messages.clear()
            console.print("[dim]Message history cleared.[/dim]")
            continue
        elif x == "edit_mode":
            current_setting = os.getenv("EDIT_APPROVAL", "enabled").lower()
            new_setting = "disabled" if current_setting == "enabled" else "enabled"
            os.environ["EDIT_APPROVAL"] = new_setting
            console.print(f"[dim]Edit approval {new_setting}.[/dim]")
            continue
        if not x:
            continue

        return [{"text": x, "type": "text"}]


async def main(llm: LLM, agent_name: str) -> None:
    try:
        intro = (
            f"\n{pyfiglet.figlet_format(f'{agent_name.replace('_', ' ').title()}', font='slant')}"
            f"model: [magenta]{llm._model}[/magenta]\n\n"
            f"tools:\n{'\n\n'.join(f'- [cyan bold]{fn.__name__}[/cyan bold]: {fn.__doc__}' for fn in llm._tool_dict.values())}\n"
            "\n\nType [bold red]'CTRL+C'[/bold red] to end the conversation.\n"
            "Type [bold yellow]'clear'[/bold yellow] to clear the message history.\n"
            f"Type [bold yellow]'edit_mode'[/bold yellow] to toggle edit approval (currently [bold magenta]{os.getenv('EDIT_APPROVAL', 'enabled').lower()}[/bold magenta]).\n\n"
        )

        console.print(intro)
        await loop(llm)
    except KeyboardInterrupt:
        console.print("\n\n[bold blue]Exiting... Goodbye![/bold blue]")
    except Exception:
        console.print_exception(show_locals=True)


if __name__ == "__main__":
    agent_name = sys.argv[1] if len(sys.argv) > 1 else "claude_code"
    asyncio.run(main(AGENT_MAP[agent_name](), agent_name))
