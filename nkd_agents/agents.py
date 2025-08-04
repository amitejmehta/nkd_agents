from pathlib import Path

from .config import settings
from .llm import LLM
from .tools import edit_file, execute_bash, read_file, spawn_subagent


def claude_code() -> LLM:
    """Create a Claude Code agent."""
    system_prompt = Path("CLAUDE.md").read_text()
    tools = [read_file, edit_file, execute_bash]
    return LLM(system_prompt=system_prompt, tools=tools)


def claude_research() -> LLM:
    """Create a Claude Research agent with sub-agent spawning capabilities."""
    system_prompt = Path(settings.prompt_dir, "claude_research.j2").read_text()
    tools = [read_file, edit_file, execute_bash, spawn_subagent]
    return LLM(system_prompt=system_prompt, tools=tools)


AGENT_MAP = {"code": claude_code, "research": claude_research}
