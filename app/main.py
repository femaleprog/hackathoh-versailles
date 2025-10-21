from app.db import get_conn, init_db

import json
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path

from typing import List
import uuid  # Import the uuid library
import httpx
from dotenv import load_dotenv
from fastapi import Body, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from llama_index.core.llms import ChatMessage as LlamaIndexChatMessage
from llama_index.core.llms import MessageRole
from fastapi.staticfiles import StaticFiles
from app.schema import (
    ChatCompletionRequest,
    ChatMessage,  # Import ChatMessage
    Conversation,  # Import new Conversation schema
    EvalCompletionAnswer,
    EvalCompletionRequest,
)
from src.agent import Agent
from src.prompts import load_prompts
from fastapi.responses import RedirectResponse

def db_get_messages(conversation_id: str):
    with get_conn() as c:
        cur = c.execute(
            "SELECT role, content FROM messages WHERE conversation_id=? ORDER BY id ASC",
            (conversation_id,)
        )
        return [dict(role=r["role"], content=r["content"]) for r in cur.fetchall()]

def db_upsert_conversation(conversation_id: str, title: str | None = None):
    with get_conn() as c:
        c.execute("""
            INSERT INTO conversations (id, title, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(id) DO UPDATE SET updated_at=CURRENT_TIMESTAMP
        """, (conversation_id, title))

def db_replace_messages(conversation_id: str, msgs: list[dict]):
    with get_conn() as c:
        c.execute("DELETE FROM messages WHERE conversation_id=?", (conversation_id,))
        c.executemany(
            "INSERT INTO messages (conversation_id, role, content) VALUES (?,?,?)",
            [(conversation_id, m["role"], m["content"]) for m in msgs]
        )
        c.execute("UPDATE conversations SET updated_at=CURRENT_TIMESTAMP WHERE id=?", (conversation_id,))

load_dotenv()

MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
SYSTEM_PROMPTS = load_prompts(
    filenames=["src/prompt_files/chat.txt", "src/prompt_files/eval.txt"]
)
# --- Personas ---
PERSONA_PROMPTS = {
    "marie_antoinette": (
        "Tu es Marie-Antoinette. Parle avec l'élégance et la politesse de la cour de Versailles (XVIIIe siècle). "
        "Emploie des tournures raffinées, vouvoie l’interlocuteur, reste claire, utile et factuelle."
    ),
    "louis_xiv": (
        "Tu es Louis XIV. Parle d’un ton solennel et assuré, avec le « nous » de majesté à l’occasion. "
        "Fais référence à l’étiquette et au devoir d’État, tout en restant concis et pratique."
    ),
}
CONVERSATION_MEMORY_FILE = "conversation_memory.json"


# --- Helper functions for JSON memory ---
# --- DB helpers for conversation list ---
def db_list_conversations():
    with get_conn() as c:
        cur = c.execute("""
            SELECT id, title, updated_at
            FROM conversations
            ORDER BY updated_at DESC
        """)
        return [dict(uuid=r["id"], title=r["title"]) for r in cur.fetchall()]


def read_memory() -> dict:
    """Reads the conversation memory from the JSON file."""

    if not os.path.exists(CONVERSATION_MEMORY_FILE):

        return {}

    with open(CONVERSATION_MEMORY_FILE, "r", encoding="utf-8") as f:

        try:

            return json.load(f)

        except json.JSONDecodeError:

            return {}

def db_delete_conversation(conversation_id: str):
    with get_conn() as c:
        # If you don't have ON DELETE CASCADE, delete messages first:
        c.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
        c.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))

def db_rename_conversation(conversation_id: str, new_title: str):
    new_title = (new_title or "").strip()
    if not new_title:
        raise ValueError("Title cannot be empty")

    with get_conn() as c:
        cur = c.execute(
            """
            UPDATE conversations
            SET title = ? WHERE id = ?
            """,
            (new_title, conversation_id),
        )
        if cur.rowcount == 0:
            # optional: create if it doesn't exist
            raise ValueError("Conversation not fousnd")


def write_memory(data: dict):
    """Writes the conversation memory to the JSON file."""

    with open(CONVERSATION_MEMORY_FILE, "w", encoding="utf-8") as f:

        json.dump(data, f, indent=2, ensure_ascii=False)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()

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
    "https://hackversailles-13-deus.ngrok.app",
    "http://192.168.1.17:5173",
    # Add any other origins you need
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Allows specific origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, OPTIONS, etc.)
    allow_headers=["*"],  # Allows all headers
)




