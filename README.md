# nkd_agents

A minimalist Python framework for building AI agents using only the essential components: an `LLM`, a `loop`, and tools.

## Installation

```bash
uv pip install -U nkd_agents
```

## Chat

Chat with your own Claude Code style agent! Simply a `LLM` object with `read_file`, `edit_file`, `execute_bash`, and `task` (sub-agent) tools.

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

## Examples

Coming soon!

## Contributing

```bash
git clone https://github.com/amitejmehta/nkd_agents.git
cd nkd_agents
uv pip install -e '.[dev]'
git checkout -b feat/your-feature
# make changes
pytest
# submit PR
```

Branch names and commits should follow [Conventional Commits](https://www.conventionalcommits.org/).

## License

MIT License