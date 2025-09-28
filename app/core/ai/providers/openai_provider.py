"""OpenAI provider implementation"""
import asyncio
import json
import os
from typing import Dict, Any, Optional

from app.core.logging_config import get_logger
from ..base import BaseAIProvider

logger = get_logger(__name__)
from ..models.requests import FinancialParsingRequest
from ..models.responses import (
    FinancialParsingResponse,
    FinancialData,
    InstallmentOption,
    TransactionData,
    NextDueInfo
)
from ..prompts.financial_parsing import get_financial_parsing_prompt


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
    
    
    
    async def parse_financial_document(self, request: FinancialParsingRequest) -> FinancialParsingResponse:
        """Parse financial documents using OpenAI structured outputs"""
        try:
            from ..models.responses import FinancialData
            
            # Truncate text to fit context
            text = request.text[:request.max_text_length]
            
            # Get appropriate prompt  
            system_prompt = get_financial_parsing_prompt(
                document_type=request.document_type,
                language=request.language
            )
            
            # Define JSON schema for structured outputs
            financial_schema = {
                "type": "object",
                "properties": {
                    "total_due": {"type": "string", "description": "Total amount due"},
                    "due_date": {"type": "string", "description": "Payment due date"},
                    "period": {"type": "string", "description": "Billing period"},
                    "min_payment": {"type": "string", "description": "Minimum payment amount"},
                    "installment_options": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "months": {"type": "integer", "description": "Number of months"},
                                "total": {"type": "string", "description": "Total amount for installment"}
                            },
                            "required": ["months", "total"]
                        }
                    },
                    "transactions": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "date": {"type": "string", "description": "Transaction date"},
                                "description": {"type": "string", "description": "Transaction description"},
                                "amount": {"type": "string", "description": "Transaction amount"},
                                "category": {"type": "string", "description": "Transaction category"}
                            },
                            "required": ["date", "description", "amount", "category"]
                        }
                    },
                    "next_due_info": {
                        "type": "object",
                        "properties": {
                            "amount": {"type": "string", "description": "Next payment amount"},
                            "balance": {"type": "string", "description": "Current balance"}
                        }
                    }
                },
                "required": ["total_due", "due_date", "period", "min_payment", "transactions"]
            }
            
            # Use OpenAI structured outputs with proper API call
            client = self._get_client()
            model_to_use = request.model or self.default_model
            logger.info(f"Using OpenAI model: {model_to_use}")
            response = await client.chat.completions.create(
                model=model_to_use,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Analyze this {request.document_type}:\n\n{text}"}
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "financial_data",
                        "schema": financial_schema
                    }
                },
                temperature=request.temperature
            )
            
            # Extract and parse the structured response
            content = response.choices[0].message.content
            if not content:
                return FinancialParsingResponse(
                    provider=self.provider_name,
                    model=request.model or self.default_model,
                    success=False,
                    error="No content returned from OpenAI"
                )
            
            # Parse JSON response into Pydantic model
            try:
                import json
                parsed_json = json.loads(content)
                financial_data = FinancialData(**parsed_json)
            except (json.JSONDecodeError, ValueError) as e:
                return FinancialParsingResponse(
                    provider=self.provider_name,
                    model=request.model or self.default_model,
                    success=False,
                    error=f"Failed to parse structured response: {str(e)}"
                )
            
            return FinancialParsingResponse(
                provider=self.provider_name,
                model=request.model or self.default_model,
                success=True,
                data=financial_data,
                raw_response=content
            )
                
        except Exception as e:
            return FinancialParsingResponse(
                provider=self.provider_name,
                model=request.model or self.default_model,
                success=False,
                error=f"Financial parsing failed: {str(e)}"
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