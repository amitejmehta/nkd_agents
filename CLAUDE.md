# nkd_agents: Naked Agents Framework

## Roadmap

### 🔧 Chore
- [x] **Pyright Fixes**: Resolve all type checking issues and improve type annotations
  - [x] Fix missing type annotations in `config.py` and `context.py`
  - [x] Add proper return type annotations for all async functions
  - [x] Resolve `NOT_GIVEN` type issues in `llm.py`
  - [x] Add comprehensive type checking for tool schema generation
- [ ] **Unit Testing Expansion**: Achieve comprehensive test coverage
  - [ ] Add tests for `LLM` class methods (`__call__`, `execute_tool`)
  - [ ] Add tests for `loop` function with various input scenarios
  - [ ] Add tests for tool execution with context injection
  - [ ] Add integration tests for agent creation and basic workflows
  - [ ] Add tests for CLI functionality and user input handling
  - [ ] Set up test coverage reporting and CI/CD pipeline
- [ ] **Documentation**: Improve inline documentation and exampitles
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

- [x] **Sub-Agent Architecture**: Hierarchical agent delegation
  - [x] **Agent Spawning**: Parent agents can create specialized child agents
    - [x] Define sub-agent specializations and capabilities
    - [x] Pass context and constraints to child agents
    - [x] Lifecycle management (create, monitor, terminate)
  - [ ] **Task Delegation**: Intelligent work distribution
    - [ ] Automatic task routing based on agent capabilities
    - [ ] Load balancing across available sub-agents
    - [ ] Task queue management and prioritization
  - [x] **Result Aggregation**: Combine outputs from multiple sub-agents
    - [x] Merge research findings and eliminate duplicates (via shared markdown report)
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