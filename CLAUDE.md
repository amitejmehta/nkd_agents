# nkd_agents: Naked Agents Framework

## Roadmap

### 🔧 Chore
- [ ] **Pyright Fixes**: Resolve all type checking issues and improve type annotations
  - [ ] Fix missing type annotations in `config.py` and `context.py`
  - [ ] Add proper return type annotations for all async functions
  - [ ] Resolve `NOT_GIVEN` type issues in `llm.py`
  - [ ] Add comprehensive type checking for tool schema generation
- [ ] **Unit Testing Expansion**: Achieve comprehensive test coverage
  - [ ] Add tests for `LLM` class methods (`__call__`, `execute_tool`)
  - [ ] Add tests for `loop` function with various input scenarios
  - [ ] Add tests for tool execution with context injection
  - [ ] Add integration tests for agent creation and basic workflows
  - [ ] Add tests for CLI functionality and user input handling
  - [ ] Set up test coverage reporting and CI/CD pipeline
- [ ] **Documentation**: Improve inline documentation and examples
  - [ ] Add comprehensive docstrings to all public methods
  - [ ] Create API reference documentation
  - [ ] Add more usage examples and tutorials

### 🐛 Fix
- [ ] **Error Handling**: Improve robustness and error recovery
  - [ ] Better handling of API rate limits and network failures
  - [ ] Graceful degradation when tools fail to execute
  - [ ] Improved error messages for common user mistakes
- [ ] **Tool Safety**: Enhance security for file and bash operations
  - [ ] Implement proper path traversal protection
  - [ ] Add file size limits for read operations
  - [ ] Improve bash command validation and sanitization

### ✨ Features

#### 🔬 Deep Research Agents
- [ ] **Task Management System**: Todo-driven agent workflows
  - [ ] **Todo.md Integration**: Agents can read, update, and manage markdown todo lists
    - [ ] Parse markdown checkboxes and task hierarchies
    - [ ] Update task status programmatically
    - [ ] Add task metadata (priority, estimates, dependencies)
  - [ ] **Progress Tracking**: Visual progress indicators and status reporting
    - [ ] Task completion percentage tracking
    - [ ] Time estimation and actual time tracking
    - [ ] Milestone and checkpoint management
  - [ ] **Research Planning**: Intelligent task breakdown and planning
    - [ ] Automatic decomposition of complex research questions
    - [ ] Dependency detection between research tasks
    - [ ] Priority-based task ordering

- [ ] **Sub-Agent Architecture**: Hierarchical agent delegation
  - [ ] **Agent Spawning**: Parent agents can create specialized child agents
    - [ ] Define sub-agent specializations and capabilities
    - [ ] Pass context and constraints to child agents
    - [ ] Lifecycle management (create, monitor, terminate)
  - [ ] **Task Delegation**: Intelligent work distribution
    - [ ] Automatic task routing based on agent capabilities
    - [ ] Load balancing across available sub-agents
    - [ ] Task queue management and prioritization
  - [ ] **Result Aggregation**: Combine outputs from multiple sub-agents
    - [ ] Merge research findings and eliminate duplicates
    - [ ] Resolve conflicts between sub-agent conclusions
    - [ ] Generate comprehensive final reports

- [ ] **Research Workflows**: Specialized patterns for deep investigation
  - [ ] **Literature Review**: Systematic research paper analysis
  - [ ] **Comparative Analysis**: Multi-option evaluation frameworks
  - [ ] **Hypothesis Testing**: Structured investigation workflows

#### 👥 Multi-Agent Collaboration
- [ ] **Agent Role System**: Specialized agent personas and capabilities
  - [ ] **Role Definitions**: Pre-configured agent archetypes
    - [ ] Software Engineer (coding, architecture, implementation)
    - [ ] DevOps Engineer (deployment, infrastructure, monitoring)
    - [ ] Product Manager (requirements, prioritization, stakeholder communication)
    - [ ] QA/Testing Engineer (test planning, execution, quality assurance)
    - [ ] Security Engineer (vulnerability assessment, compliance)
  - [ ] **Role-Specific Tools**: Curated toolsets for each specialization
  - [ ] **Dynamic Role Assignment**: Agents can adapt roles based on task requirements

