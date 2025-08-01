from pathlib import Path

from .llm import LLM
from .tools import edit_file, execute_bash, read_file


def claude_code() -> LLM:
    """Create a Claude Code agent."""
    system_prompt = Path("CLAUDE.md").read_text()
    tools = [read_file, edit_file, execute_bash]
    return LLM(system_prompt=system_prompt, tools=tools)


AGENT_MAP = {"code": claude_code}
