from typing import List, Literal, Optional, Dict, Any

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


# RAG-related schemas
class DocumentUploadRequest(BaseModel):
    texts: List[str] = Field(..., description="List of text content to index")
    metadata: Optional[List[Dict[str, Any]]] = Field(
        None, description="Optional metadata for each text"
    )


class QueryRequest(BaseModel):
    question: str = Field(
        ..., description="Question to ask about the indexed documents"
    )
    top_k: Optional[int] = Field(
        5, description="Number of top similar documents to retrieve"
    )
    similarity_threshold: Optional[float] = Field(
        0.7, description="Minimum similarity threshold for results"
    )


class QueryResponse(BaseModel):
    status: str
    answer: Optional[str] = None
    sources: Optional[List[Dict[str, Any]]] = None
    question: Optional[str] = None
    message: Optional[str] = None


class IndexResponse(BaseModel):
    status: str
    message: str
    document_count: Optional[int] = None


class CollectionInfoResponse(BaseModel):
    status: str
    collection_name: Optional[str] = None
    points_count: Optional[int] = None
    vectors_count: Optional[int] = None
    message: Optional[str] = None


class Conversation(BaseModel):
    messages: List[ChatMessage]