- [ ] **Communication Primitives**: Inter-agent coordination mechanisms
  - [ ] **Message Passing**: Structured communication between agents
    - [ ] Async message queues for agent-to-agent communication
    - [ ] Message routing and delivery guarantees
    - [ ] Support for broadcast, multicast, and direct messaging
  - [ ] **Shared Context**: Collaborative workspace management
    - [ ] Shared memory/state that multiple agents can read/write
    - [ ] Version control for shared artifacts
    - [ ] Conflict resolution for concurrent modifications
  - [ ] **Event System**: Reactive coordination patterns
    - [ ] Event-driven triggers for agent activation
    - [ ] Subscription patterns for relevant events
    - [ ] Workflow orchestration via event chains

- [ ] **Collaboration Patterns**: High-level coordination strategies
  - [ ] **Pipeline**: Sequential handoffs between specialized agents
  - [ ] **Committee**: Parallel analysis with consensus building
  - [ ] **Hierarchy**: Manager-worker delegation patterns
  - [ ] **Swarm**: Distributed problem-solving with emergence
  - [ ] **Peer Review**: Cross-validation and quality assurance workflows

- [ ] **Workflow Orchestration**: Managing complex multi-agent processes
  - [ ] **Workflow Definition**: Declarative workflow specification (YAML/JSON)
  - [ ] **State Management**: Track progress across multiple agents and tasks
  - [ ] **Error Recovery**: Handle failures and retry strategies in multi-agent workflows
  - [ ] **Resource Management**: Prevent resource conflicts and ensure fair usage

#### 🔒 Security & Sandboxing
- [ ] **Execution Sandboxing**: Isolated environments for safe agent operation
  - [ ] **Container Integration**: Docker-based agent isolation
    - [ ] Pre-built container images for different agent types
    - [ ] Resource limits (CPU, memory, disk, network)
    - [ ] File system isolation and volume mounting
  - [ ] **Virtual Environment**: Python-level isolation for tool execution
  - [ ] **Network Restrictions**: Control agent internet access and API usage
  - [ ] **Filesystem Boundaries**: Restrict file access to designated directories

- [ ] **Permission System**: Fine-grained access control
  - [ ] **Tool Permissions**: Per-agent tool access configuration
  - [ ] **Resource Quotas**: Limits on API calls, file operations, compute usage
  - [ ] **Approval Workflows**: Human-in-the-loop for sensitive operations
  - [ ] **Audit Logging**: Complete activity logs for security review

- [ ] **Secret Management**: Secure handling of API keys and credentials
  - [ ] **Environment-based**: Secure injection of secrets into sandboxed environments
  - [ ] **Rotation Support**: Automatic credential rotation and refresh
  - [ ] **Least Privilege**: Minimal required permissions for each agent role

#### 🎯 Enhanced Core Features
- [ ] **Advanced Tool System**: More sophisticated tool capabilities
  - [ ] **Tool Composition**: Chain tools together for complex operations
  - [ ] **Tool Discovery**: Dynamic tool loading and capability detection
  - [ ] **Tool Versioning**: Support multiple versions of tools with compatibility
  - [ ] **Custom Tool SDK**: Framework for building domain-specific tools

- [ ] **Memory & Persistence**: Long-term agent memory and state
  - [ ] **Conversation Persistence**: Save and restore conversation history
  - [ ] **Knowledge Base**: Persistent storage for learned information
  - [ ] **Experience Learning**: Agents improve performance over time
  - [ ] **Context Windows**: Intelligent context management for long conversations

- [ ] **Observability**: Monitoring and debugging capabilities
  - [ ] **Metrics Collection**: Performance and usage analytics
  - [ ] **Distributed Tracing**: Track requests across multi-agent workflows
  - [ ] **Debug Mode**: Detailed logging and step-by-step execution
  - [ ] **Performance Profiling**: Identify bottlenecks and optimization opportunities

---

## Overview

`nkd_agents` is a minimalist Python framework for building AI agents using only the essential components: an LLM, a loop, and tools. The library is built around the philosophy of simplicity, providing a clean, type-safe way to create conversational agents that can execute tools and maintain conversation history.

## Repository Structure

