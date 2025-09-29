from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["user", "system", "assistant"]
    content: str


class ChatCompletionRequest(BaseModel):
    model: str  # ex: "mistral-small-latest", "mistral-large-latest"
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None
    stream: bool = False
    # On peut ajouter d'autres champs OpenAI si nécessaire (top_p, etc.)

    class Config:
        # Permet de capturer les champs non définis (ex: top_p)
        # et de les transférer quand même
        extra = "allow"
