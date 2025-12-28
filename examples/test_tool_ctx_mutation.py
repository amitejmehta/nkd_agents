"""
Test context variable mutation with tools.

Key lesson: Tools can mutate mutable context objects (dataclass with frozen=False).
The tool edits the string in place, and mutations are visible after llm() returns.
"""

import logging
from contextvars import ContextVar
from dataclasses import dataclass

from _utils import test_runner

from nkd_agents.ctx import ctx
from nkd_agents.llm import llm

logger = logging.getLogger(__name__)


@dataclass(frozen=False)
class Document:
    content: str


document = ContextVar[Document | None]("document", default=None)


async def edit_string(old_str: str, new_str: str) -> str:
    """Edit the string in the current document context."""
    doc = document.get()
    assert doc is not None

    if old_str == new_str:
        return "Error: old_str and new_str must be different"
    if old_str not in doc.content:
        return "Error: old_str not found in content"

    doc.content = doc.content.replace(old_str, new_str, 1)
    return f"Success: Replaced '{old_str}' with '{new_str}'"


@test_runner("tool_ctx_mutation")
async def main():
    doc = Document(content="The quick brown sloth jumps over the lazy dog")
    logger.info(f"Before: {doc.content}")

    with ctx(document, doc):
        prompt = f"Current document: '{doc.content}'\n\nThat animal can't jump! Replace it with 'cat'"
        await llm(prompt, tools=[edit_string], max_tokens=1000)

    logger.info(f"After: {doc.content}")

    expected = "The quick brown cat jumps over the lazy dog"
    assert doc.content == expected


if __name__ == "__main__":
    main()
