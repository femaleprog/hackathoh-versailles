# src/agent.py

import json
import logging  # Ajout
import os
import time
import uuid
from datetime import datetime
from typing import Any, AsyncGenerator, Dict

from dotenv import load_dotenv
from langfuse import Langfuse, observe
from llama_index.core.agent.workflow import (
    AgentStream,
    FunctionAgent,
    ToolCall,
    ToolCallResult,
)
from llama_index.core.tools import FunctionTool
from llama_index.llms.mistralai import MistralAI
from openinference.instrumentation.llama_index import LlamaIndexInstrumentor

# Import tools
from src.query_planner import QueryPlanner
from src.tools.google import (
    get_best_route_between_places,
    get_weather_in_versailles,
    search_places_in_versailles,
)
from src.tools.rag import versailles_dual_rag_tool
from src.tools.schedule_scraper import scrape_versailles_schedule
from src.utils import get_langfuse

# --- Configuration du logging ---
# Mettez le level à logging.DEBUG pour tout voir, ou logging.INFO pour moins de détails
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
# --------------------------------

LlamaIndexInstrumentor().instrument()

langfuse = get_langfuse()


@observe(name="sum_numbers")
def sum_numbers(a: int, b: int) -> int:
    """Additionne deux nombres entiers."""
    return a + b


