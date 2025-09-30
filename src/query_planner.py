#!/usr/bin/env python3
"""
Query Planner Agent for Versailles Chatbot

This module implements an intelligent query planner that analyzes user queries
and determines which tools to use before passing the refined query to the RAG system.
"""

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv
from llama_index.llms.mistralai import MistralAI

# Import tools
from src.tools.google import (
    get_best_route_between_places,
    get_weather_in_versailles,
    search_places_in_versailles,
)
from src.tools.rag import versailles_expert_tool
from src.tools.schedule_scraper import scrape_versailles_schedule


class QueryType(Enum):
    """Types of queries that can be handled"""

    PURE_KNOWLEDGE = "pure_knowledge"  # Only needs RAG
    LOCATION_SEARCH = "location_search"  # Needs place search
    ROUTE_PLANNING = "route_planning"  # Needs route planning
    WEATHER_INQUIRY = "weather_inquiry"  # Needs weather info
    SCHEDULE_CHECK = "schedule_check"  # Needs schedule info
    MIXED_QUERY = "mixed_query"  # Needs multiple tools


@dataclass
class QueryAnalysis:
    """Analysis result of a user query"""

    query_type: QueryType
    confidence: float
    required_tools: List[str]
    extracted_entities: Dict[str, Any]
    reasoning: str


@dataclass
class ToolResult:
    """Result from a tool execution"""

    tool_name: str
    success: bool
    data: Any
    error: Optional[str] = None


