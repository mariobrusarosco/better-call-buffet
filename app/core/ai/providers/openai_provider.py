"""OpenAI provider implementation"""
import asyncio
import json
import os
from typing import Dict, Any, Optional

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


class OpenAIProvider(BaseAIProvider):
    """OpenAI provider for AI operations"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get("api_key") or os.getenv("OPENAI_API_KEY")
        self.default_model = config.get("model", "gpt-3.5-turbo-1106")
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
                self.client = openai.OpenAI(api_key=self.api_key)
            except ImportError:
                raise ImportError("OpenAI library not installed. Please install: pip install openai")
        return self.client
    
    def _supports_json_mode(self) -> bool:
        """OpenAI supports JSON mode"""
        return True
    
    async def chat_completion(self, request: ChatRequest) -> ChatResponse:
        """Generate chat completion using OpenAI"""
        try:
            client = self._get_client()
            
            # Convert ChatMessage objects to dict format
            messages = []
            for msg in request.messages:
                if isinstance(msg, ChatMessage):
                    messages.append({"role": msg.role, "content": msg.content})
                else:
                    messages.append(msg)
            
            # Prepare request parameters
            params = {
                "model": request.model or self.default_model,
                "messages": messages,
                "temperature": request.temperature,
            }
            
            if request.max_tokens:
                params["max_tokens"] = request.max_tokens
                
            if request.response_format:
                params["response_format"] = request.response_format
            
            # Make async call to OpenAI
            response = await asyncio.to_thread(
                client.chat.completions.create,
                **params
            )
            
            content = response.choices[0].message.content if response.choices else None
            usage = {
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0
            } if response.usage else None
            
            return ChatResponse(
                provider=self.provider_name,
                model=params["model"],
                success=True,
                content=content,
                usage=usage,
                finish_reason=response.choices[0].finish_reason if response.choices else None
            )
            
        except Exception as e:
            return ChatResponse(
                provider=self.provider_name,
                model=request.model or self.default_model,
                success=False,
                error=str(e)
            )
    
    async def parse_financial_document(self, request: FinancialParsingRequest) -> FinancialParsingResponse:
        """Parse financial documents using OpenAI"""
        try:
            # Truncate text to fit context
            text = request.text[:request.max_text_length]
            
            # Get appropriate prompt
            system_prompt = get_financial_parsing_prompt(
                document_type=request.document_type,
                language=request.language
            )
            
            # Create chat request
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
                    error="OpenAI returned empty response"
                )
            
            # Parse JSON response
            try:
                parsed_data = json.loads(chat_response.content)
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
                    error=f"Invalid JSON response: {str(e)}"
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
        """Check if OpenAI API is available"""
        try:
            chat_request = ChatRequest(
                provider=self.provider_name,
                model=self.default_model,
                temperature=0.1,
                messages=[ChatMessage(role="user", content="Hello")]
            )
            
            response = await self.chat_completion(chat_request)
            return response.success
            
        except Exception:
            return False