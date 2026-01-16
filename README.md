# nkd_agents

`nkd_agents` is an LLM/Agent framework built upon two tenets:
1. **Strip abstractions** - In implementation, an agent is just LLM + Loop + Tools. The loop: call LLM → if tool calls, execute → repeat. Stop when LLM returns text.

2. **Elegance through simplicity** - You need far less than you think to build bespoke production-grade AI agents for your use-case.


The best way to get acquainted is to check out our examples! [`examples/anthropic/test_basic.py`](examples/anthropic/test_basic.py) 

## Installation

```bash
uv pip install -U nkd_agents
```

For CLI support (interactive chat), install with the `cli` extra:
```bash
uv pip install -U nkd_agents[cli]
```

## Chat

Chat with your own Claude Code style agent! Uses the `llm` function with `read_file`, `edit_file`, `execute_bash`, and `subtask` (sub-agent) tools.

```bash
export ANTHROPIC_API_KEY=your_api_key_here
nkd_agents
```
Alternatively, set `ANTHROPIC_API_KEY` in a `.env` file in your `cwd` (will automatically be loaded).

### Docker Sandbox

To run in an isolated Docker container:

```bash
docker build -t nkd_agents https://github.com/amitejmehta/nkd_agents.git
docker run -it -e ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY nkd_agents
```

Run with volume mount:
```bash
docker run -it -e ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY -v $(pwd):/workspace nkd_agents
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