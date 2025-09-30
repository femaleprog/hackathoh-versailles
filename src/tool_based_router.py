#!/usr/bin/env python3
"""
Tool-based Query Router
Routes queries based on required tools/data sources, not complexity
"""

import os
import json
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum
from dotenv import load_dotenv
from llama_index.llms.mistralai import MistralAI


class ToolType(Enum):
    """Available tools and data sources"""
    KNOWLEDGE_BASE = "knowledge_base"           # Official Versailles KB (RAG)
    GOOGLE_MAPS = "google_maps"                 # Location, directions, distances
    GOOGLE_WEATHER = "google_weather"           # Weather forecast
    SCHEDULE_API = "schedule_api"               # Opening hours, crowd levels
    RESTAURANT_API = "restaurant_api"           # Nearby restaurants
    HOTEL_API = "hotel_api"                     # Nearby hotels
    ACCESSIBILITY_KB = "accessibility_kb"       # Accessibility information


@dataclass
class ToolRequirement:
    """Requirement for a specific tool"""
    tool: ToolType
    purpose: str                                # Why this tool is needed
    priority: float                             # 0.0 to 1.0
    query_for_tool: str                         # Specific query for this tool
    expected_output: str                        # What we expect to get


@dataclass
class RoutingDecision:
    """Routing decision based on tool requirements"""
    required_tools: List[ToolRequirement]
    can_answer_directly: bool                   # Can answer with single tool
    needs_synthesis: bool                       # Needs to combine multiple sources
    reasoning: str
    confidence: float
    execution_plan: str                         # How to execute (sequential/parallel)


