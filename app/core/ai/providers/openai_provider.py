"""OpenAI provider implementation"""
import asyncio
import os
from typing import Dict, Any, Optional

from app.core.logging_config import get_logger
from ..base import BaseAIProvider

logger = get_logger(__name__)
from ..models.requests import FinancialParsingRequest
from ..models.responses import (
    FinancialParsingResponse,
    FinancialData,
    CreditCardInvoiceData,
    BankStatementData
)
from app.domains.statements.ai_prompts import get_bank_statement_prompt
from app.domains.invoices.ai_prompts import get_credit_card_invoice_prompt


class OpenAIProvider(BaseAIProvider):
    """OpenAI provider for AI operations"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get("api_key") or os.getenv("OPENAI_API_KEY")
        self.default_model = config.get("model", "gpt-4o-mini-2024-07-18")
        self.client = None
        
    def _get_provider_name(self) -> str:
        return "openai"
    
    def _get_client(self):
        """Get OpenAI client, creating if needed"""
        if self.client is None:
            try:
                import openai
                if not self.api_key:
                    raise ValueError("OpenAI API key not configured")
                self.client = openai.AsyncOpenAI(api_key=self.api_key)
            except ImportError:
                raise ImportError("OpenAI library not installed. Please install: pip install openai")
        return self.client
    
    
    
    async def parse_bank_statement(self, request: FinancialParsingRequest) -> FinancialParsingResponse:
        """
        Parse BANK ACCOUNT STATEMENT ONLY using OpenAI structured outputs.
        
        NO credit card logic. NO shared conversion. Bank statements ONLY.
        """
        try:
            from ..models.responses import BankStatementData, FinancialData
            
            # Truncate text to fit context
            text = request.text[:request.max_text_length]
            
            # Get bank statement specific prompt
            system_prompt = get_bank_statement_prompt(language=request.language)
            
            # Use OpenAI structured outputs with .parse() method
            client = self._get_client()
            model_to_use = request.model or self.default_model
            logger.info(f"Parsing BANK STATEMENT with OpenAI model: {model_to_use}")
            
            # Parse with BankStatementData schema (no credit card fields!)
            response = await client.beta.chat.completions.parse(
                model=model_to_use,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Analyze this bank account statement:\n\n{text}"}
                ],
                response_format=BankStatementData,  # Bank statement schema ONLY!
                temperature=request.temperature
            )
            
            # Get the parsed Pydantic model
            parsed_message = response.choices[0].message
            
            if not parsed_message.parsed:
                return FinancialParsingResponse(
                    provider=self.provider_name,
                    model=model_to_use,
                    success=False,
                    error="OpenAI failed to parse bank statement"
                )
            
            # Get BankStatementData object
            bank_statement = parsed_message.parsed
            
            # Convert to FinancialData (legacy format for compatibility)
            financial_data = FinancialData(
                period=bank_statement.period,
                # Credit card fields (empty for bank statements)
                total_due="",
                due_date="",
                min_payment="",
                installment_options=[],
                next_due_info=None,
                # Bank statement fields
                opening_balance=bank_statement.opening_balance,
                closing_balance=bank_statement.closing_balance,
                # Common fields
                transactions=bank_statement.transactions
            )
            
            logger.info(f"✅ Bank statement parsed: {len(bank_statement.transactions)} transactions, closing={bank_statement.closing_balance}")
            
            return FinancialParsingResponse(
                provider=self.provider_name,
                model=model_to_use,
                success=True,
                data=financial_data,
                raw_response=parsed_message.content or ""
            )
                
        except Exception as e:
            logger.error(f"Bank statement parsing failed: {str(e)}")
            return FinancialParsingResponse(
                provider=self.provider_name,
                model=request.model or self.default_model,
                success=False,
                error=f"Bank statement parsing failed: {str(e)}"
            )
    
    
    async def parse_credit_card_invoice(self, request: FinancialParsingRequest) -> FinancialParsingResponse:
        """
        Parse CREDIT CARD INVOICE ONLY using OpenAI structured outputs.
        
        NO bank statement logic. NO shared conversion. Credit card invoices ONLY.
        """
        try:
            from ..models.responses import CreditCardInvoiceData, FinancialData
            
            # Truncate text to fit context
            text = request.text[:request.max_text_length]
            
            # Get credit card invoice specific prompt
            system_prompt = get_credit_card_invoice_prompt(language=request.language)
            
            # Use OpenAI structured outputs with .parse() method
            client = self._get_client()
            model_to_use = request.model or self.default_model
            logger.info(f"Parsing CREDIT CARD INVOICE with OpenAI model: {model_to_use}")
            
            # Parse with CreditCardInvoiceData schema (no bank statement fields!)
            response = await client.beta.chat.completions.parse(
                model=model_to_use,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Analyze this credit card invoice:\n\n{text}"}
                ],
                response_format=CreditCardInvoiceData,  # Credit card schema ONLY!
                temperature=request.temperature
            )
            
            # Get the parsed Pydantic model
            parsed_message = response.choices[0].message
            
            if not parsed_message.parsed:
                return FinancialParsingResponse(
                    provider=self.provider_name,
                    model=model_to_use,
                    success=False,
                    error="OpenAI failed to parse credit card invoice"
                )
            
            # Get CreditCardInvoiceData object
            invoice = parsed_message.parsed
            
            # Convert to FinancialData (legacy format for compatibility)
            financial_data = FinancialData(
                period=invoice.period,
                # Credit card fields
                total_due=invoice.total_due,
                due_date=invoice.due_date,
                min_payment=invoice.min_payment,
                installment_options=invoice.installment_options,
                next_due_info=invoice.next_due_info,
                # Bank statement fields (empty for credit cards)
                opening_balance="",
                closing_balance="",
                # Common fields
                transactions=invoice.transactions
            )
            
            logger.info(f"✅ Credit card invoice parsed: {len(invoice.transactions)} transactions, total_due={invoice.total_due}")
            
            return FinancialParsingResponse(
                provider=self.provider_name,
                model=model_to_use,
                success=True,
                data=financial_data,
                raw_response=parsed_message.content or ""
            )
                
        except Exception as e:
            logger.error(f"Credit card invoice parsing failed: {str(e)}")
            return FinancialParsingResponse(
                provider=self.provider_name,
                model=request.model or self.default_model,
                success=False,
                error=f"Credit card invoice parsing failed: {str(e)}"
            )
    
    
    async def health_check(self) -> bool:
        """Check if OpenAI API is available"""
        try:
            client = self._get_client()
            response = await client.chat.completions.create(
                model=self.default_model,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1
            )
            return bool(response.choices)
        except Exception:
            return False