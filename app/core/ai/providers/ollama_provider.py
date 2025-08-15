"""Ollama provider implementation"""
import asyncio
import json
from typing import Dict, Any, Optional
import httpx

from ..base import BaseAIProvider
from ..models.requests import (
    ChatRequest, 
    FinancialParsingRequest, 
    ChatMessage
)
from ..models.responses import (
    ChatResponse, 
    FinancialParsingResponse,
    FinancialData,
    InstallmentOption,
    TransactionData,
    NextDueInfo
)
from ..prompts.financial_parsing import get_financial_parsing_prompt


class OllamaProvider(BaseAIProvider):
    """Ollama provider for AI operations"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = config.get("base_url", "http://localhost:11434")
        self.default_model = config.get("model", "llama2")
        self.timeout = config.get("timeout", 120)  # 2 minutes default
        
    def _get_provider_name(self) -> str:
        return "ollama"
    
    def _supports_json_mode(self) -> bool:
        """Ollama supports JSON through format parameter"""
        return True
    
    async def chat_completion(self, request: ChatRequest) -> ChatResponse:
        """Generate chat completion using Ollama"""
        try:
            # Convert ChatMessage objects to dict format
            messages = []
            for msg in request.messages:
                if isinstance(msg, ChatMessage):
                    messages.append({"role": msg.role, "content": msg.content})
                else:
                    messages.append(msg)
            
            # Prepare request payload
            payload = {
                "model": request.model or self.default_model,
                "messages": messages,
                "stream": False,  # We want complete responses
                "options": {
                    "temperature": request.temperature,
                }
            }
            
            if request.max_tokens:
                payload["options"]["num_predict"] = request.max_tokens
            
            # Add JSON format if requested
            if request.response_format and request.response_format.get("type") == "json_object":
                payload["format"] = "json"
            
            # Make async HTTP request to Ollama
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json=payload
                )
                response.raise_for_status()
                
                result = response.json()
                content = result.get("message", {}).get("content", "")
                
                return ChatResponse(
                    provider=self.provider_name,
                    model=payload["model"],
                    success=True,
                    content=content,
                    finish_reason=result.get("done_reason")
                )
                
        except httpx.TimeoutException:
            return ChatResponse(
                provider=self.provider_name,
                model=request.model or self.default_model,
                success=False,
                error="Request timeout - Ollama may be slow or unavailable"
            )
        except httpx.HTTPStatusError as e:
            return ChatResponse(
                provider=self.provider_name,
                model=request.model or self.default_model,
                success=False,
                error=f"HTTP error: {e.response.status_code} - {e.response.text}"
            )
        except Exception as e:
            return ChatResponse(
                provider=self.provider_name,
                model=request.model or self.default_model,
                success=False,
                error=str(e)
            )
    
    async def parse_financial_document(self, request: FinancialParsingRequest) -> FinancialParsingResponse:
        """Parse financial documents using Ollama"""
        try:
            # Truncate text to fit context
            text = request.text[:request.max_text_length]
            
            # Get appropriate prompt
            system_prompt = get_financial_parsing_prompt(
                document_type=request.document_type,
                language=request.language
            )
            
            # Create chat request with JSON format
            chat_request = ChatRequest(
                provider=self.provider_name,
                model=request.model or self.default_model,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                messages=[
                    ChatMessage(role="system", content=system_prompt),
                    ChatMessage(
                        role="user", 
                        content=f"Please analyze the following {request.document_type} text and return the information in JSON format:\n\n{text}"
                    )
                ],
                response_format={"type": "json_object"}
            )
            
            # Get response from chat completion
            chat_response = await self.chat_completion(chat_request)
            
            if not chat_response.success:
                return FinancialParsingResponse(
                    provider=self.provider_name,
                    model=request.model or self.default_model,
                    success=False,
                    error=chat_response.error
                )
            
            if not chat_response.content:
                return FinancialParsingResponse(
                    provider=self.provider_name,
                    model=request.model or self.default_model,
                    success=False,
                    error="Ollama returned empty response"
                )
            
            # Parse JSON response
            try:
                # Clean up response - sometimes Ollama adds extra text
                content = chat_response.content.strip()
                
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
                    raw_response=chat_response.content
                )
                
            except json.JSONDecodeError as e:
                return FinancialParsingResponse(
                    provider=self.provider_name,
                    model=request.model or self.default_model,
                    success=False,
                    error=f"Invalid JSON response: {str(e)}. Raw response: {chat_response.content[:200]}..."
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