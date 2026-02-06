# nkd-agents

`nkd-agents` is an LLM/Agent framework built upon two tenets:
1. **Strip abstractions** - In implementation, an agent is just LLM + Loop + Tools. The loop: call LLM → if tool calls, execute tools → repeat. If no tool calls, return text.

2. **Elegance through simplicity** - You need far less than you think to build bespoke production-grade AI agents for your use-case.


The best way to get acquainted is to check out our examples! [`examples/anthropic/test_basic.py`](examples/anthropic/test_basic.py) 

## Installation

**Package** (build AI agents programmatically with Anthropic/OpenAI):

```bash
uv pip install nkd-agents  # or: pip install nkd-agents
```

**CLI** (Claude Code-style coding assistant with web search):

via `uv tool` (or `pipx`)
```bash
uv tool install nkd-agents[cli]  # or: pipx install nkd-agents[cli]

# Configure (one-time)
mkdir -p ~/.nkd-agents
echo "NKD_AGENTS_ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY" > ~/.nkd-agents/.env

# Launch
nkd
```

> **Requirements:** Chrome/Chromium for web search. No Chrome? Use Docker instead (see below).

via Docker (sandboxed: can only edit files you mount, restricts system access)
```bash
docker build -t nkd-agents https://github.com/amitejmehta/nkd-agents.git

# Configure (one-time)
mkdir -p ~/.nkd-agents
echo "NKD_AGENTS_ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY" > ~/.nkd-agents/.env

# Add alias to your shell config (~/.bashrc, ~/.zshrc, etc.)
echo "alias nkd-sandbox='docker run -it --env-file ~/.nkd-agents/.env -v \$(pwd):/workspace nkd-agents'" >> ~/.zshrc
source ~/.zshrc  # or: echo to ~/.bashrc and source that

# Launch
nkd-sandbox  # or just: nkd
```

> **Note:** Docker includes web tools (`web_search`, `fetch_url`) using Microsoft's Playwright image (~1.5GB).

## Contributing

```bash
git clone https://github.com/amitejmehta/nkd-agents.git
cd nkd-agents
uv pip install -e '.[dev,cli]'
git checkout -b feat/your-feature
# make changes
pytest
# submit PR
```

Branch names and commits should follow [Conventional Commits](https://www.conventionalcommits.org/).

## License

MIT License
