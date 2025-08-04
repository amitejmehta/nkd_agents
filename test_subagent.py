#!/usr/bin/env python3
"""
Simple test script for sub-agent spawning functionality.
Run this to verify the sub-agent system works correctly.
"""

import asyncio
from nkd_agents.agents import claude_research
from nkd_agents.llm import loop, prompt_input


async def test_subagent():
    """Test the sub-agent spawning functionality with a simple research task."""
    
    # Create a research agent
    agent = claude_research()
    
    # Give it a complex research task that would benefit from sub-agents
    task = """I need to research the current state of AI agent frameworks. Please investigate:
1. What are the most popular open-source agent frameworks available today?
2. What are their key features and architectural approaches?
3. How do they handle tool integration and multi-agent coordination?

Use sub-agents to investigate different aspects of this question systematically."""
    
    print("🔬 Starting research agent test...")
    print(f"Task: {task}")
    print("-" * 50)
    
    try:
        # Run the research agent
        result = await loop(agent, prompt_input(task))
        print(f"\n✅ Research completed!")
        print(f"Result: {result}")
        
        # Check if research report was created
        from pathlib import Path
        report_path = Path("research_report.md")
        if report_path.exists():
            print(f"\n📊 Research report created at: {report_path}")
            print("Preview of research report:")
            print("-" * 30)
            content = report_path.read_text()
            print(content[:500] + "..." if len(content) > 500 else content)
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_subagent())