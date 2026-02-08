# nkd-agents

`nkd-agents` is two things: a minimal async LLM agent framework and a Claude Code-style coding CLI. The framework wraps the Anthropic and OpenAI APIs with as little abstraction as possible. The CLI is a terminal-based coding assistant built on top of the Anthropic provider, using Claude models exclusively.

## The Framework

An agent is an LLM in a loop with tools. The loop calls the LLM; if the response contains tool calls, it executes them, feeds the results back, and repeats. When the response contains no tool calls, it returns the text. This is the entire control flow—there is nothing else.

Each provider module (`nkd_agents.anthropic`, `nkd_agents.openai`) exposes a single `llm()` function with three positional concerns: a client, the conversation history (a mutable list of messages), and an optional sequence of tool functions (`fns`). All other parameters—`model`, `max_tokens`, `system`, `temperature`—pass through as `**kwargs` directly to the underlying SDK. There are no wrapper-specific parameters and no configuration objects.

```python
from anthropic import AsyncAnthropic
from nkd_agents.anthropic import llm, user

response = await llm(
    AsyncAnthropic(),
    [user("What's the weather in Paris?")],
    fns=[get_weather],
    model="claude-sonnet-4-5", max_tokens=1024
)
```

One convenience is provided by default: automatic generation of JSON tool schemas from function signatures and docstrings. Maintaining these schemas by hand is tedious and error-prone; automating it lets you focus on tool design rather than schema bookkeeping. This default can be overridden however—pass your own schemas via the `tools` kwarg and they will be used as-is. This is the reason for the naming distinction: `fns` refers to the callable Python functions, while `tools` refers to the JSON schemas, and `tools` lives in `**kwargs` because it is passed directly to the API.

Because the framework is async, tools that need shared state—a client instance, a working directory, user-defined configuration—receive it via Python's `contextvars.ContextVar` rather than special framework parameters or wrapper objects. Context vars are inherited by async tasks spawned via `asyncio.gather()`, so tools executed in parallel within the agent loop automatically see the correct values. Set a context var before calling `llm()`, and every tool invocation within that call has access to it—no framework-specific context manipulation required. See [`examples/anthropic/test_tool_ctx.py`](examples/anthropic/test_tool_ctx.py) for a working example.

Everything else in the framework is module-level helper functions: formatting tool results into the provider's expected message structure, converting a string into a user message, constructing an output config for structured (Pydantic) responses. No classes wrap the providers. No base classes. No middleware.

## The CLI

The CLI is a terminal-based coding assistant with the following controls:

| Key | Action |
|---|---|
| `tab` | Toggle extended thinking |
| `shift+tab` | Toggle plan mode |
| `ctrl+l` | Cycle model (haiku → sonnet → opus → haiku) |
| `ctrl+k` | Compact history (strip tool call/result messages) |
| `esc esc` | Interrupt current LLM call |
| `ctrl+u` | Clear input line |
| `ctrl+c` | Exit |

The CLI understands images and PDFs natively via `read_file`.

### Dynamic Control

Two interaction properties underpin everything else:
1. **Interruption**: `esc esc` cancels the active LLM call immediately. Interruptions are handled gracefully during both API calls and tool execution—when a tool call is interrupted, the string "Interrupted" is returned as its tool result, preventing message history corruption (both the Anthropic and OpenAI APIs require every tool call to be followed by a tool result).
2. **Message queuing**: messages can be submitted while the LLM is still responding; they enqueue and execute in sequence. 

These two, combined with the keyboard shortcuts for model switching, thinking, and plan mode, enable fast and dynamic control. For example: Sonnet starts heading in the wrong direction—`esc esc` to interrupt, `ctrl+l` to Opus, type a correction and send. While Opus is working, toggle thinking on and queue a harder follow-up that benefits from extended reasoning. All sub-second.

### Context-Efficient Web Search

The CLI includes a free `web_search` tool (DuckDuckGo via headless Chrome) and a `fetch_url` tool designed for maximum context efficiency. Rather than injecting webpage content into the conversation, `fetch_url` converts a page to clean markdown, saves it to a file, and returns only the file path and character count. The full content never enters the context window—the model explores long responses via `bash` (grep, head, tail), reading only what it needs. Since the model filters out false positives at read time, the scraping step can favor recall over precision—ensuring more salient information from complex JavaScript-heavy pages, for example.

This also makes the CLI exceptionally well-suited for deep research. Give it a well-written research prompt and it will search, fetch, and persist a local library of markdown files on disk—source material it can then cross-reference, explore, and synthesize across multiple documents, all without exhausting its context window.

### Start Phrases

The most distinctive design element in the CLI. Every user message is automatically prepended with a fixed phrase before it is sent to the model. This feature emerged from a cost optimization journey.

A goal of the CLI was to reduce cost and improve efficiency. The first axis explored was model selection: route cheap tasks to lighter models, expensive tasks to heavier ones. A classifier-based router was rejected—a single utterance in an ongoing conversation lacks sufficient context for classification, and passing the full history to a classifier on every turn is expensive, defeating the purpose. A `switch_model` tool, letting the LLM self-route, proved brittle—without extensive escalation guidance, accuracy was effectively random, and Haiku was not capable enough to decide when to escalate itself. Without starting on Haiku, the cost savings disappeared. The simplest answer was a keyboard shortcut (`ctrl+l`), which worked. (*Update, Feb 28 2026:* Given the Opus 4.6 release and its *relatively* small cost premium over Sonnet, might consider experimenting adding a  `switch_model` tool scoped to just Sonnet and Opus).

The second axis was output verbosity—the real cost driver. Claude is verbose not in its reasoning, but in its output: the tokens spent presenting an answer it has already arrived at. System prompting for brevity worked initially but degraded as conversations grew; after several turns of tool calls and file reads, the system prompt became a vanishing fraction of total context. This also appears to conflict with how models have been trained generally—there has never been a focus on brevity and information density in responses. Chain-of-thought made this worse, since reasoning and output were conflated in the same token stream; more tokens meant better answers *and* longer responses, with no way to separate the two.

The solution: prepend **"Be brief and exacting."** to every user message. Because the phrase appears at the start of each turn, it maintains consistent influence regardless of context length—not once at the top of a context that may now span tens of thousands of tokens, but immediately before every request. This works reliably across Haiku, Sonnet, and Opus.

Constraining output length might appear to conflict with the prevailing trend of increasing inference-time compute. It does not. The key distinction is between tokens spent on *reasoning*—arriving at the answer—and tokens spent on *output*—presenting it. Reasoning models make this distinction explicit: reasoning now lives in a dedicated thinking trace, separate from the response, and can be toggled on independently. More reasoning tokens improve quality. More output tokens, after the answer has been reached, are waste. Start phrases constrain only the latter. Toggle thinking on and the model gets extended reasoning traces while the responses remain terse and information-dense.

Start phrases also solved plan mode. When toggled, messages are prepended with **"PLAN MODE - READ ONLY."** The obvious implementation would be to restrict tools. Removing `edit_file` is straightforward, but `bash` can also write files, so it would need to be removed too—or heavily restricted with command-level filtering. Removing `bash` entirely cripples codebase exploration (searching, listing files, running tests), and fine-grained bash restrictions add complexity for uncertain reliability. Start phrases sidestepped all of this. The model retains full tool access but respects the read-only instruction.

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
