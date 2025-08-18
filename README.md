# nkd_agents: Naked Agents Framework

A minimalist Python framework for building AI agents using only the essential components: an LLM, a loop, and tools.

## Architecture

**LLM + Loop + Tools = Agent**

The framework follows a simple but powerful architecture:

1. **LLM**: Handles communication with Anthropic's Claude API
2. **Loop**: Manages the conversation flow and tool execution  
3. **Tools**: Async functions that the agent can call to interact with the environment

## Installation

```bash
pip install -e .
```

## Usage

### Interactive Mode

Start the interactive code agent:

```bash
# Using the console script
nkd_agents

# Or using the module
python -m nkd_agents

# Explicitly specify the code agent
nkd_agents code
```

### Sandbox Mode

Run the agent in a secure, containerized sandbox environment:

```bash
nkd_agents sandbox
```

The sandbox mode:

- Uses Docker to create an isolated container environment
- Mounts your current working directory at `/workspace` in the container
- Automatically builds the Docker image if it doesn't exist
- Passes through your `ANTHROPIC_API_KEY` environment variable
- Provides the same interactive experience in a secure environment

#### Sandbox Requirements

- [Docker](https://docs.docker.com/get-docker/) must be installed and running
- Your `ANTHROPIC_API_KEY` environment variable must be set

#### User Experience

1. **Install the package:**
   ```bash
   pip install -e .
   ```

2. **Set your API key:**
   ```bash
   export ANTHROPIC_API_KEY=your_api_key_here
   ```

3. **Run in sandbox:**
   ```bash
   cd /path/to/your/project
   nkd_agents sandbox
   ```

The first time you run `nkd_agents`, it will automatically build the Docker image. Subsequent runs will be much faster.

#### Why Sandbox?

The sandbox mode is perfect when you want to:

- Let the agent work with files and run commands without affecting your host system
- Test potentially dangerous operations safely
- Work on projects where you want an isolated environment
- Demonstrate the agent's capabilities without security concerns

## Configuration

Set your Anthropic API key:

```bash
export ANTHROPIC_API_KEY=your_api_key_here
```

## Available Commands

In the interactive session, you can use:

- `/clear` - Clear message history
- `/edit_mode` - Toggle edit approval mode
- `/help` - Show help
- `!<command>` - Execute bash commands

## Architecture Overview

```
nkd_agents/
├── __init__.py          # Package initializer
├── __main__.py          # CLI entry point
├── config.py            # Configuration and logging setup
├── context.py           # Type-safe dependency injection wrapper
├── llm.py              # Core LLM wrapper and main loop logic
├── tools.py            # Built-in file system, bash, and sub-agent tools
├── agents.py           # Pre-configured agent definitions
├── cli.py              # Command-line interface for interactive chat
├── util.py             # Jinja2 template rendering utilities
└── prompts/            # Agent prompt templates
```

## Development

Install development dependencies:

```bash
pip install -e .[dev]
```

Run tests:

```bash
pytest
```

## License

MIT License