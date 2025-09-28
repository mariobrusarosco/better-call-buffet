from abc import ABC
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class AIRequest(BaseModel, ABC):
    """Base class for all AI requests"""
    provider: str = Field(description="AI provider name (openai, ollama)")
    model: str = Field(description="Model name to use")
    temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, gt=0)




class FinancialParsingRequest(AIRequest):
    """Request for parsing financial documents"""
    text: str = Field(description="Document text to parse")
    document_type: str = Field(description="Type of document: invoice, statement, etc.")
    language: str = Field(default="pt", description="Document language")
    max_text_length: int = Field(default=12000, description="Max text length to process")