@app.post("/v1/chat/completions")
async def proxy_chat_completions(payload: ChatCompletionRequest, request: Request):
    """
    Proxy pour l'agent LlamaIndex (avec personas)
    """
    # Session
    session_id = request.headers.get("X-Session-ID") or f"session_{int(time.time())}"

    # Persona from header/query/payload
    persona = (
        request.headers.get("X-Persona")
        or request.query_params.get("persona")
        or getattr(payload, "persona", None)
    )

    # Agent + system prompt (append persona style if any)
    agent = Agent(session_id=session_id)
    base_prompt = SYSTEM_PROMPTS["chat"]
    if persona in PERSONA_PROMPTS:
        base_prompt = base_prompt + "\n\n" + PERSONA_PROMPTS[persona]
    agent.agent.system_prompt = base_prompt

    # Extract query + build safe chat history
    try:
        query = payload.messages[-1].content
        chat_history_objects = payload.messages[:-1]
    except (AttributeError, IndexError, TypeError):
        raise HTTPException(status_code=400, detail="Payload de messages invalide.")

    chat_history_for_llamaindex = []
    for msg in chat_history_objects:
        try:
            # keep only roles supported by LlamaIndex
            if msg.role in ("user", "assistant"):
                chat_history_for_llamaindex.append(
                    LlamaIndexChatMessage(role=MessageRole(msg.role), content=msg.content)
                )
        except Exception as e:
            print(f"Skipping message due to error: {e}")

    print(f"Session {session_id} (persona={persona or 'default'}): {query}")

    try:
        if payload.stream:
            final_generator = agent.chat_completion_stream(
                query=query, chat_history=chat_history_for_llamaindex
            )
            return StreamingResponse(final_generator, media_type="text/event-stream")
        else:
            # Try Query Planner first
            try:
                planner_response = await agent.chat_completion_with_planner(query=query)
                response_content = planner_response["final_answer"]
                final_response = {
                    "id": f"cmpl-{int(time.time())}",
                    "object": "chat.completion",
                    "created": int(time.time()),
                    "model": "mistral-medium-planner",
                    "choices": [
                        {"index": 0, "message": {"role": "assistant", "content": response_content}, "finish_reason": "stop"}
                    ],
                    "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                    "query_analysis": planner_response.get("analysis", {}),
                    "tools_used": list(planner_response.get("tool_results", {}).keys()),
                    "processing_method": planner_response.get("processing_method", "query_planner"),
                    "persona": persona or "default",
                }
                return JSONResponse(content=final_response, status_code=200)
            except Exception as planner_error:
                print(f"Query Planner failed: {planner_error}")
                response = await agent.chat_completion_non_stream(query=query)
                response_content = response["choices"][0]["message"]["content"]
                final_response = {
                    "id": f"cmpl-{int(time.time())}",
                    "object": "chat.completion",
                    "created": int(time.time()),
                    "model": "mistral-medium-fallback",
                    "choices": [
                        {"index": 0, "message": {"role": "assistant", "content": response_content}, "finish_reason": "stop"}
                    ],
                    "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                    "processing_method": "fallback",
                    "planner_error": str(planner_error),
                    "persona": persona or "default",
                }
                return JSONResponse(content=final_response, status_code=200)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur interne du proxy: {str(e)}")


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
        # Use Query Planner for complete response with tool integration
        planner_response = await agent.chat_completion_with_planner(query=query)
        answer = planner_response.get("final_answer", "")

        if not answer:
            raise ValueError("No answer generated from agent")

        return EvalCompletionAnswer(answer=answer)

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Erreur interne du proxy: {str(e)}"
        )


@app.post("/chat")
async def chat_redirect(payload: EvalCompletionRequest, request: Request):
    """
    Redirect to the evaluate endpoint
    """
    return await quantitative_eval_route(payload, request)


# CONV MEMORY ENDPOINTS


@app.get("/v1/conversations", status_code=200)
async def get_conversations_list():
    return JSONResponse(content=db_list_conversations())



@app.get("/v1/conversations/{conversation_id}", status_code=200)
async def get_conversation_by_id(conversation_id: str):
    msgs = db_get_messages(conversation_id)
    if not msgs:
        raise HTTPException(status_code=404, detail="Conversation non trouvée.")
    return JSONResponse(content=msgs)

@app.post("/v1/conversations/{conversation_id}", status_code=200)
async def save_conversation(conversation_id: str, payload: List[ChatMessage] = Body(...)):
    if not payload:
        raise HTTPException(status_code=400, detail="Le contenu des messages ne peut être vide.")
    # use first user message as title (trim length)
    title = next((m.content for m in payload if m.role == "user"), "Nouvelle Conversation")[:80]
    db_upsert_conversation(conversation_id, title=title)
    db_replace_messages(conversation_id, [m.dict() for m in payload])
    return JSONResponse(content={"status": "success", "uuid": conversation_id})

@app.delete("/v1/conversations/{conversation_id}", status_code=200)
async def delete_conversation(conversation_id: str):
    try:
        db_delete_conversation(conversation_id)
        return JSONResponse({"status": "success"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
from pydantic import BaseModel

class RenamePayload(BaseModel):
    title: str

@app.patch("/v1/conversations/{conversation_id}", status_code=200)
async def rename_conversation(conversation_id: str, payload: RenamePayload):
    try:
        db_rename_conversation(conversation_id, payload.title)
        return {"status": "success"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


BASE_DIR = Path(__file__).resolve().parent.parent
SPA_DIR = BASE_DIR / "front-chat-versaille" / "dist"

if not SPA_DIR.exists():
    raise RuntimeError(f"Directory '{SPA_DIR}' does not exist")

app.mount("/", StaticFiles(directory=str(SPA_DIR), html=True), name="spa")