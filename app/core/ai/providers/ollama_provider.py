"""Ollama provider implementation"""
import asyncio
import json
from typing import Dict, Any, Optional
import httpx

from ..base import BaseAIProvider
from ..models.requests import FinancialParsingRequest
from ..models.responses import (
    FinancialParsingResponse,
    FinancialData,
    InstallmentOption,
    TransactionData,
    NextDueInfo
)
from app.domains.statements.ai_prompts import get_bank_statement_prompt
from app.domains.invoices.ai_prompts import get_credit_card_invoice_prompt


class OllamaProvider(BaseAIProvider):
    """Ollama provider for AI operations"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = config.get("base_url", "http://localhost:11434")
        self.default_model = config.get("model", "llama2")
        self.timeout = config.get("timeout", 120)  # 2 minutes default
        
    def _get_provider_name(self) -> str:
        return "ollama"
    
    
    async def parse_financial_document(self, request: FinancialParsingRequest) -> FinancialParsingResponse:
        """Parse financial documents using Ollama"""
        try:
            # Truncate text to fit context
            text = request.text[:request.max_text_length]
            
            # Get appropriate prompt from domain-specific modules
            if request.document_type == "invoice":
                system_prompt = get_credit_card_invoice_prompt(language=request.language)
            elif request.document_type == "statement":
                system_prompt = get_bank_statement_prompt(language=request.language)
            else:
                raise ValueError(f"Unsupported document_type: {request.document_type}")
            
            # Prepare request payload for direct Ollama API call
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Please analyze the following {request.document_type} text and return the information in JSON format:\n\n{text}"}
            ]
            
            payload = {
                "model": request.model or self.default_model,
                "messages": messages,
                "stream": False,
                "format": "json",
                "options": {
                    "temperature": request.temperature,
                }
            }
            
            if request.max_tokens:
                payload["options"]["num_predict"] = request.max_tokens
            
            # Make direct async HTTP request to Ollama
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json=payload
                )
                response.raise_for_status()
                
                result = response.json()
                content = result.get("message", {}).get("content", "")
                
                if not content:
                    return FinancialParsingResponse(
                        provider=self.provider_name,
                        model=request.model or self.default_model,
                        success=False,
                        error="Ollama returned empty response"
                    )
            
            # Parse JSON response
            try:
                # Clean up response - sometimes Ollama adds extra text
                content = content.strip()
                
                # Try to find JSON in the response
                start_idx = content.find('{')
                end_idx = content.rfind('}') + 1
                
                if start_idx >= 0 and end_idx > start_idx:
                    json_content = content[start_idx:end_idx]
                else:
                    json_content = content
                
                parsed_data = json.loads(json_content)
                financial_data = self._parse_financial_data(parsed_data)
                
                return FinancialParsingResponse(
                    provider=self.provider_name,
                    model=request.model or self.default_model,
                    success=True,
                    data=financial_data,
                    raw_response=content
                )
                
            except json.JSONDecodeError as e:
                return FinancialParsingResponse(
                    provider=self.provider_name,
                    model=request.model or self.default_model,
                    success=False,
                    error=f"Invalid JSON response: {str(e)}. Raw response: {content[:200]}..."
                )
                
        except Exception as e:
            return FinancialParsingResponse(
                provider=self.provider_name,
                model=request.model or self.default_model,
                success=False,
                error=f"Financial parsing failed: {str(e)}"
            )
    
    def _parse_financial_data(self, data: Dict[str, Any]) -> FinancialData:
        """Convert raw JSON to FinancialData model"""
        
        # Parse installment options
        installment_options = []
        for option in data.get("installment_options", []):
            installment_options.append(InstallmentOption(
                months=option.get("months", 0),
                total=option.get("total", "")
            ))
        
        # Parse transactions
        transactions = []
        for transaction in data.get("transactions", []):
            transactions.append(TransactionData(
                date=transaction.get("date", ""),
                description=transaction.get("description", ""),
                amount=transaction.get("amount", ""),
                movement_type=transaction.get("movement_type", "other"),
                category=transaction.get("category", "")
            ))
        
        # Parse next due info
        next_due_info = None
        if "next_due_info" in data and data["next_due_info"]:
            next_due_info = NextDueInfo(
                amount=data["next_due_info"].get("amount", ""),
                balance=data["next_due_info"].get("balance", "")
            )
        
        return FinancialData(
            total_due=data.get("total_due", ""),
            due_date=data.get("due_date", ""),
            period=data.get("period", ""),
            min_payment=data.get("min_payment", ""),
            installment_options=installment_options,
            transactions=transactions,
            next_due_info=next_due_info
        )
    
    async def health_check(self) -> bool:
        """Check if Ollama API is available"""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except Exception:
            return False
    
    async def list_models(self) -> list:
        """List available models in Ollama"""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
                result = response.json()
                return [model["name"] for model in result.get("models", [])]
        except Exception:
            return []