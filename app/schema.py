from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["user", "system", "assistant"]
    content: str


class ChatCompletionRequest(BaseModel):
    model: str = "mistral-medium-2508"
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None
    stream: bool = False

    class Config:
        extra = "allow"


# --- Evaluation ---
class EvalCompletionRequest(BaseModel):
    model: str = "mistral-medium-2508"
    question: str


class EvalCompletionAnswer(BaseModel):
    answer: str