```
nkd_agents/
├── __init__.py          # Empty package initializer
├── config.py            # Configuration, logging, and settings
├── context.py           # Type-safe dependency injection wrapper
├── llm.py              # Core LLM wrapper and main loop logic
├── tools.py            # Built-in file system and bash tools
├── agents.py           # Pre-configured agent definitions
└── cli.py              # Command-line interface for interactive chat

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

## Detailed Component Analysis

### 1. config.py - Configuration and Logging

**Purpose**: Provides centralized configuration management and rich console logging.

**Key Components**:

- `RichLogger`: A custom logger that extends Rich Console for beautiful terminal output
  - Supports different log levels with color coding (debug, info, warning, error, critical)
  - Provides a clean interface for structured logging output

- `AgentSettings`: Pydantic-based settings class that handles environment configuration
  - `runtime_env`: Property that determines the execution environment (default: "local")
  - `get_logger()`: Factory method that returns appropriate logger based on environment

**Usage Pattern**:
```python
from nkd_agents.config import logger
logger.info("This will be displayed in blue")
logger.error("This will be displayed in red")
```

### 2. context.py - Dependency Injection

**Purpose**: Provides type-safe dependency injection for tools that need external context.

**Key Components**:

- `ContextWrapper[T]`: Generic wrapper class for dependency injection
  - Uses Python generics for type safety
  - Allows tools to access shared state or dependencies
  - Implements the dependency injection pattern cleanly

**Usage Pattern**:
```python
# In your tool function
async def my_tool(param: str, wrapper: ContextWrapper[MyContext]) -> str:
    context = wrapper.ctx  # Type-safe access to your context
    return context.do_something(param)
```

### 3. llm.py - Core LLM Implementation

**Purpose**: The heart of the framework - handles Claude API communication, tool execution, and conversation management.

**Key Components**:

#### `LLM` Class
The main class that orchestrates everything:

**Constructor Parameters**:
- `model`: Claude model to use (default: "claude-sonnet-4-20250514")
- `system_prompt`: System instructions for the agent
- `tools`: List of callable functions the agent can use
- `msg_history`: Optional pre-existing conversation history
- `ctx`: Optional context object for dependency injection

**Key Methods**:

- `__call__(content)`: Main method for sending messages to Claude
  - Appends user message to history
  - Sends request to Claude API with tools
  - Handles both text responses and tool calls
  - Automatically manages message history
  - Returns tuple of (output_text, tool_calls)

- `execute_tool(tool_call)`: Executes a single tool call
  - Handles dependency injection via the `wrapper` parameter
  - Supports both sync and async tools
  - Returns properly formatted tool result for Claude

**Properties**:
- `messages`: Get/set conversation history
- Thread-safe message management

#### Helper Functions

- `parse_signature(func)`: Extracts type hints and required parameters from function signatures
  - Validates that all parameters have type hints
  - Skips the special `wrapper` parameter for dependency injection
  - Maps Python types to JSON schema types

- `to_json(func)`: Converts Python functions to Anthropic tool schemas
  - Validates that functions have docstrings (required for tool descriptions)
  - Generates proper JSON schema for Anthropic's API
  - Handles required vs optional parameters

- `loop(llm, input_iter)`: The main agent execution loop
  - External loop: processes messages from input iterator
  - Internal loop: continues until no tool calls are returned
  - Executes tool calls in parallel for performance
  - Manages conversation flow automatically

- `prompt_input(prompt)`: Simple input iterator for single-turn conversations

**Caching**: Uses Anthropic's ephemeral caching for the latest user message to improve performance.

### 4. tools.py - Built-in Tools

**Purpose**: Provides essential file system and shell interaction capabilities for coding agents.

**Key Tools**:

#### File Operations
- `read_file(path)`: Reads file contents with proper error handling
- `edit_file(path, old_str, new_str)`: Safe file editing with diff preview and approval

#### Shell Operations  
- `execute_bash(command)`: Executes bash commands with safety checks

**Safety Features**:

- **Diff Preview**: Shows unified diffs before applying file changes
- **User Approval**: Requires confirmation for destructive operations
- **Error Handling**: Graceful handling of file system errors
- **Security**: Approval required for dangerous bash commands (rm, git reset, etc.)

**Diff System**:
- `generate_diff()`: Creates unified diffs between file versions
- `display_diff()`: Shows colorized diffs in the terminal
- Color coding: Red for deletions, green for additions, gray for context

### 5. agents.py - Pre-configured Agents

**Purpose**: Provides factory functions for creating specialized agents with pre-configured tools and prompts.

**Current Agents**:

- `claude_code()`: Creates a coding assistant agent
  - Uses system prompt from `CLAUDE.md`
  - Equipped with file and bash tools
  - Optimized for software development tasks

**Agent Map**:
- `AGENT_MAP`: Dictionary mapping agent names to factory functions
- Enables easy agent selection via CLI

### 6. cli.py - Interactive Interface

**Purpose**: Provides a rich terminal interface for chatting with agents.

**Key Components**:

- `user_input(llm)`: Async generator that handles user interaction
  - Supports special commands: "clear" (clears history), empty input (ignored)
  - Uses prompt-toolkit for rich terminal experience
  - Yields properly formatted messages for the loop

- `chat(llm)`: Main chat interface
  - Shows agent info (model, available tools)
  - Handles keyboard interrupt gracefully
  - Provides clear user instructions

**Features**:
- **Rich Terminal**: Uses prompt-toolkit for better UX
- **Command Support**: Built-in commands for managing conversation
- **Error Handling**: Graceful handling of interrupts and errors
- **Agent Info**: Shows available tools and model information

## How Components Interact

### Agent Creation Flow
1. `agents.py` factory function creates an `LLM` instance
2. System prompt loaded from file
3. Tools list passed to LLM constructor
4. Tool schemas automatically generated from function signatures

### Conversation Flow
1. `cli.py` starts interactive session
2. User input collected via `user_input()` generator
3. Messages passed to `loop()` function
4. `loop()` calls `LLM.__call__()` to get Claude response
5. If tool calls returned, `execute_tool()` runs them in parallel
6. Results fed back to Claude until no more tool calls
7. Final response displayed to user

### Tool Execution Flow
1. Claude returns tool calls in response
2. `execute_tool()` looks up function in tool dictionary
3. Function signature inspected for `wrapper` parameter
4. Context injected if needed
5. Tool executed (async/sync handled automatically)
6. Result formatted for Claude API
7. Multiple tool calls executed in parallel

## Key Design Decisions

### Type Safety
- Extensive use of type hints throughout
- Generic `ContextWrapper` for dependency injection
- Automatic validation of tool function signatures

### Async-First Design
- All core operations are async
- Tool functions should be async (sync supported but discouraged)
- Parallel tool execution for performance

### Minimal Dependencies
- Core dependencies: anthropic, rich, pydantic-settings
- Optional dependencies for development/testing
- No heavy frameworks or unnecessary abstractions

### User Safety
- File editing with diff preview and approval
- Dangerous command approval system
- Graceful error handling and recovery

## Usage Examples

### Basic Agent Creation
```python
from nkd_agents.llm import LLM, loop, prompt_input

