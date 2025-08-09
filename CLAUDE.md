# nkd_agents: Naked Agents Framework

## Overview

`nkd_agents` is a minimalist Python framework for building AI agents using only the essential components: an LLM, a loop, and tools. The library is built around the philosophy of simplicity, providing a clean, type-safe way to create conversational agents that can execute tools and maintain conversation history.

## Repository Structure

```
nkd_agents/
├── __init__.py          # Empty package initializer
├── config.py            # Configuration and logging setup
├── context.py           # Type-safe dependency injection wrapper
├── llm.py              # Core LLM wrapper and main loop logic
├── tools.py            # Built-in file system, bash, and sub-agent tools
├── agents.py           # Pre-configured agent definitions
├── cli.py              # Command-line interface for interactive chat
├── util.py             # Jinja2 template rendering utilities
└── prompts/            # Agent prompt templates
    ├── claude_research.j2  # Research agent system prompt
    └── subagent.j2        # Sub-agent task prompt template

Supporting Files:
├── CLAUDE.md           # System prompt for Claude code agent
├── pyproject.toml      # Project configuration and dependencies
└── tests/
    └── test_llm.py     # Unit tests for core functionality
```

## Core Architecture

The framework follows a simple but powerful architecture:

**LLM + Loop + Tools = Agent**

1. **LLM**: Handles communication with Anthropic's Claude API
2. **Loop**: Manages the conversation flow and tool execution
3. **Tools**: Async functions that the agent can call to interact with the environment