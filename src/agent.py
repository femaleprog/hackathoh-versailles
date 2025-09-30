# src/agent.py

import json
import os
import time
import uuid
from datetime import datetime
from typing import Any, AsyncGenerator, Dict

from dotenv import load_dotenv
from llama_index.core.agent.workflow import (
    AgentStream,
    FunctionAgent,
    ToolCall,
    ToolCallResult,
)
from llama_index.core.tools import FunctionTool
from llama_index.llms.mistralai import MistralAI

# Import tools
from src.tools.rag import versailles_expert_tool
from src.tools.schedule_scraper import scrape_versailles_schedule
from src.tools.google import (
    search_places_in_versailles,
    get_best_route_between_places,
    get_weather_in_versailles
)


def sum_numbers(a: int, b: int) -> int:
    """Additionne deux nombres entiers."""
    return a + b


class Agent:
    """
    Un agent encapsulant un FunctionAgent de LlamaIndex avec un LLM Mistral.
    """

    def __init__(self):
        """Initialise l'agent, le LLM et les outils."""

        load_dotenv()

        api_key = os.getenv("MISTRAL_API_KEY")
        if not api_key:
            raise ValueError("La variable d'environnement MISTRAL_API_KEY est requise.")

        self.llm = MistralAI(model="mistral-medium-latest", api_key=api_key)

        self.tools = [
            FunctionTool.from_defaults(
                fn=sum_numbers,
                # name="sum_numbers",
                description="Allows the LLM to sum up two numbers",
            ),
            FunctionTool.from_defaults(
                fn=versailles_expert_tool,
                name="versailles_expert",
                description="Ask questions about the Palace of Versailles. Provides comprehensive expert answers with historical, architectural, and cultural information about Versailles, its history, gardens, and notable figures like Louis XIV and Marie Antoinette.",
            ),
            FunctionTool.from_defaults(
                fn=scrape_versailles_schedule,
                name="get_versailles_schedule",
                description="Retrieves the opening hours, visitor numbers and schedule for the Palace of Versailles and its estate for a specific date. The input must be a date string in 'YYYY-MM-DD' format.",
            ),
            FunctionTool.from_defaults(
                fn=search_places_in_versailles,
                name="search_places_versailles",
                description="Search for specific places, buildings, or locations within Versailles using Google Places API. Returns place name, address, and place ID. Automatically adds 'Versailles' to the search query.",
            ),
            FunctionTool.from_defaults(
                fn=get_best_route_between_places,
                name="get_walking_route",
                description="Calculate the optimal walking route between multiple places in Versailles. Takes a list of place names and returns the best route with duration, distance, and detailed walking directions.",
            ),
            FunctionTool.from_defaults(
                fn=get_weather_in_versailles,
                name="get_versailles_weather",
                description="Get weather forecast for Versailles. Takes the number of days (1-7) and returns detailed weather information including temperature, conditions, and precipitation.",
            ),
        ]

        today_date = datetime.now().strftime("%Y-%m-%d")
        self.agent = FunctionAgent(
            llm=self.llm,
            tools=self.tools,
            system_prompt=f"Today's date is {today_date}.",
            verbose=True,
        )

    def _format_chunk(self, content: str) -> str:
        chunk = {
            "id": 123,
            "object": "chat.completion.chunk",
            "created": int(datetime.now().timestamp()),
            "model": "Mistral",
            "choices": [
                {"index": 0, "delta": {"content": content}, "finish_reason": None}
            ],
        }
        return f"data: {json.dumps(chunk)}\n\n"

    def _get_nonstream_response_template(
        self,
        response_id: str,
    ) -> str:
        """
        Create a template for non-streaming chat completion response.

        Args:
            response_id: Unique identifier for the response
            model_name: Name of the model generating the response

        Returns:
            Dictionary template for non-streaming response
        """
        response = {
            "id": response_id,
            "object": "chat.completion",
            "created": int(datetime.now().timestamp()),
            "model": "mistral",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [],
                    },
                    "finish_reason": "tool_calls",
                }
            ],
        }
        return response

    async def _internal_streamer(self, query) -> AsyncGenerator[str, None]:
        try:
            today_date = datetime.now().strftime("%Y-%m-%d")
            handler = self.agent.run(
                f"Today's date is {today_date}, use only if it's need." + query
            )

            async for event in handler.stream_events():
                if isinstance(event, AgentStream):
                    yield self._format_chunk(event.delta)
        except Exception as e:
            raise e

    async def chat_completion_non_stream(self, query: str) -> str:
        """Traite une requête en mode non-stream."""

        handler = self.agent.run(query)
        response = self._get_nonstream_response_template(str(uuid.uuid4()))
        async for event in handler.stream_events():
            if isinstance(event, AgentStream):
                if not response["choices"][0]["message"]["content"]:
                    response["choices"][0]["message"]["content"] = event.delta
                else:
                    response["choices"][0]["message"]["content"] += event.delta
            elif isinstance(event, ToolCall):
                tool_call_id = f"call_{uuid.uuid4().hex}"
                response["choices"][0]["message"]["tool_calls"].append(
                    {
                        "id": tool_call_id,
                        "type": "function",
                        "function": {
                            "name": event.tool_name,
                            "arguments": json.dumps(event.tool_kwargs),
                        },
                    }
                )

            elif isinstance(event, ToolCallResult):
                for tool_call in response["choices"][0]["message"]["tool_calls"]:
                    if tool_call["function"]["name"] == event.tool_name:
                        tool_call["function"]["output"] = str(
                            event.tool_output.model_dump() or ""
                        )
                return response
        return response

    def chat_completion_stream(self, query: str) -> AsyncGenerator:
        """Traite une requête en mode stream."""

        return self._internal_streamer(query)
