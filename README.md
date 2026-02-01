# nkd_agents

`nkd_agents` is an LLM/Agent framework built upon two tenets:
1. **Strip abstractions** - In implementation, an agent is just LLM + Loop + Tools. The loop: call LLM → if tool calls, execute tools → repeat. If no tool calls, return text.

2. **Elegance through simplicity** - You need far less than you think to build bespoke production-grade AI agents for your use-case.


The best way to get acquainted is to check out our examples! [`examples/anthropic/test_basic.py`](examples/anthropic/test_basic.py) 

## Installation

**Package** (build AI agents programmatically with Anthropic/OpenAI):

```bash
uv pip install nkd_agents  # or: pip install nkd_agents
```

**CLI** (Claude Code-style coding assistant in Python - chat with an AI that can read/edit files and run bash):

via `uv tool` (or `pipx`)
```bash
uv tool install nkd_agents[cli]  # or: pipx install nkd_agents[cli]
# Makes `nkd_agents` CLI command globally available. Package not in venvs; venv installs of package will take precedence.

# Configure and launch (saves key to ~/.nkd_agents/.env)
NKD_AGENTS_ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY nkd_agents

# Subsequent launches
nkd_agents
```

via Docker (sandboxed: can only edit files you mount, restricts system access)
```bash
docker build -t nkd_agents https://github.com/amitejmehta/nkd_agents.git

# Configure and launch: creates and mounts ~/.nkd_agents (along with cwd)
docker run -it -e NKD_AGENTS_ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY -v ~/.nkd_agents:/home/agent/.nkd_agents -v $(pwd):/workspace nkd_agents

# Subsequent launches
docker run -it -v ~/.nkd_agents:/home/agent/.nkd_agents -v $(pwd):/workspace nkd_agents
```

## Contributing

```bash
git clone https://github.com/amitejmehta/nkd_agents.git
cd nkd_agents
uv pip install -e '.[dev,cli]'
git checkout -b feat/your-feature
# make changes
pytest
# submit PR
```

Branch names and commits should follow [Conventional Commits](https://www.conventionalcommits.org/).

## License

MIT License