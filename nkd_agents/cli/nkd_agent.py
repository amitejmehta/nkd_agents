from pathlib import Path

from ..llm import LLM
from ..tools import edit_file, execute_bash, read_file, spawn_subagent


def nkd_agent() -> LLM:
    """Create the naked Claude Code style agent."""
    system_prompt = Path("CLAUDE.md").read_text()
    tools = [read_file, edit_file, execute_bash, spawn_subagent]
    return LLM(system_prompt=system_prompt, tools=tools)
