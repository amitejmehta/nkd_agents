# nkd_agents: Naked Agents Framework

You are a first-principles oriented coding assistant building `nkd_agents`, a no-BS framework for AI agents. The framework strips away unnecessary abstractions to expose what matters: **LLM + Loop + Tools = Agent**. That's it.

## Repository Structure

```
nkd_agents/
├── __init__.py         # Empty (providers imported directly)
├── anthropic.py        # Anthropic/Claude provider with complete agentic loop
├── openai.py           # OpenAI provider with complete agentic loop
├── tools.py            # Built-in tool implementations
├── ctx.py              # Context variable helper
├── logging.py          # Logging configuration helper
├── cli.py              # Command-line interface (Claude Code style agent)
└── utils.py           # Internal utilities

Supporting Files:
├── Dockerfile
├── CLAUDE.md           # This file
├── README.md
├── pyproject.toml
├── examples/           # Runnable examples with real LLM calls
│   ├── anthropic/      # Anthropic/Claude examples
│   └── utils.py        # Shared example utilities
└── tests/              # Unit tests (pytest) for deterministic logic
```

## Examples & Tests

**Examples** (`examples/`) - Runnable demonstrations with real LLM calls:
- `test_tool_ctx.py` - Context variable isolation across tool calls
- `test_tool_ctx_mutation.py` - Mutable context objects modified by tools
- Run: `for f in examples/anthropic/test_*.py; do python3 -m "$(echo "${f%.py}" | tr / .)" & done; wait`


**Tests** (`tests/`) - Unit tests with pytest (no LLM calls):
- `test_sandbox.py` - Sandbox security and path resolution tests
- `test_extract_function_params.py` - Function parameter extraction and JSON schema generation tests
- Run: `pytest tests/ -v --cov=nkd_agents --cov-report=term-missing`