class ToolBasedRouter:
    """
    Routes queries based on required tools, not complexity
    LLM decides which tools are needed to answer the query
    """
    
    def __init__(self):
        load_dotenv()
        
        api_key = os.getenv("MISTRAL_API_KEY")
        if not api_key:
            raise ValueError("MISTRAL_API_KEY is required")
        
        self.llm = MistralAI(model="mistral-medium-latest", api_key=api_key)
        
        # Tool descriptions for LLM
        self.tool_descriptions = {
            "knowledge_base": "Official Versailles knowledge base - history, attractions, facilities, general information",
            "google_maps": "Google Maps API - location search, directions, distances, navigation between places",
            "google_weather": "Weather API - current weather, forecasts, seasonal conditions",
            "schedule_api": "Schedule API - opening hours, closing times, crowd levels, special events",
            "restaurant_api": "Restaurant recommendations - nearby dining options with ratings and reviews",
            "hotel_api": "Hotel recommendations - nearby accommodation with ratings and prices",
            "accessibility_kb": "Accessibility information - wheelchair access, elevators, accessible routes, facilities"
        }
    
    async def route_query(self, query: str) -> RoutingDecision:
        """
        Analyze query and determine which tools are needed
        """
        
        tools_list = "\n".join([f"- **{k}**: {v}" for k, v in self.tool_descriptions.items()])
        
        routing_prompt = f"""You are a tool selection expert for a Versailles Palace chatbot.
Analyze the user query and determine which tools/data sources are needed to answer it.

USER QUERY: "{query}"

AVAILABLE TOOLS:
{tools_list}

YOUR TASK:
1. Identify ALL tools needed to answer this query
2. For each tool, specify:
   - Why it's needed
   - Priority (1.0 = critical, 0.5 = nice-to-have)
   - Specific query for that tool
   - Expected output
3. Determine if answer can be given directly or needs synthesis

EXAMPLES:

Query: "What time does Versailles open?"
→ Tools: [schedule_api]
→ Can answer directly: YES
→ No synthesis needed

Query: "Where is the Hall of Mirrors?"
→ Tools: [knowledge_base, google_maps]
→ Can answer directly: NO (need to combine location info + directions)
→ Needs synthesis: YES

Query: "Plan a rainy day visit with wheelchair access"
→ Tools: [google_weather, accessibility_kb, knowledge_base, google_maps]
→ Can answer directly: NO
→ Needs synthesis: YES (complex planning)

Query: "Best restaurants near Versailles"
→ Tools: [restaurant_api, google_maps]
→ Can answer directly: NO (need to combine recommendations + distances)
→ Needs synthesis: YES

Respond in JSON format:
{{
    "required_tools": [
        {{
            "tool": "tool_name",
            "purpose": "why this tool is needed",
            "priority": 0.0-1.0,
            "query_for_tool": "specific query for this tool",
            "expected_output": "what we expect to get"
        }}
    ],
    "can_answer_directly": true/false,
    "needs_synthesis": true/false,
    "reasoning": "brief explanation of tool selection",
    "confidence": 0.0-1.0,
    "execution_plan": "sequential" or "parallel"
}}

IMPORTANT:
- If query asks about LOCATION/DIRECTIONS → include google_maps
- If query asks about WEATHER → include google_weather
- If query asks about OPENING HOURS/CROWDS → include schedule_api
- If query asks about RESTAURANTS/DINING → include restaurant_api
- If query asks about HOTELS/ACCOMMODATION → include hotel_api
- If query asks about ACCESSIBILITY/WHEELCHAIR → include accessibility_kb
- For general information → use knowledge_base

Now analyze the query and respond with JSON only."""

        try:
            response = await self.llm.acomplete(routing_prompt)
            result_text = response.text.strip()
            
            # Extract JSON from response
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
            
            # Fix common JSON issues
            result_text = result_text.replace('\n', ' ')  # Remove newlines
            result_text = result_text.replace('\t', ' ')  # Remove tabs
            # Remove control characters
            result_text = ''.join(char for char in result_text if ord(char) >= 32 or char in '\n\r\t')
            
            result = json.loads(result_text)
            
            # Convert to ToolRequirement objects
            tool_requirements = []
            for tool_data in result["required_tools"]:
                tool_requirements.append(ToolRequirement(
                    tool=ToolType[tool_data["tool"].upper()],
                    purpose=tool_data["purpose"],
                    priority=tool_data["priority"],
                    query_for_tool=tool_data["query_for_tool"],
                    expected_output=tool_data["expected_output"]
                ))
            
            return RoutingDecision(
                required_tools=tool_requirements,
                can_answer_directly=result["can_answer_directly"],
                needs_synthesis=result["needs_synthesis"],
                reasoning=result["reasoning"],
                confidence=result["confidence"],
                execution_plan=result["execution_plan"]
            )
            
        except Exception as e:
            print(f"Routing error: {e}")
            # Fallback to knowledge base only
            return RoutingDecision(
                required_tools=[ToolRequirement(
                    tool=ToolType.KNOWLEDGE_BASE,
                    purpose="Fallback to general knowledge base",
                    priority=1.0,
                    query_for_tool=query,
                    expected_output="General information"
                )],
                can_answer_directly=True,
                needs_synthesis=False,
                reasoning=f"Fallback due to error: {str(e)}",
                confidence=0.5,
                execution_plan="sequential"
            )
    
    async def execute_routing(self, query: str) -> Tuple[RoutingDecision, Dict[str, Any]]:
        """
        Route query and provide execution guidance
        """
        
        routing = await self.route_query(query)
        
        print(f"\n{'='*100}")
        print(f"🎯 TOOL-BASED ROUTING")
        print(f"{'='*100}")
        print(f"📝 Query: \"{query}\"")
        print(f"💭 Reasoning: {routing.reasoning}")
        print(f"📊 Confidence: {routing.confidence:.2f}")
        print(f"\n🔧 Required Tools ({len(routing.required_tools)}):")
        
        for i, tool_req in enumerate(routing.required_tools, 1):
            print(f"\n   {i}. {tool_req.tool.value} [Priority: {tool_req.priority:.1f}]")
            print(f"      Purpose: {tool_req.purpose}")
            print(f"      Query: \"{tool_req.query_for_tool}\"")
            print(f"      Expected: {tool_req.expected_output}")
        
        print(f"\n📋 Execution Plan:")
        print(f"   • Can answer directly: {'✅ YES' if routing.can_answer_directly else '❌ NO'}")
        print(f"   • Needs synthesis: {'✅ YES' if routing.needs_synthesis else '❌ NO'}")
        print(f"   • Execution mode: {routing.execution_plan.upper()}")
        
        # Provide execution guidance
        execution_guidance = {
            "single_tool": len(routing.required_tools) == 1,
            "parallel_execution": routing.execution_plan == "parallel" and len(routing.required_tools) > 1,
            "needs_llm_synthesis": routing.needs_synthesis,
            "estimated_time": self._estimate_execution_time(routing)
        }
        
        print(f"\n⏱️  Estimated Time: {execution_guidance['estimated_time']:.1f}s")
        
        if execution_guidance["single_tool"]:
            print(f"   → Single tool execution (fast path)")
        elif execution_guidance["parallel_execution"]:
            print(f"   → Parallel execution of {len(routing.required_tools)} tools")
        else:
            print(f"   → Sequential execution required")
        
        print(f"{'='*100}\n")
        
        return routing, execution_guidance
    
    def _estimate_execution_time(self, routing: RoutingDecision) -> float:
        """Estimate execution time based on tools"""
        
        # Base time estimates per tool (seconds)
        tool_times = {
            ToolType.KNOWLEDGE_BASE: 1.0,
            ToolType.GOOGLE_MAPS: 1.5,
            ToolType.GOOGLE_WEATHER: 1.0,
            ToolType.SCHEDULE_API: 1.0,
            ToolType.RESTAURANT_API: 2.0,
            ToolType.HOTEL_API: 2.0,
            ToolType.ACCESSIBILITY_KB: 1.0
        }
        
        if routing.execution_plan == "parallel":
            # Parallel: time = max(tool_times) + synthesis
            max_time = max([tool_times.get(tr.tool, 1.0) for tr in routing.required_tools])
            synthesis_time = 2.0 if routing.needs_synthesis else 0.5
            return max_time + synthesis_time
        else:
            # Sequential: time = sum(tool_times) + synthesis
            total_time = sum([tool_times.get(tr.tool, 1.0) for tr in routing.required_tools])
            synthesis_time = 2.0 if routing.needs_synthesis else 0.5
            return total_time + synthesis_time


# Example usage and testing
async def test_tool_based_routing():
    """Test the tool-based router with various queries"""
    
    router = ToolBasedRouter()
    
    test_queries = [
        # Simple queries
        "What time does Versailles open?",
        "How much is a ticket?",
        
        # Location queries (should use google_maps)
        "Where is the Hall of Mirrors?",
        "How do I get from the palace to the gardens?",
        
        # Weather queries
        "What's the weather like today?",
        
        # Complex planning queries
        "Plan a rainy day visit with wheelchair access",
        "Best restaurants near Versailles with good reviews",
        "Find hotels near Versailles under 150 euros",
        
        # Multi-tool queries
        "What are the opening hours and how's the weather?",
        "Show me accessible routes to indoor attractions",
    ]
    
    print(f"\n{'='*100}")
    print(f"🧪 TOOL-BASED ROUTING TEST")
    print(f"{'='*100}\n")
    
    for query in test_queries:
        routing, guidance = await router.execute_routing(query)
        
        # Brief pause between tests
        import asyncio
        await asyncio.sleep(0.5)
    
    print(f"\n{'='*100}")
    print(f"✅ All tests completed!")
    print(f"{'='*100}\n")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_tool_based_routing())
