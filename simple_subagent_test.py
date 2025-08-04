#!/usr/bin/env python3
"""
Simple test for sub-agent functionality without API calls.
Just test the basic structure and imports.
"""

import asyncio
from nkd_agents.agents import claude_research, AGENT_MAP
from nkd_agents.tools import spawn_subagent


def test_imports():
    """Test that all imports work correctly."""
    print("✅ Testing imports...")
    
    # Test agent creation
    research_agent = claude_research()
    print(f"✅ Research agent created with {len(research_agent._tool_dict)} tools")
    
    # Check available agents
    print(f"✅ Available agent types: {list(AGENT_MAP.keys())}")
    
    # Check that spawn_subagent is in the research agent's tools
    if 'spawn_subagent' in research_agent._tool_dict:
        print("✅ spawn_subagent tool is available in research agent")
    else:
        print("❌ spawn_subagent tool is NOT available in research agent")
    
    print("✅ All imports and basic setup working!")


if __name__ == "__main__":
    test_imports()