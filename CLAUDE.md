# nkd_agents: Naked Agents Framework

## Overview

`nkd_agents` is a minimalist Python framework for building AI agents using only the essential components: an LLM, a loop, and tools. The library is built around the philosophy of simplicity, providing a clean, type-safe way to create conversational agents that can execute tools and maintain conversation history.

## Repository Structure

```
nkd_agents/
├── __init__.py          # Package initializer
├── context.py           # Type-safe dependency injection wrapper
├── llm.py              # Core LLM wrapper and main loop logic
├── logging.py           # Logging configuration
├── tools.py            # Built-in file system, bash, and sub-agent tools
├── util.py             # Jinja2 template rendering utilities
└── chat/               # Chat w/ Claude Code style agent
    ├── cli.py          # Command-line interface
    └── config.py       # CLI configuration and session setup

Supporting Files:
├── Dockerfile
├── CLAUDE.md            
├── pyproject.toml      
└── tests/
```

## Core Architecture

The framework follows a simple but powerful architecture:

**LLM + Loop + Tools = Agent**

1. **LLM**: Handles communication with Anthropic's Claude API
2. **Loop**: Manages the conversation flow and tool execution
3. **Tools**: Async functions that the agent can call to interact with the environment