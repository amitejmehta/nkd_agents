# nkd_agents: Naked Agents Framework

## Overview

`nkd_agents` is a minimalist Python framework for building AI agents using only the essential components: an LLM, a loop, and tools. The library is built around the philosophy of simplicity, providing a clean, type-safe way to create conversational agents that can execute tools and maintain conversation history.

## Core Architecture

The framework follows a simple but powerful architecture:

**LLM + Loop + Tools = Agent**

1. **LLM**: Handles communication with Anthropic's Claude API
2. **Loop**: Manages the conversation flow and tool execution
3. **Tools**: Async functions that the agent can call to interact with the environment

## Repository Structure

```
nkd_agents/
├── llm.py              # Core LLM wrapper with agentic loop
├── tools.py            # Built-in tool implementations
├── context.py          # Type-safe dependency injection wrapper
├── logging.py          # Logging configuration helper
└── chat/               # Chat w/ Claude Code style agent
    ├── cli.py          # Command-line interface
    └── config.py       # CLI configuration and session setup

Supporting Files:
├── Dockerfile
├── CLAUDE.md            
├── pyproject.toml      
└── tests/
```