"""
Test context variable mutation with tools.

Key lesson: Tools can mutate mutable context objects (dataclass with frozen=False).
The tool edits the string in place, and mutations are visible after llm() returns.
"""

import asyncio
from contextvars import ContextVar
from dataclasses import dataclass

from nkd_agents.ctx import ctx
from nkd_agents.llm import llm


@dataclass(frozen=False)
class Document:
    content: str


document = ContextVar[Document | None]("document", default=None)


async def edit_string(old_str: str, new_str: str) -> str:
    """Edit the string in the current document context."""
    doc = document.get()

    if old_str == new_str:
        return "Error: old_str and new_str must be different"
    if old_str not in doc.content:
        return "Error: old_str not found in content"

    doc.content = doc.content.replace(old_str, new_str, 1)
    return f"Success: Replaced '{old_str}' with '{new_str}'"


async def main():
    print("\n" + "=" * 70)
    print("Test: MUTATION - Tool mutates context object")
    print("=" * 70 + "\n")

    doc = Document(content="The quick brown sloth jumps over the lazy dog")
    print(f"   Before: {doc.content}")

    with ctx(document, doc):
        await llm(
            f"Current document: '{doc.content}'\n\nThat animal can't jump! Replace it with 'cat'",
            tools=[edit_string],
            max_tokens=1000,
        )

    print(f"   After:  {doc.content}")

    # Assertion
    expected = "The quick brown cat jumps over the lazy dog"
    assert doc.content == expected
    print("\n   ✓ Mutation persisted correctly!\n")

    print("=" * 70)
    print("✓ Test passed!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
