import os
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

load_dotenv()
# --- Configuration ---
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
if not MISTRAL_API_KEY:
    raise ValueError("MISTRAL_API_KEY env var is not defined.")

MISTRAL_API_BASE_URL = "https://api.mistral.ai"


# --- Client HTTP Asynchrone ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.httpx_client = httpx.AsyncClient(base_url=MISTRAL_API_BASE_URL)

    yield

    print("Fermeture du client HTTPX...")
    await app.state.httpx_client.aclose()


app = FastAPI(title="Proxy Mistral API (OpenAI-like)", lifespan=lifespan)


# --- Endpoint Proxy ---
@app.get("/")
def root():
    return "Versailles Chatbot"


@app.post("/v1/chat/completions")
async def proxy_chat_completions(request: ChatCompletionRequest):
    """
    Proxy for Mistral API
    """
    client: httpx.AsyncClient = app.state.httpx_client

    headers = {
        "Authorization": f"Bearer {MISTRAL_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",  # Ajout pour être explicite
    }

    payload = request.dict(exclude_none=True)

    try:
        if request.stream:

            async def stream_generator():
                async with client.stream(
                    "POST",
                    "/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=None,
                ) as response:
                    if response.status_code != 200:
                        error_content = await response.aread()
                        raise HTTPException(
                            status_code=response.status_code,
                            detail=error_content.decode(),
                        )

                    async for chunk in response.aiter_bytes():
                        yield chunk

            return StreamingResponse(stream_generator(), media_type="text/event-stream")

        else:
            response = await client.post(
                "/v1/chat/completions", headers=headers, json=payload, timeout=300
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code, detail=response.json()
                )

            return JSONResponse(
                content=response.json(), status_code=response.status_code
            )

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
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Erreur interne du proxy: {str(e)}"
        )


@app.post("/v1/evaluate")
async def quantitative_eval_route(request: EvalCompletionRequest):
    """
    Proxy for Mistral API
    """
    client: httpx.AsyncClient = app.state.httpx_client

    headers = {
        "Authorization": f"Bearer {MISTRAL_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",  # Ajout pour être explicite
    }

    payload = request.dict(exclude_none=True)

    try:
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
        except (KeyError, IndexError):
            raise HTTPException(
                status_code=500,
                detail="Format de réponse inattendu depuis l'API Mistral",
            )

        return {"answer": answer}

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
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Erreur interne du proxy: {str(e)}"
        )
