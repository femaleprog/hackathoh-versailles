import json
import os
import time
from contextlib import asynccontextmanager

import httpx
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from app.schema import (
    ChatCompletionRequest,
    EvalCompletionAnswer,
    EvalCompletionRequest,
)
from src.agent import Agent
from src.prompts import load_prompts

load_dotenv()

MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
SYSTEM_PROMPTS = load_prompts(
    filenames=["src/prompt_files/chat.txt", "src/prompt_files/eval.txt"]
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.agent = Agent()

    app.state.httpx_client = httpx.AsyncClient(base_url="https://api.mistral.ai")

    print("Agent et client HTTP sont prêts !")
    yield

    await app.state.httpx_client.aclose()
    print("Arrêt de l'agent et du client.")


app = FastAPI(title="Proxy Mistral API (OpenAI-like)", lifespan=lifespan)


origins = [
    "http://localhost:5173",  # Default Vue dev server port
    "http://127.0.0.1:5173",
    # Add any other origins you need
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Allows specific origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, OPTIONS, etc.)
    allow_headers=["*"],  # Allows all headers
)


@app.get("/")
def root():
    return "Versailles Chatbot"


@app.post("/v1/chat/completions")
async def proxy_chat_completions(payload: ChatCompletionRequest, request: Request):
    """
    Proxy pour l'agent LlamaIndex
    """
    # Create a new session ID for each request
    session_id = request.headers.get("X-Session-ID") or f"session_{int(time.time())}"

    # Create a new agent instance for this session
    agent = Agent(session_id=session_id)
    agent.agent.system_prompt = SYSTEM_PROMPTS["chat"]

    try:
        query = payload.messages[-1].content
        print(f"Session {session_id}: {query}")
    except (AttributeError, IndexError, TypeError):
        raise HTTPException(status_code=400, detail="Payload de messages invalide.")

    try:
        if payload.stream:  # STREAMING HANDLING
            final_generator = agent.chat_completion_stream(query=query)

            return StreamingResponse(final_generator, media_type="text/event-stream")

        else:  # NON STREAM HANDLING - Use Query Planner
            # Try Query Planner first
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
                    "processing_method": planner_response.get("processing_method", "query_planner")
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
                    "model": "mistral-medium-fallback",
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
                    "planner_error": str(planner_error)
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
    # Create a new session ID for evaluation requests
    session_id = (
        request.headers.get("X-Session-ID") or f"eval_session_{int(time.time())}"
    )

    # Create a new agent instance for this evaluation session
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
