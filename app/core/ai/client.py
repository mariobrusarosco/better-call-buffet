"""Main AI client factory and interface"""
from typing import Dict, Any, Optional, Union
import structlog

from .base import BaseAIProvider
from .providers import OpenAIProvider, OllamaProvider
from .models.requests import (
    ChatRequest, 
    FinancialParsingRequest, 
    StructuredExtractionRequest, 
    TextClassificationRequest,
    ChatMessage
)
from .models.responses import (
    ChatResponse, 
    FinancialParsingResponse, 
    StructuredExtractionResponse, 
    TextClassificationResponse
)


logger = structlog.get_logger(__name__)


class AIClient:
    """Main AI client that provides a unified interface to multiple AI providers"""
    
    def __init__(self, provider: str, config: Dict[str, Any]):
        """
        Initialize AI client with specified provider
        
        Args:
            provider: Provider name ("openai" or "ollama")
            config: Provider-specific configuration
        """
        self.provider_name = provider
        self.config = config
        self._provider = self._create_provider(provider, config)
        
        logger.info(
            "AI client initialized",
            provider=provider,
            model=config.get("model", "default")
        )
    
    def _create_provider(self, provider: str, config: Dict[str, Any]) -> BaseAIProvider:
        """Create provider instance based on provider name"""
        providers = {
            "openai": OpenAIProvider,
            "ollama": OllamaProvider
        }
        
        if provider not in providers:
            raise ValueError(f"Unsupported AI provider: {provider}. Available: {list(providers.keys())}")
        
        return providers[provider](config)
    
    @classmethod
    def from_config(cls, ai_config: Dict[str, Any]) -> "AIClient":
        """Create AI client from configuration dictionary"""
        provider = ai_config.get("provider", "openai")
        return cls(provider, ai_config)
    
    async def health_check(self) -> bool:
        """Check if AI provider is available and healthy"""
        try:
            return await self._provider.health_check()
        except Exception as e:
            logger.error("AI health check failed", error=str(e), provider=self.provider_name)
            return False
    
    # Core AI Operations
    
    async def chat_completion(
        self, 
        messages: Union[list, str], 
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, str]] = None
    ) -> ChatResponse:
        """Generate chat completion"""
        
        # Convert simple string to messages format
        if isinstance(messages, str):
            messages = [ChatMessage(role="user", content=messages)]
        elif isinstance(messages, list) and messages and isinstance(messages[0], dict):
            messages = [ChatMessage(role=msg["role"], content=msg["content"]) for msg in messages]
        
        request = ChatRequest(
            provider=self.provider_name,
            model=model or self.config.get("model"),
            temperature=temperature,
            max_tokens=max_tokens,
            messages=messages,
            response_format=response_format
        )
        
        try:
            response = await self._provider.chat_completion(request)
            
            logger.info(
                "Chat completion completed",
                provider=self.provider_name,
                model=request.model,
                success=response.success,
                usage=response.usage if hasattr(response, 'usage') else None
            )
            
            return response
            
        except Exception as e:
            logger.error(
                "Chat completion failed",
                provider=self.provider_name,
                model=request.model,
                error=str(e)
            )
            return ChatResponse(
                provider=self.provider_name,
                model=request.model,
                success=False,
                error=str(e)
            )
    
    async def parse_financial_document(
        self,
        text: str,
        document_type: str = "statement",
        language: str = "pt",
        model: Optional[str] = None,
        temperature: float = 0.3
    ) -> FinancialParsingResponse:
        """Parse financial documents into structured data"""
        
        request = FinancialParsingRequest(
            provider=self.provider_name,
            model=model or self.config.get("model"),
            temperature=temperature,
            text=text,
            document_type=document_type,
            language=language
        )
        
        try:
            response = await self._provider.parse_financial_document(request)
            
            logger.info(
                "Financial document parsing completed",
                provider=self.provider_name,
                model=request.model,
                document_type=document_type,
                success=response.success,
                transaction_count=len(response.data.transactions) if response.data else 0
            )
            
            return response
            
        except Exception as e:
            logger.error(
                "Financial document parsing failed",
                provider=self.provider_name,
                model=request.model,
                document_type=document_type,
                error=str(e)
            )
            return FinancialParsingResponse(
                provider=self.provider_name,
                model=request.model,
                success=False,
                error=str(e)
            )
    
    async def structured_extraction(
        self,
        text: str,
        schema: Dict[str, Any],
        instructions: str,
        model: Optional[str] = None,
        temperature: float = 0.3
    ) -> StructuredExtractionResponse:
        """Extract structured data from text"""
        
        request = StructuredExtractionRequest(
            provider=self.provider_name,
            model=model or self.config.get("model"),
            temperature=temperature,
            text=text,
            schema=schema,
            instructions=instructions
        )
        
        try:
            response = await self._provider.structured_extraction(request)
            
            logger.info(
                "Structured extraction completed",
                provider=self.provider_name,
                model=request.model,
                success=response.success
            )
            
            return response
            
        except Exception as e:
            logger.error(
                "Structured extraction failed",
                provider=self.provider_name,
                model=request.model,
                error=str(e)
            )
            return StructuredExtractionResponse(
                provider=self.provider_name,
                model=request.model,
                success=False,
                error=str(e)
            )
    
    async def text_classification(
        self,
        text: str,
        categories: list,
        multi_label: bool = False,
        model: Optional[str] = None,
        temperature: float = 0.3
    ) -> TextClassificationResponse:
        """Classify text into categories"""
        
        request = TextClassificationRequest(
            provider=self.provider_name,
            model=model or self.config.get("model"),
            temperature=temperature,
            text=text,
            categories=categories,
            multi_label=multi_label
        )
        
        try:
            response = await self._provider.text_classification(request)
            
            logger.info(
                "Text classification completed",
                provider=self.provider_name,
                model=request.model,
                success=response.success,
                prediction_count=len(response.predictions) if response.predictions else 0
            )
            
            return response
            
        except Exception as e:
            logger.error(
                "Text classification failed",
                provider=self.provider_name,
                model=request.model,
                error=str(e)
            )
            return TextClassificationResponse(
                provider=self.provider_name,
                model=request.model,
                success=False,
                error=str(e)
            )
    
    # Convenience methods for common operations
    
    async def ask(self, question: str, model: Optional[str] = None) -> str:
        """Simple question answering (returns just the text response)"""
        response = await self.chat_completion(question, model=model)
        return response.content if response.success else f"Error: {response.error}"
    
    async def parse_nubank_statement(self, text: str, model: Optional[str] = None) -> FinancialParsingResponse:
        """Parse Nubank credit card statement (convenience method)"""
        return await self.parse_financial_document(
            text=text,
            document_type="statement",
            language="pt",
            model=model
        )
    
    async def parse_invoice(self, text: str, model: Optional[str] = None) -> FinancialParsingResponse:
        """Parse invoice document (convenience method)"""
        return await self.parse_financial_document(
            text=text,
            document_type="invoice",
            language="pt",
            model=model
        )
    
    # Provider-specific methods
    
    def get_provider_info(self) -> Dict[str, Any]:
        """Get information about the current provider"""
        return {
            "provider": self.provider_name,
            "config": self.config,
            "supports_json_mode": self._provider._supports_json_mode()
        }
    
    async def list_available_models(self) -> list:
        """List available models (if supported by provider)"""
        if hasattr(self._provider, 'list_models'):
            return await self._provider.list_models()
        return []