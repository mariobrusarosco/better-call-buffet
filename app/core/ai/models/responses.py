from abc import ABC
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class AIResponse(BaseModel, ABC):
    """Base class for all AI responses"""
    provider: str = Field(description="AI provider used")
    model: str = Field(description="Model used for generation")
    success: bool = Field(description="Whether the request was successful")
    error: Optional[str] = Field(default=None, description="Error message if failed")


class ChatResponse(AIResponse):
    """Response from chat completion"""
    content: Optional[str] = Field(description="Generated response content")
    usage: Optional[Dict[str, int]] = Field(default=None, description="Token usage stats")
    finish_reason: Optional[str] = Field(default=None, description="Completion finish reason")


class InstallmentOption(BaseModel):
    """Credit card installment option"""
    months: int = Field(description="Number of months")
    total: str = Field(description="Total amount for installment")


class TransactionData(BaseModel):
    """Individual transaction data"""
    date: str = Field(description="Transaction date")
    description: str = Field(description="Transaction description")
    amount: str = Field(description="Transaction amount")
    category: str = Field(default="", description="Transaction category")


class NextDueInfo(BaseModel):
    """Next payment due information"""
    amount: str = Field(description="Next payment amount")
    balance: str = Field(description="Current balance")


class FinancialData(BaseModel):
    """Structured financial document data"""
    total_due: str = Field(description="Total amount due")
    due_date: str = Field(description="Payment due date")
    period: str = Field(description="Billing period")
    min_payment: str = Field(description="Minimum payment amount")
    installment_options: List[InstallmentOption] = Field(default_factory=list)
    transactions: List[TransactionData] = Field(default_factory=list)
    next_due_info: Optional[NextDueInfo] = Field(default=None)


class FinancialParsingResponse(AIResponse):
    """Response from financial document parsing"""
    data: Optional[FinancialData] = Field(default=None, description="Parsed financial data")
    raw_response: Optional[str] = Field(default=None, description="Raw AI response")


class StructuredExtractionResponse(AIResponse):
    """Response from structured data extraction"""
    extracted_data: Optional[Dict[str, Any]] = Field(default=None, description="Extracted structured data")
    confidence: Optional[float] = Field(default=None, description="Extraction confidence score")


class ClassificationResult(BaseModel):
    """Single classification result"""
    category: str = Field(description="Predicted category")
    confidence: float = Field(description="Confidence score")


class TextClassificationResponse(AIResponse):
    """Response from text classification"""
    predictions: List[ClassificationResult] = Field(default_factory=list, description="Classification results")