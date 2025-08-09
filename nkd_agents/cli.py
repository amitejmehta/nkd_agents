import asyncio
import os
import sys
from typing import List

from anthropic.types import TextBlockParam
from jinja2 import Template
from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import HTML

from .agents import AGENT_MAP
from .config import console
from .llm import LLM

session = PromptSession(multiline=False)
PROMPT = HTML("<b><ansiyellow>You:</ansiyellow></b> ")
INTRO_TEMPLATE = """\nWelcome to [bold blue]pyClaude![/bold blue]

model: [magenta]{{ llm._model }}[/magenta]

{% if llm._tool_defs %}
tools:
{% for tool in llm._tool_defs %}
- [cyan bold]{{ tool["name"] }}[/cyan bold]: {{ tool["description"] }}
{% endfor %}
{% endif %}

Type [bold red]'CTRL+C'[/bold red] to end the conversation.
Type [bold yellow]'clear'[/bold yellow] to clear the message history.
Type [bold turquoise]'edit_mode'[/bold turquoise] to toggle edit approval (currently [bold magenta]{{ edit_mode }}[/bold magenta])."""


async def loop(llm: LLM) -> None:
    "Main CLI loop w/ status and user input"
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


async def main(llm: LLM) -> None:
    try:
        edit_mode = os.getenv("EDIT_APPROVAL", "enabled").lower()
        intro = Template(INTRO_TEMPLATE).render(llm=llm, edit_mode=edit_mode)
        console.print(intro)

        await loop(llm)

    except KeyboardInterrupt:
        console.print("\n\n[bold blue]Exiting... Goodbye![/bold blue]")
    except Exception:
        console.print_exception(show_locals=True)


if __name__ == "__main__":
    agent_name = sys.argv[1] if len(sys.argv) > 1 else "code"
    asyncio.run(main(AGENT_MAP[agent_name]()))
