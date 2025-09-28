"""Main AI client factory and interface"""
from typing import Dict, Any, Optional, Union
import structlog

from .base import BaseAIProvider
from .providers import OpenAIProvider, OllamaProvider
from .models.requests import FinancialParsingRequest
from .models.responses import FinancialParsingResponse


logger = structlog.get_logger(__name__)


class AIClient:
    def __init__(self, provider: str, config: Dict[str, Any]):
        self.provider_name = provider
        self.config = config
        self._provider = self._create_provider(provider, config)
    
    def _create_provider(self, provider: str, config: Dict[str, Any]) -> BaseAIProvider:
        providers = {
            "openai": OpenAIProvider,
            "ollama": OllamaProvider
        }
        
        if provider not in providers:
            raise ValueError(f"Unsupported AI provider: {provider}. Available: {list(providers.keys())}")
        
        return providers[provider](config)
    
    @classmethod
    def from_config(cls, ai_config: Dict[str, Any]) -> "AIClient":
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
    
    
    # Provider-specific methods
    def get_provider_info(self) -> Dict[str, Any]:
        return {
            "provider": self.provider_name,
            "config": self.config
        }
    
