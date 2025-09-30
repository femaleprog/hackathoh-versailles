#!/usr/bin/env python3
"""
Intelligent Query Router with LLM-based Decomposition
Decides whether to use simple RAG or complex multi-step planning
"""

import os
import json
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum
from dotenv import load_dotenv
from llama_index.llms.mistralai import MistralAI


class QueryComplexity(Enum):
    """Query complexity levels"""
    SIMPLE = "simple"           # Direct RAG lookup
    MODERATE = "moderate"       # 2-3 sub-queries
    COMPLEX = "complex"         # 4+ sub-queries with dependencies


class RouteDecision(Enum):
    """Routing decision"""
    DIRECT_RAG = "direct_rag"           # Simple query → direct RAG
    DECOMPOSE = "decompose"             # Complex query → decompose into sub-queries
    CLARIFY = "clarify"                 # Ambiguous query → ask for clarification


@dataclass
class RoutingResult:
    """Result of routing decision"""
    decision: RouteDecision
    complexity: QueryComplexity
    reasoning: str
    confidence: float
    suggested_subqueries: Optional[List[str]] = None
    clarification_questions: Optional[List[str]] = None
    direct_query: Optional[str] = None  # Reformulated query for direct RAG


@dataclass
class DecomposedQuery:
    """LLM-generated sub-query"""
    query: str
    purpose: str                    # What this sub-query aims to find
    priority: float                 # 0.0 to 1.0
    dependencies: List[str]         # List of other sub-query purposes this depends on
    required_sources: List[str]     # ["official_kb", "weather_api", "maps_api", etc.]
    expected_info: str              # What information we expect to get