class QueryPlanner:
    """
    Intelligent query planner that analyzes queries and coordinates tool usage
    """

    def __init__(self):
        """Initialize the Query Planner"""
        load_dotenv()

        api_key = os.getenv("MISTRAL_API_KEY")
        if not api_key:
            raise ValueError("MISTRAL_API_KEY is required for Query Planner")

        self.llm = MistralAI(model="mistral-medium-latest", api_key=api_key)

        # Define query patterns for different types
        self.patterns = {
            QueryType.LOCATION_SEARCH: [
                r"où\s+(?:se trouve|est|est-ce que je peux trouver)",
                r"where\s+(?:is|can I find|to find)",
                r"location\s+of",
                r"address\s+of",
                r"find\s+(?:the\s+)?(?:location|place|building)",
                r"chercher\s+(?:le\s+lieu|l'endroit|la\s+place)",
            ],
            QueryType.ROUTE_PLANNING: [
                r"comment\s+(?:aller|me rendre|y aller)",
                r"how\s+(?:to get|do I get|can I go)",
                r"route\s+(?:from|to|between)",
                r"chemin\s+(?:vers|de|entre)",
                r"itinéraire\s+(?:pour|vers|de)",
                r"plan\s+(?:a\s+)?(?:route|path|walk)",
                r"walking\s+(?:route|path|directions)",
            ],
            QueryType.WEATHER_INQUIRY: [
                r"météo|weather|temps\s+(?:qu'il fait|aujourd'hui|demain)",
                r"(?:will it|va-t-il)\s+(?:rain|pleuvoir)",
                r"temperature|température",
                r"forecast|prévisions",
                r"sunny|cloudy|rainy|ensoleillé|nuageux|pluvieux",
            ],
            QueryType.SCHEDULE_CHECK: [
                r"(?:heures?\s+d')?ouverture|opening\s+(?:hours?|times?)",
                r"(?:quand|when)\s+(?:est-ce que|does|do)\s+(?:c'est\s+)?ouvert",
                r"fermé|closed|fermeture",
                r"horaires?|schedule|timetable",
                r"combien\s+de\s+(?:visiteurs|monde|personnes)",
                r"(?:visitor|attendance)\s+(?:numbers?|count)",
            ],
        }

    def analyze_query(self, query: str) -> QueryAnalysis:
        """
        Analyze a user query to determine what tools are needed

        Args:
            query: The user's query string

        Returns:
            QueryAnalysis object with analysis results
        """
        query_lower = query.lower()
        required_tools = []
        extracted_entities = {}
        confidence_scores = {}

        # Check for each query type
        for query_type, patterns in self.patterns.items():
            score = 0
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    score += 1

            if score > 0:
                confidence_scores[query_type] = score / len(patterns)

        # Extract entities
        extracted_entities = self._extract_entities(query)

        # Determine primary query type and required tools
        if confidence_scores:
            primary_type = max(
                confidence_scores.keys(), key=lambda k: confidence_scores[k]
            )
            max_confidence = confidence_scores[primary_type]

            # Determine required tools based on query type
            if primary_type == QueryType.LOCATION_SEARCH:
                required_tools.append("search_places_versailles")
            elif primary_type == QueryType.ROUTE_PLANNING:
                required_tools.extend(["search_places_versailles", "get_walking_route"])
            elif primary_type == QueryType.WEATHER_INQUIRY:
                required_tools.append("get_versailles_weather")
            elif primary_type == QueryType.SCHEDULE_CHECK:
                required_tools.append("get_versailles_schedule")

            # Check for mixed queries (multiple high confidence scores)
            high_confidence_types = [t for t, c in confidence_scores.items() if c > 0.3]
            if len(high_confidence_types) > 1:
                primary_type = QueryType.MIXED_QUERY
                # Add tools for all detected types
                for qtype in high_confidence_types:
                    if (
                        qtype == QueryType.LOCATION_SEARCH
                        and "search_places_versailles" not in required_tools
                    ):
                        required_tools.append("search_places_versailles")
                    elif qtype == QueryType.ROUTE_PLANNING:
                        if "search_places_versailles" not in required_tools:
                            required_tools.append("search_places_versailles")
                        if "get_walking_route" not in required_tools:
                            required_tools.append("get_walking_route")
                    elif (
                        qtype == QueryType.WEATHER_INQUIRY
                        and "get_versailles_weather" not in required_tools
                    ):
                        required_tools.append("get_versailles_weather")
                    elif (
                        qtype == QueryType.SCHEDULE_CHECK
                        and "get_versailles_schedule" not in required_tools
                    ):
                        required_tools.append("get_versailles_schedule")
        else:
            # Default to pure knowledge query
            primary_type = QueryType.PURE_KNOWLEDGE
            max_confidence = 1.0

        # Always include RAG tool for final answer generation
        if "versailles_expert" not in required_tools:
            required_tools.append("versailles_expert")

        reasoning = self._generate_reasoning(
            primary_type, confidence_scores, extracted_entities
        )

        return QueryAnalysis(
            query_type=primary_type,
            confidence=max_confidence,
            required_tools=required_tools,
            extracted_entities=extracted_entities,
            reasoning=reasoning,
        )

    def _extract_entities(self, query: str) -> Dict[str, Any]:
        """Extract relevant entities from the query"""
        entities = {}

        # Extract dates
        date_patterns = [
            r"aujourd'hui|today",
            r"demain|tomorrow",
            r"(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})",
            r"(\d{4})[\/\-](\d{1,2})[\/\-](\d{1,2})",
        ]

        for pattern in date_patterns:
            match = re.search(pattern, query.lower())
            if match:
                if "aujourd'hui" in match.group() or "today" in match.group():
                    entities["date"] = datetime.now().strftime("%Y-%m-%d")
                elif "demain" in match.group() or "tomorrow" in match.group():
                    entities["date"] = (datetime.now() + timedelta(days=1)).strftime(
                        "%Y-%m-%d"
                    )
                else:
                    # Try to parse the date
                    try:
                        if len(match.groups()) == 3:
                            if len(match.group(1)) == 4:  # YYYY-MM-DD format
                                entities["date"] = (
                                    f"{match.group(1)}-{match.group(2).zfill(2)}-{match.group(3).zfill(2)}"
                                )
                            else:  # DD/MM/YYYY format
                                entities["date"] = (
                                    f"{match.group(3)}-{match.group(2).zfill(2)}-{match.group(1).zfill(2)}"
                                )
                    except:
                        pass
                break

        # Extract place names (common Versailles locations)
        places = [
            "galerie des glaces",
            "hall of mirrors",
            "miroir",
            "petit trianon",
            "grand trianon",
            "hameau de la reine",
            "marie antoinette",
            "hamlet",
            "jardins",
            "gardens",
            "parc",
            "château",
            "palace",
            "palais",
            "écuries",
            "stables",
            "orangerie",
            "bosquets",
        ]

        found_places = []
        for place in places:
            if place in query.lower():
                found_places.append(place)

        if found_places:
            entities["places"] = found_places

        # Extract weather-related time frames
        weather_times = [
            r"(\d+)\s+(?:jours?|days?)",
            r"cette\s+semaine|this\s+week",
            r"week-?end|weekend",
        ]

        for pattern in weather_times:
            match = re.search(pattern, query.lower())
            if match:
                if "jours" in match.group() or "days" in match.group():
                    entities["weather_days"] = int(match.group(1))
                elif "semaine" in match.group() or "week" in match.group():
                    entities["weather_days"] = 7
                break

        return entities

    def _generate_reasoning(
        self, query_type: QueryType, confidence_scores: Dict, entities: Dict
    ) -> str:
        """Generate reasoning for the query analysis"""
        reasoning_parts = []

        reasoning_parts.append(f"Query classified as: {query_type.value}")

        if confidence_scores:
            top_scores = sorted(
                confidence_scores.items(), key=lambda x: x[1], reverse=True
            )[:3]
            reasoning_parts.append(
                f"Confidence scores: {', '.join([f'{t.value}: {s:.2f}' for t, s in top_scores])}"
            )

        if entities:
            reasoning_parts.append(f"Extracted entities: {entities}")

        return " | ".join(reasoning_parts)

    async def execute_tools(
        self, required_tools: List[str], entities: Dict[str, Any], original_query: str
    ) -> Dict[str, ToolResult]:
        """
        Execute the required tools in the correct order

        Args:
            required_tools: List of tool names to execute
            entities: Extracted entities from the query
            original_query: The original user query

        Returns:
            Dictionary of tool results
        """
        results = {}

        # Execute tools in dependency order
        tool_order = [
            "get_versailles_schedule",
            "get_versailles_weather",
            "search_places_versailles",
            "get_walking_route",
            "versailles_expert",
        ]

        for tool_name in tool_order:
            if tool_name in required_tools:
                try:
                    result = await self._execute_single_tool(
                        tool_name, entities, original_query, results
                    )
                    results[tool_name] = result
                except Exception as e:
                    results[tool_name] = ToolResult(
                        tool_name=tool_name, success=False, data=None, error=str(e)
                    )

        return results

    async def _execute_single_tool(
        self, tool_name: str, entities: Dict, query: str, previous_results: Dict
    ) -> ToolResult:
        """Execute a single tool with appropriate parameters"""

        if tool_name == "get_versailles_schedule":
            date = entities.get("date", datetime.now().strftime("%Y-%m-%d"))
            result = scrape_versailles_schedule(date)
            return ToolResult(tool_name, True, result)

        elif tool_name == "get_versailles_weather":
            days = entities.get("weather_days", 3)
            result = get_weather_in_versailles(days)
            return ToolResult(tool_name, True, result)

        elif tool_name == "search_places_versailles":
            places = entities.get("places", [])
            if places:
                # Search for the first mentioned place
                place_query = places[0]
                result = search_places_in_versailles(place_query)
                return ToolResult(tool_name, True, result)
            else:
                # Extract place from query using LLM
                place_query = await self._extract_place_with_llm(query)
                if place_query:
                    result = search_places_in_versailles(place_query)
                    return ToolResult(tool_name, True, result)
                else:
                    return ToolResult(tool_name, False, None, "No place found in query")

        elif tool_name == "get_walking_route":
            places = entities.get("places", [])
            if len(places) >= 2:
                result = get_best_route_between_places(places)
                return ToolResult(tool_name, True, result)
            else:
                # Try to extract route from query
                route_places = await self._extract_route_with_llm(query)
                if len(route_places) >= 2:
                    result = get_best_route_between_places(route_places)
                    return ToolResult(tool_name, True, result)
                else:
                    return ToolResult(
                        tool_name, False, None, "Insufficient places for route planning"
                    )

        elif tool_name == "versailles_expert":
            # Refine query with previous tool results
            refined_query = self._refine_query_with_context(query, previous_results)
            result = versailles_expert_tool(refined_query)
            return ToolResult(tool_name, True, result)

        else:
            return ToolResult(tool_name, False, None, f"Unknown tool: {tool_name}")

    async def _extract_place_with_llm(self, query: str) -> Optional[str]:
        """Use LLM to extract place name from query"""
        prompt = f"""
        Extract the main place or location mentioned in this query about Versailles:
        "{query}"
        
        Return only the place name, or "NONE" if no specific place is mentioned.
        Examples: "Hall of Mirrors", "Petit Trianon", "Gardens", "Palace entrance"
        """

        try:
            response = await self.llm.acomplete(prompt)
            place = response.text.strip()
            return place if place != "NONE" else None
        except:
            return None

    async def _extract_route_with_llm(self, query: str) -> List[str]:
        """Use LLM to extract route places from query"""
        prompt = f"""
        Extract the starting point and destination from this route query about Versailles:
        "{query}"
        
        Return as JSON array of place names, or empty array if unclear.
        Example: ["Palace entrance", "Petit Trianon"]
        """

        try:
            response = await self.llm.acomplete(prompt)
            places = json.loads(response.text.strip())
            return places if isinstance(places, list) else []
        except:
            return []

    def _refine_query_with_context(
        self, original_query: str, tool_results: Dict[str, ToolResult]
    ) -> str:
        """
        Refine the original query with context from tool results

        Args:
            original_query: The original user query
            tool_results: Results from executed tools

        Returns:
            Refined query with additional context
        """
        context_parts = [f"Original question: {original_query}"]

        # Add context from successful tool results
        for tool_name, result in tool_results.items():
            if result.success and tool_name != "versailles_expert":
                if tool_name == "get_versailles_schedule":
                    context_parts.append(
                        f"Current schedule information: {str(result.data)[:200]}..."
                    )
                elif tool_name == "get_versailles_weather":
                    context_parts.append(
                        f"Weather forecast: {str(result.data)[:200]}..."
                    )
                elif tool_name == "search_places_versailles":
                    context_parts.append(
                        f"Location details: {str(result.data)[:200]}..."
                    )
                elif tool_name == "get_walking_route":
                    context_parts.append(
                        f"Route information: {str(result.data)[:200]}..."
                    )

        refined_query = "\n\n".join(context_parts)
        refined_query += (
            "\n\nPlease provide a comprehensive answer using all the above information."
        )

        return refined_query

    async def process_query(
        self, query: str
    ) -> Tuple[QueryAnalysis, Dict[str, ToolResult], str]:
        """
        Main method to process a query through the complete pipeline

        Args:
            query: The user's query

        Returns:
            Tuple of (analysis, tool_results, final_answer)
        """
        # Step 1: Analyze the query
        analysis = self.analyze_query(query)

        # Step 2: Execute required tools
        tool_results = await self.execute_tools(
            analysis.required_tools, analysis.extracted_entities, query
        )

        # Step 3: Get final answer from RAG
        final_answer = ""
        if "versailles_expert" in tool_results:
            rag_result = tool_results["versailles_expert"]
            if rag_result.success:
                final_answer = rag_result.data
            else:
                final_answer = "I apologize, but I encountered an error while processing your question."

        return analysis, tool_results, final_answer
