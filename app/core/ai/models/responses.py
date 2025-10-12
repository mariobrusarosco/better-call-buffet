from abc import ABC
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

# Import transaction schema from transactions domain
from app.domains.transactions.schemas import TransactionData


class AIResponse(BaseModel, ABC):
    """Base class for all AI responses"""
    provider: str = Field(description="AI provider used")
    model: str = Field(description="Model used for generation")
    success: bool = Field(description="Whether the request was successful")
    error: Optional[str] = Field(default=None, description="Error message if failed")






# ============================================================================
# CREDIT CARD INVOICE MODELS (Credit card specific)
# ============================================================================

class InstallmentOption(BaseModel):
    """Credit card installment option"""
    months: int = Field(description="Number of months")
    total: str = Field(description="Total amount for installment")


class NextDueInfo(BaseModel):
    """Next payment due information for credit cards"""
    amount: str = Field(description="Next payment amount")
    balance: str = Field(description="Current balance")


class CreditCardInvoiceData(BaseModel):
    """Structured credit card invoice data"""
    total_due: str = Field(description="Total amount due on the credit card")
    due_date: str = Field(description="Payment due date")
    period: str = Field(description="Billing period")
    min_payment: str = Field(description="Minimum payment amount")
    installment_options: List[InstallmentOption] = Field(default_factory=list, description="Available installment payment options")
    transactions: List[TransactionData] = Field(default_factory=list, description="List of transactions")
    next_due_info: Optional[NextDueInfo] = Field(default=None, description="Information about next payment due")


# ============================================================================
# BANK STATEMENT MODELS (Bank account specific)
# ============================================================================

class BankStatementData(BaseModel):
    """Structured bank account statement data"""
    period: str = Field(description="Statement period (e.g., '01/01/2025 - 31/01/2025')")
    opening_balance: str = Field(default="", description="Opening balance at start of period")
    closing_balance: str = Field(description="Closing balance at end of period")
    transactions: List[TransactionData] = Field(default_factory=list, description="List of transactions with signed amounts")


# ============================================================================
# LEGACY/COMPATIBILITY MODEL (For backward compatibility)
# ============================================================================

class FinancialData(BaseModel):
    """
    Legacy financial document data model.
    
    DEPRECATED: Use CreditCardInvoiceData or BankStatementData instead.
    Kept for backward compatibility with existing code.
    """
    period: str = Field(description="Billing/statement period")
    
    # Credit card fields (optional for bank statements)
    total_due: str = Field(default="", description="Total amount due")
    due_date: str = Field(default="", description="Payment due date")
    min_payment: str = Field(default="", description="Minimum payment amount")
    installment_options: List[InstallmentOption] = Field(default_factory=list)
    next_due_info: Optional[NextDueInfo] = Field(default=None)
    
    # Bank statement fields (optional for credit cards)
    opening_balance: str = Field(default="", description="Opening balance (bank statements)")
    closing_balance: str = Field(default="", description="Closing balance (bank statements)")
    
    # Common fields
    transactions: List[TransactionData] = Field(default_factory=list)


# ============================================================================
# RESPONSE MODELS
# ============================================================================

class FinancialParsingResponse(AIResponse):
    """Response from financial document parsing"""
    data: Optional[FinancialData] = Field(default=None, description="Parsed financial data")
    raw_response: Optional[str] = Field(default=None, description="Raw AI response")