class IntelligentRouter:
    """
    Intelligent router that decides query processing strategy
    Uses LLM to make routing decisions and decompose queries
    """
    
    def __init__(self):
        load_dotenv()
        
        api_key = os.getenv("MISTRAL_API_KEY")
        if not api_key:
            raise ValueError("MISTRAL_API_KEY is required")
        
        self.llm = MistralAI(model="mistral-medium-latest", api_key=api_key)
    
    async def route_query(self, query: str, conversation_history: Optional[List[Dict]] = None) -> RoutingResult:
        """
        Decide how to process the query
        Returns routing decision with reasoning
        """
        
        routing_prompt = f"""You are an intelligent query router for a Versailles Palace chatbot.
Analyze the user query and decide the best processing strategy.

USER QUERY: "{query}"

ROUTING OPTIONS:
1. DIRECT_RAG: Simple factual question that can be answered with a single knowledge base lookup
   Examples: "What time does Versailles open?", "How much is a ticket?", "Where is the Hall of Mirrors?"

2. DECOMPOSE: Complex query requiring multiple information sources or planning
   Examples: "Plan a full day visit with kids", "Accessible route for wheelchair users", "Best itinerary for rainy day"

3. CLARIFY: Ambiguous or incomplete query that needs more information
   Examples: "Tell me about Versailles", "I want to visit", "What should I do?"

ANALYSIS CRITERIA:
- Does the query ask for a single fact or multiple pieces of information?
- Does it require planning, comparison, or synthesis?
- Does it mention constraints (time, budget, accessibility, group composition)?
- Is the query specific enough to answer, or too vague?

Respond in JSON format:
{{
    "decision": "DIRECT_RAG" | "DECOMPOSE" | "CLARIFY",
    "complexity": "simple" | "moderate" | "complex",
    "reasoning": "Brief explanation of your decision",
    "confidence": 0.0-1.0,
    "direct_query": "Reformulated query for RAG (if DIRECT_RAG)",
    "clarification_questions": ["question1", "question2"] (if CLARIFY)
}}"""

        try:
            response = await self.llm.acomplete(routing_prompt)
            result_text = response.text.strip()
            
            # Extract JSON from response
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
            
            result = json.loads(result_text)
            
            return RoutingResult(
                decision=RouteDecision[result["decision"]],
                complexity=QueryComplexity[result["complexity"].upper()],
                reasoning=result["reasoning"],
                confidence=result["confidence"],
                direct_query=result.get("direct_query"),
                clarification_questions=result.get("clarification_questions")
            )
            
        except Exception as e:
            print(f"Routing error: {e}, falling back to DECOMPOSE")
            # Fallback to decompose for safety
            return RoutingResult(
                decision=RouteDecision.DECOMPOSE,
                complexity=QueryComplexity.MODERATE,
                reasoning=f"Fallback due to routing error: {str(e)}",
                confidence=0.5
            )
    
    async def decompose_query(self, query: str, routing_result: RoutingResult) -> List[DecomposedQuery]:
        """
        Use LLM to intelligently decompose a complex query into sub-queries
        This replaces the hardcoded facet-based approach
        """
        
        decomposition_prompt = f"""You are an expert at breaking down complex travel planning queries into focused sub-queries.

USER QUERY: "{query}"
COMPLEXITY: {routing_result.complexity.value}

Your task is to decompose this query into 2-5 focused sub-queries that can be answered independently.

GUIDELINES:
1. Each sub-query should target a specific information need
2. Identify dependencies between sub-queries (e.g., weather info needed before itinerary planning)
3. Specify which data sources are needed for each sub-query
4. Prioritize sub-queries by importance (1.0 = critical, 0.5 = nice-to-have)

AVAILABLE DATA SOURCES:
- official_kb: Official Versailles knowledge base (history, attractions, facilities)
- weather_api: Current and forecast weather data
- maps_api: Location search, navigation, distances
- schedule_api: Opening hours, crowd levels, special events
- accessibility_kb: Accessibility information and facilities

EXAMPLE for "Plan a rainy day visit with elderly parents":
{{
    "sub_queries": [
        {{
            "query": "What are the main indoor attractions at Versailles?",
            "purpose": "indoor_attractions",
            "priority": 1.0,
            "dependencies": [],
            "required_sources": ["official_kb"],
            "expected_info": "List of indoor areas and attractions"
        }},
        {{
            "query": "Weather forecast for Versailles today",
            "purpose": "weather_info",
            "priority": 0.9,
            "dependencies": [],
            "required_sources": ["weather_api"],
            "expected_info": "Current weather and forecast"
        }},
        {{
            "query": "Accessible routes and rest areas for elderly visitors",
            "purpose": "elderly_accessibility",
            "priority": 1.0,
            "dependencies": [],
            "required_sources": ["official_kb", "accessibility_kb"],
            "expected_info": "Wheelchair access, elevators, seating areas"
        }},
        {{
            "query": "Optimal indoor route considering weather and accessibility",
            "purpose": "route_planning",
            "priority": 0.8,
            "dependencies": ["indoor_attractions", "weather_info", "elderly_accessibility"],
            "required_sources": ["maps_api", "official_kb"],
            "expected_info": "Step-by-step itinerary with distances and times"
        }}
    ]
}}

Now decompose the user query. Respond ONLY with valid JSON in the same format."""

        try:
            response = await self.llm.acomplete(decomposition_prompt)
            result_text = response.text.strip()
            
            # Extract JSON from response
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
            
            result = json.loads(result_text)
            
            # Convert to DecomposedQuery objects
            decomposed_queries = []
            for sq in result["sub_queries"]:
                decomposed_queries.append(DecomposedQuery(
                    query=sq["query"],
                    purpose=sq["purpose"],
                    priority=sq["priority"],
                    dependencies=sq["dependencies"],
                    required_sources=sq["required_sources"],
                    expected_info=sq["expected_info"]
                ))
            
            return decomposed_queries
            
        except Exception as e:
            print(f"Decomposition error: {e}")
            # Fallback to simple decomposition
            return [DecomposedQuery(
                query=query,
                purpose="general_info",
                priority=1.0,
                dependencies=[],
                required_sources=["official_kb"],
                expected_info="General information about the query"
            )]
    
    async def process_query(self, query: str) -> Tuple[RoutingResult, Optional[List[DecomposedQuery]]]:
        """
        Main entry point: route query and decompose if needed
        Returns (routing_result, decomposed_queries)
        """
        
        # Step 1: Route the query
        routing_result = await self.route_query(query)
        
        print(f"\n🎯 ROUTING DECISION: {routing_result.decision.value}")
        print(f"   Complexity: {routing_result.complexity.value}")
        print(f"   Confidence: {routing_result.confidence:.2f}")
        print(f"   Reasoning: {routing_result.reasoning}")
        
        # Step 2: Decompose if needed
        decomposed_queries = None
        if routing_result.decision == RouteDecision.DECOMPOSE:
            print(f"\n🔍 DECOMPOSING QUERY...")
            decomposed_queries = await self.decompose_query(query, routing_result)
            print(f"   Generated {len(decomposed_queries)} sub-queries:")
            for i, sq in enumerate(decomposed_queries, 1):
                print(f"   {i}. [{sq.priority:.1f}] {sq.query}")
                print(f"      Purpose: {sq.purpose}")
                print(f"      Sources: {', '.join(sq.required_sources)}")
                if sq.dependencies:
                    print(f"      Depends on: {', '.join(sq.dependencies)}")
        
        elif routing_result.decision == RouteDecision.DIRECT_RAG:
            print(f"\n✅ DIRECT RAG")
            print(f"   Query: {routing_result.direct_query}")
        
        elif routing_result.decision == RouteDecision.CLARIFY:
            print(f"\n❓ NEEDS CLARIFICATION")
            if routing_result.clarification_questions:
                print(f"   Questions:")
                for q in routing_result.clarification_questions:
                    print(f"   - {q}")
        
        return routing_result, decomposed_queries


# Example usage and testing
async def test_router():
    """Test the intelligent router with various queries"""
    
    router = IntelligentRouter()
    
    test_queries = [
        "What time does Versailles open?",  # Should be DIRECT_RAG
        "Plan a full day visit with my 2 kids and elderly mother",  # Should be DECOMPOSE
        "I want to visit Versailles",  # Should be CLARIFY
        "Best accessible route for wheelchair users on a rainy day",  # Should be DECOMPOSE
        "How much is a ticket?",  # Should be DIRECT_RAG
    ]
    
    for query in test_queries:
        print(f"\n{'='*80}")
        print(f"QUERY: {query}")
        print(f"{'='*80}")
        
        routing_result, decomposed = await router.process_query(query)
        print()


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_router())
