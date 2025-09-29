# Fichier API (CORRIGÉ)

import json
import os
import time
from contextlib import asynccontextmanager

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from app.schema import (
    ChatCompletionRequest,
    EvalCompletionAnswer,
    EvalCompletionRequest,
)
from src.agent import Agent  # Assurez-vous que le chemin est correct

load_dotenv()

# CORRECTION : Définir la clé API globalement pour la route /evaluate
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.agent = Agent()

    # CORRECTION : Initialiser le client httpx pour la route /evaluate
    app.state.httpx_client = httpx.AsyncClient(base_url="https://api.mistral.ai")

    print("Agent et client HTTP sont prêts !")
    yield

    # CORRECTION : Fermer le client proprement
    await app.state.httpx_client.aclose()
    print("Arrêt de l'agent et du client.")


app = FastAPI(title="Proxy Mistral API (OpenAI-like)", lifespan=lifespan)


@app.get("/")
def root():
    return "Versailles Chatbot"


@app.post("/v1/chat/completions")
async def proxy_chat_completions(payload: ChatCompletionRequest, request: Request):
    """
    Proxy pour l'agent LlamaIndex
    """
    agent: Agent = request.app.state.agent

    try:
        query = payload.messages[-1].content
        print(query)
    except (AttributeError, IndexError, TypeError):
        raise HTTPException(status_code=400, detail="Payload de messages invalide.")

    try:
        if payload.stream:
            final_generator = agent.chat_completion_stream(query=query)

            return StreamingResponse(final_generator, media_type="text/event-stream")

        else:
            response = await agent.chat_completion_non_stream(query=query)
            print(response)
            response_content = response["choices"][0]["message"]["content"]
            final_response = {
                "id": f"cmpl-{int(time.time())}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": "mistral-large-agent",
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
                },  # Usage non suivi ici
            }
            return JSONResponse(content=final_response, status_code=200)

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Erreur interne du proxy: {str(e)}"
        )


@app.post("/v1/evaluate")
async def quantitative_eval_route(request: EvalCompletionRequest):
    """
    Proxy direct vers l'API Mistral (contourne l'agent)
    """
    client: httpx.AsyncClient = app.state.httpx_client

    # CORRECTION : Utiliser la variable MISTRAL_API_KEY globale
    if not MISTRAL_API_KEY:
        raise HTTPException(
            status_code=500, detail="MISTRAL_API_KEY non configurée côté serveur."
        )

    headers = {
        "Authorization": f"Bearer {MISTRAL_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    payload = request.dict(exclude_none=True)

    try:
        # Le client a déjà la base_url "https://api.mistral.ai"
        response = await client.post(
            "/v1/chat/completions", headers=headers, json=payload, timeout=300
        )

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code, detail=response.json()
            )

        try:
            data = response.json()
            answer = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            raise HTTPException(
                status_code=500,
                detail="Format de réponse inattendu depuis l'API Mistral",
            )

        return EvalCompletionAnswer(answer=answer)

    except httpx.ReadTimeout:
        raise HTTPException(
            status_code=504,
            detail="Gateway Timeout: La requête vers l'API Mistral a expiré.",
        )
    except httpx.ConnectError:
        raise HTTPException(
            status_code=502,
            detail="Bad Gateway: Impossible de se connecter à l'API Mistral.",
        )
    except HTTPException as e:
        # Re-lever les exceptions HTTP déjà formatées
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Erreur interne du proxy: {str(e)}"
        )