class Agent:
    """
    Un agent encapsulant un FunctionAgent de LlamaIndex avec un LLM Mistral.
    """

    def __init__(self, session_id: str = None):
        """Initialise l'agent, le LLM et les outils."""
        logger.info("Initializing Agent...")
        self.session_id = session_id or str(uuid.uuid4())
        logger.info(f"Session ID: {self.session_id}")

        load_dotenv()

        api_key = os.getenv("MISTRAL_API_KEY")
        if not api_key:
            logger.error("MISTRAL_API_KEY environment variable not found.")
            raise ValueError("La variable d'environnement MISTRAL_API_KEY est requise.")

        self.llm = MistralAI(model="mistral-large-latest", api_key=api_key)
        logger.info(f"MistralAI LLM initialized with model: {self.llm.model}")

        # Initialize Query Planner
        self.query_planner = QueryPlanner()
        logger.info("QueryPlanner initialized.")

        self.tools = [
            # ... (les définitions de vos outils restent inchangées) ...
            FunctionTool.from_defaults(
                fn=versailles_dual_rag_tool, name="versailles_expert", description="..."
            ),
            FunctionTool.from_defaults(
                fn=scrape_versailles_schedule,
                name="get_versailles_schedule",
                description="...",
            ),
            FunctionTool.from_defaults(
                fn=search_places_in_versailles,
                name="search_places_versailles",
                description="...",
            ),
            FunctionTool.from_defaults(
                fn=get_best_route_between_places,
                name="get_walking_route",
                description="...",
            ),
            FunctionTool.from_defaults(
                fn=get_weather_in_versailles,
                name="get_versailles_weather",
                description="...",
            ),
        ]
        logger.info(f"Loaded {len(self.tools)} tools.")

        today_date = datetime.now().strftime("%Y-%m-%d")

        # --- CORRECTION PROBABLE (Prompt Système) ---
        # Un prompt minimaliste peut être la cause des réponses vides.
        # Le LLM utilise les outils mais "oublie" de formuler une réponse finale.
        system_prompt = (
            f"Today's date is {today_date}. "
            "You are a helpful assistant for Versailles. You must answer the user's query. "
            "When necessary, you can use the provided tools to gather information. "
            "After using tools, you MUST synthesize the results and provide a final, "
            "comprehensive answer to the user. Do not just stop after calling tools. "
            "Always formulate a final response."
        )
        # ------------------------------------------

        self.agent = FunctionAgent(
            llm=self.llm,
            tools=self.tools,
            system_prompt=system_prompt,  # Utilisation du prompt amélioré
            verbose=True,
        )
        logger.info("FunctionAgent initialized.")

    def _format_chunk(self, content: str) -> str:
        """Formate un chunk pour le streaming (identique à la version corrigée)"""
        chunk = {
            "id": f"chunk-{uuid.uuid4()}",
            "object": "chat.completion.chunk",
            "created": int(datetime.now().timestamp()),
            "model": self.llm.model,
            "choices": [
                {"index": 0, "delta": {"content": content}, "finish_reason": None}
            ],
        }
        return f"data: {json.dumps(chunk)}\n\n"

    def _get_nonstream_response_template(
        self,
        response_id: str,
    ) -> str:
        """Crée un template de réponse (identique à la version corrigée)"""
        response = {
            "id": response_id,
            "object": "chat.completion",
            "created": int(datetime.now().timestamp()),
            "model": self.llm.model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [],
                    },
                    "finish_reason": None,
                }
            ],
        }
        return response

    @observe(name="chat_completion_stream")
    async def _internal_streamer(self, query) -> AsyncGenerator[str, None]:
        """Gestionnaire de streaming interne avec trace Langfuse et logging."""
        logger.info(
            f"Entering _internal_streamer for session {self.session_id} with query: '{query}'"
        )

        langfuse.update_current_trace(
            session_id=self.session_id,
            tags=[f"session:{self.session_id}", "stream"],
            metadata={
                "agent_session": self.session_id,
                "request_type": "stream",
                "timestamp": datetime.now().isoformat(),
            },
        )

        try:
            handler = self.agent.run(query)
            event_count = 0
            async for event in handler.stream_events():
                event_count += 1
                logger.debug(f"Stream Event {event_count} received: {type(event)}")

                if isinstance(event, AgentStream):
                    logger.debug(f"AgentStream delta: '{event.delta}'")
                    if event.delta is not None:  # Ne pas envoyer de chunk vide
                        yield self._format_chunk(event.delta)
                elif isinstance(event, ToolCall):
                    logger.debug(
                        f"ToolCall: {event.tool_name}, Args: {event.tool_kwargs}"
                    )
                elif isinstance(event, ToolCallResult):
                    logger.debug(
                        f"ToolCallResult for {event.tool_name}. Output: {event.tool_output.content[:100]}..."
                    )

            if event_count == 0:
                logger.warning(
                    f"No events received from a_stream_events() for query: {query}"
                )
                yield self._format_chunk(
                    "[DEBUG: No events received from agent. Check LLM or agent config.]"
                )

        except Exception as e:
            logger.error(f"Error in _internal_streamer: {e}", exc_info=True)
            error_chunk = self._format_chunk(f"An error occurred: {e}")
            yield error_chunk

    @observe(name="chat_completion_with_planner")
    async def chat_completion_with_planner(self, query: str) -> Dict[str, Any]:
        """Traite la requête avec le Query Planner (inchangé)."""
        logger.info(f"Entering chat_completion_with_planner with query: '{query}'")
        try:
            (
                analysis,
                tool_results,
                final_answer,
            ) = await self.query_planner.process_query(query)

            logger.info("Query Planner processing successful.")
            return {
                "analysis": {
                    "query_type": analysis.query_type.value,
                    "confidence": analysis.confidence,
                    "required_tools": analysis.required_tools,
                    "entities": analysis.extracted_entities,
                    "reasoning": analysis.reasoning,
                },
                "tool_results": {
                    name: {
                        "success": result.success,
                        "data": result.data,
                        "error": result.error,
                    }
                    for name, result in tool_results.items()
                },
                "final_answer": final_answer,
                "processing_method": "query_planner",
            }
        except Exception as e:
            logger.warning(
                f"Query Planner failed, falling back to original method: {e}",
                exc_info=True,
            )
            fallback_response = await self.chat_completion_non_stream(query)
            return {
                "analysis": {"error": str(e)},
                "tool_results": {},
                "final_answer": fallback_response.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "Error processing query"),
                "processing_method": "fallback",
            }

    @observe(name="chat_completion_non_stream")
    async def chat_completion_non_stream(self, query: str) -> Dict[str, Any]:
        """Traite une requête en mode non-stream avec logging."""
        logger.info(
            f"Entering chat_completion_non_stream for session {self.session_id} with query: '{query}'"
        )

        handler = self.agent.run(query)
        response = self._get_nonstream_response_template(str(uuid.uuid4()))

        has_tool_calls = False
        has_content = False
        event_count = 0

        try:
            async for event in handler.stream_events():
                event_count += 1
                logger.debug(f"Non-Stream Event {event_count} received: {type(event)}")

                if isinstance(event, AgentStream):
                    has_content = True
                    logger.debug(f"AgentStream delta: '{event.delta}'")
                    if not response["choices"][0]["message"]["content"]:
                        response["choices"][0]["message"]["content"] = event.delta
                    else:
                        response["choices"][0]["message"]["content"] += event.delta

                elif isinstance(event, ToolCall):
                    has_tool_calls = True
                    # tool_call_id = event.id_
                    logger.info(
                        f"ToolCall received: {event.tool_name} with args: {event.tool_kwargs}"
                    )
                    response["choices"][0]["message"]["tool_calls"].append(
                        {
                            "id": 1345,
                            "type": "function",
                            "function": {
                                "name": event.tool_name,
                                "arguments": json.dumps(event.tool_kwargs),
                            },
                        }
                    )

                elif isinstance(event, ToolCallResult):
                    logger.info(
                        f"ToolCallResult received for ID: (Name: {event.tool_name})"
                    )
                    for tool_call in response["choices"][0]["message"]["tool_calls"]:
                        # if tool_call["id"] == event.id_:
                        tool_call["function"]["output"] = (
                            event.tool_output.content or ""
                        )
                        logger.debug(
                            f"Tool output added to response: {event.tool_output.content[:100]}..."
                        )
                        break

        except Exception as e:
            logger.error(f"Error in chat_completion_non_stream: {e}", exc_info=True)
            response["choices"][0]["message"]["content"] = f"An error occurred: {e}"
            response["choices"][0]["finish_reason"] = "error"

        if event_count == 0:
            logger.warning(
                f"No events received from a_stream_events() for query: {query}"
            )
            if not response["choices"][0]["message"]["content"]:
                response["choices"][0]["message"]["content"] = (
                    "[DEBUG: No events received from agent. Check LLM or agent config.]"
                )

        # Définir le finish_reason final
        if has_content and not response["choices"][0]["finish_reason"]:
            response["choices"][0]["finish_reason"] = "stop"
        elif (
            has_tool_calls
            and not has_content
            and not response["choices"][0]["finish_reason"]
        ):
            response["choices"][0]["finish_reason"] = "tool_calls"
        elif not response["choices"][0]["finish_reason"]:
            response["choices"][0]["finish_reason"] = "stop"  # Par défaut

        logger.info(
            f"Non-stream processing complete. has_content: {has_content}, has_tool_calls: {has_tool_calls}, finish_reason: {response['choices'][0]['finish_reason']}"
        )
        logger.debug(f"Final non-stream response: {json.dumps(response, indent=2)}")

        return response

    def chat_completion_stream(self, query: str) -> AsyncGenerator:
        """Traite une requête en mode stream."""
        logger.debug(f"Creating stream generator for query: '{query}'")
        return self._internal_streamer(query)
