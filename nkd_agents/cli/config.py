from pathlib import Path
from typing import cast

from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.history import FileHistory
from prompt_toolkit.styles import Style
from rich.console import Console

from .completer import CombinedCompleter

INTRO = """[dim]\n\nWelcome to [bold magenta]nkd_agents[/bold magenta]!
\n/help to learn more.[/dim]\n"""
HELP = """
[dim]Available Commands:
- /clear: Clear the message history
- /edit_mode: Toggle edit approval mode
- /help: Show this help message

Tips:
- Use ↑↓ arrow keys to navigate through command history
- Auto-suggestions appear in gray as you type
- Press Tab to complete commands (only at start of line)
- Press Ctrl+C to interrupt long-running operations[/dim]
"""

HISTORY_FILE = Path.home() / ".nkd_agents" / "history.txt"
HISTORY_FILE.parent.mkdir(exist_ok=True)
STATUS = [
    "Thinking...",
    "Pondering...",
    "Contemplating...",
    "Processing...",
    "Analyzing...",
    "Ruminating...",
    "Deliberating...",
    "Computing...",
    "Brain storming...",
    "Cogitating...",
    "Working on it...",
    "Churning away...",
    "Deep in thought...",
    "Neurons firing...",
    "Synapses sparking...",
    "Wheels turning...",
    "Gears grinding...",
    "Magic happening...",
    "Algorithms dancing...",
    "Bits flowing...",
    "Logic loops looping...",
    "Neural networks networking...",
    "Silicon dreams dreaming...",
]


console = Console()
session = PromptSession(
    multiline=False,
    history=FileHistory(str(HISTORY_FILE)),  # enable history via arrow keys
    auto_suggest=AutoSuggestFromHistory(),  # enable auto-suggestions
    completer=CombinedCompleter(),  # enable slash command and @file completion
)
cmds = cast(CombinedCompleter, session.completer).commands
style = Style.from_dict({"": "ansibrightblack"})
