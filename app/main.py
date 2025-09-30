import json
import os
import time
import uuid  # Import the uuid library
from contextlib import asynccontextmanager
from typing import List

import httpx
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException, Request, Body
from fastapi.responses import JSONResponse, StreamingResponse

# Make sure to reference the new schema location
from app.schema import (
    ChatCompletionRequest,
    EvalCompletionAnswer,
    EvalCompletionRequest,
    ChatMessage,  # Import ChatMessage
    Conversation,  # Import new Conversation schema
)
from src.agent import Agent
from src.prompts import load_prompts

load_dotenv()

MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
SYSTEM_PROMPTS = load_prompts(
    filenames=["src/prompt_files/chat.txt", "src/prompt_files/eval.txt"]
)
# Define path for our local JSON database
CONVERSATION_MEMORY_FILE = "conversation_memory.json"


# --- Helper functions for JSON memory ---
def read_memory() -> dict:
    """Reads the conversation memory from the JSON file."""
    if not os.path.exists(CONVERSATION_MEMORY_FILE):
        return {}
    with open(CONVERSATION_MEMORY_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}


def write_memory(data: dict):
    """Writes the conversation memory to the JSON file."""
    with open(CONVERSATION_MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.agent = Agent()
    app.state.httpx_client = httpx.AsyncClient(base_url="https://api.mistral.ai")
    print("Agent et client HTTP sont prêts !")
    yield
    await app.state.httpx_client.aclose()
    print("Arrêt de l'agent et du client.")


app = FastAPI(title="Proxy Mistral API (OpenAI-like)", lifespan=lifespan)

origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return "Versailles Chatbot"


@app.post("/v1/chat/completions")
async def proxy_chat_completions(payload: ChatCompletionRequest, request: Request):
    """
    Proxy pour l'agent LlamaIndex
    """
    session_id = request.headers.get("X-Session-ID") or f"session_{int(time.time())}"
    agent = Agent(session_id=session_id)
    agent.agent.system_prompt = SYSTEM_PROMPTS["chat"]

    try:
        query = payload.messages[-1].content
        print(f"Session {session_id}: {query}")
    except (AttributeError, IndexError, TypeError):
        raise HTTPException(status_code=400, detail="Payload de messages invalide.")

    try:
        if payload.stream:
            final_generator = agent.chat_completion_stream(
                query=query, chat_history=payload.messages[:-1]
            )
            return StreamingResponse(final_generator, media_type="text/event-stream")
        else:
            # Non-streaming logic remains the same
            try:
                planner_response = await agent.chat_completion_with_planner(query=query)
                print(f"Query Planner Response: {planner_response}")

                response_content = planner_response["final_answer"]
                final_response = {
                    "id": f"cmpl-{int(time.time())}",
                    "object": "chat.completion",
                    "created": int(time.time()),
                    "model": "mistral-medium-planner",
                    "choices": [
                        {
                            "index": 0,
                            "message": {
                                "role": "assistant",
                                "content": response_content,
                            },
                            "finish_reason": "stop",
                        }
                    ],
                    "usage": {
                        "prompt_tokens": 0,
                        "completion_tokens": 0,
                        "total_tokens": 0,
                    },
                    "query_analysis": planner_response.get("analysis", {}),
                    "tools_used": list(planner_response.get("tool_results", {}).keys()),
                    "processing_method": planner_response.get(
                        "processing_method", "query_planner"
                    ),
                }
                return JSONResponse(content=final_response, status_code=200)

            except Exception as planner_error:
                print(f"Query Planner failed: {planner_error}")
                # Fallback to original method
                response = await agent.chat_completion_non_stream(query=query)
                print(response)
                response_content = response["choices"][0]["message"]["content"]
                final_response = {
                    "id": f"cmpl-{int(time.time())}",
                    "object": "chat.completion",
                    "created": int(time.time()),
                    "model": "mistral-large-planner",
                    "choices": [
                        {
                            "index": 0,
                            "message": {
                                "role": "assistant",
                                "content": response_content,
                            },
                            "finish_reason": "stop",
                        }
                    ],
                    "usage": {
                        "prompt_tokens": 0,
                        "completion_tokens": 0,
                        "total_tokens": 0,
                    },
                    "processing_method": "fallback",
                    "planner_error": str(planner_error),
                }
                return JSONResponse(content=final_response, status_code=200)

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Erreur interne du proxy: {str(e)}"
        )


@app.post("/v1/evaluate")
async def quantitative_eval_route(payload: EvalCompletionRequest, request: Request):
    """
    Proxy direct vers l'API Mistral (contourne l'agent)
    """
    session_id = (
        request.headers.get("X-Session-ID") or f"eval_session_{int(time.time())}"
    )

    agent = Agent(session_id=session_id)
    agent.agent.system_prompt = SYSTEM_PROMPTS["eval"]
    query = payload.question

    try:
        response = await agent.chat_completion_non_stream(query=query)
        answer = response["choices"][0]["message"]["content"]
        return EvalCompletionAnswer(answer=answer)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Erreur interne du proxy: {str(e)}"
        )


# CONV MEMORY ENDPOINTS


@app.get("/v1/conversations", status_code=200)
async def get_conversations_list():
    """Returns a list of all conversation IDs and their first user message."""
    memory = read_memory()
    conv_list = []
    for conv_id, data in memory.items():
        first_message = "Nouvelle Conversation"
        # Find the first user message for a better title
        if data.get("messages"):
            for msg in data["messages"]:
                if msg.get("role") == "user":
                    first_message = msg.get("content", first_message)
                    break
        conv_list.append({"uuid": conv_id, "title": first_message})
    return JSONResponse(content=conv_list)


@app.get("/v1/conversations/{conversation_id}", status_code=200)
async def get_conversation_by_id(conversation_id: str):
    """Returns the full message history for a given conversation UUID."""
    memory = read_memory()
    conversation = memory.get(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation non trouvée.")
    return JSONResponse(content=conversation.get("messages", []))


@app.post("/v1/conversations/{conversation_id}", status_code=200)
async def save_conversation(conversation_id: str, payload: List[ChatMessage]):
    """Saves or updates the message history for a given conversation UUID."""
    if not payload:
        raise HTTPException(
            status_code=400, detail="Le contenu des messages ne peut être vide."
        )

    memory = read_memory()
    memory[conversation_id] = {"messages": [msg.dict() for msg in payload]}
    write_memory(memory)
    return JSONResponse(content={"status": "success", "uuid": conversation_id})
