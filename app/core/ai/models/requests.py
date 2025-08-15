from abc import ABC
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class AIRequest(BaseModel, ABC):
    """Base class for all AI requests"""
    provider: str = Field(description="AI provider name (openai, ollama)")
    model: str = Field(description="Model name to use")
    temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, gt=0)


class ChatMessage(BaseModel):
    """Individual chat message"""
    role: str = Field(description="Message role: system, user, assistant")
    content: str = Field(description="Message content")


class ChatRequest(AIRequest):
    """Request for chat completion"""
    messages: List[ChatMessage] = Field(description="List of chat messages")
    response_format: Optional[Dict[str, str]] = Field(default=None)
    stream: bool = Field(default=False)


class FinancialParsingRequest(AIRequest):
    """Request for parsing financial documents"""
    text: str = Field(description="Document text to parse")
    document_type: str = Field(description="Type of document: invoice, statement, etc.")
    language: str = Field(default="pt", description="Document language")
    max_text_length: int = Field(default=12000, description="Max text length to process")


class StructuredExtractionRequest(AIRequest):
    """Request for structured data extraction"""
    text: str = Field(description="Text to extract data from")
    schema: Dict[str, Any] = Field(description="Expected output schema")
    instructions: str = Field(description="Extraction instructions")


class TextClassificationRequest(AIRequest):
    """Request for text classification"""
    text: str = Field(description="Text to classify")
    categories: List[str] = Field(description="Possible categories")
    multi_label: bool = Field(default=False, description="Allow multiple labels")