# Create simple agent
llm = LLM(system_prompt="You are a helpful assistant")

# Single interaction
await loop(llm, prompt_input("Hello!"))
```

### Agent with Tools
```python
async def get_weather(city: str) -> str:
    """Get weather for a city."""
    return f"Sunny in {city}"

llm = LLM(
    system_prompt="You are a weather assistant",
    tools=[get_weather]
)
```

### Interactive Chat
```python
# Use pre-built agent
from nkd_agents.agents import AGENT_MAP
from nkd_agents.cli import chat

agent = AGENT_MAP["code"]()
await chat(agent)
```

## Extension Points

### Custom Tools
Create async functions with proper type hints and docstrings:

```python
async def my_tool(param: str, wrapper: ContextWrapper[MyContext]) -> str:
    """Description of what this tool does."""
    # Tool implementation
    return result
```

### Custom Agents
Create factory functions following the pattern in `agents.py`:

```python
def my_agent() -> LLM:
    """Create my specialized agent."""
    return LLM(
        system_prompt="...",
        tools=[tool1, tool2],
        model="claude-sonnet-4-20250514"
    )
```

### Custom Input Iterators
Create async generators that yield message lists:

```python
async def my_input_source() -> AsyncIterator[List[Dict[str, str]]]:
    # Your input logic here
    yield [{"type": "text", "text": message}]
```

## Testing

The framework includes unit tests that validate:
- Function signature parsing
- Type hint validation  
- Tool schema generation
- Error handling

Tests use pytest and cover the core `llm.py` functionality.

## Summary

`nkd_agents` provides a clean, minimal foundation for building AI agents. By focusing on the essential components (LLM + Loop + Tools), it avoids unnecessary complexity while providing powerful capabilities for creating interactive, tool-enabled agents. The framework's type-safe design, async-first architecture, and built-in safety features make it suitable for both experimentation and production use cases.

The modular design allows easy customization of any component while maintaining the core conversation loop and tool execution patterns. Whether you're building a coding assistant, a data analysis agent, or a custom domain-specific agent, `nkd_agents` provides the foundation you need without getting in your way.
