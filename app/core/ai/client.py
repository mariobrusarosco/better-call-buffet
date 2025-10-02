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
    
    # ============================================================================
    # SPECIALIZED AI OPERATIONS - NO SHARED LOGIC
    # ============================================================================
    
    async def parse_bank_statement(
        self,
        text: str,
        language: str = "pt",
        model: Optional[str] = None,
        temperature: float = 0.3
    ) -> FinancialParsingResponse:
        """
        Parse BANK ACCOUNT STATEMENT into structured data.
        
        ONLY for bank statements - NOT for credit card invoices.
        """
        
        request = FinancialParsingRequest(
            provider=self.provider_name,
            model=model or self.config.get("model"),
            temperature=temperature,
            text=text,
            document_type="statement",  # Hardcoded for bank statements
            language=language
        )
        
        try:
            response = await self._provider.parse_bank_statement(request)
            return response
            
        except Exception as e:
            logger.error(
                "Bank statement parsing failed",
                provider=self.provider_name,
                model=request.model,
                error=str(e)
            )
            return FinancialParsingResponse(
                provider=self.provider_name,
                model=request.model,
                success=False,
                error=str(e)
            )
    
    async def parse_credit_card_invoice(
        self,
        text: str,
        language: str = "pt",
        model: Optional[str] = None,
        temperature: float = 0.3
    ) -> FinancialParsingResponse:
        """
        Parse CREDIT CARD INVOICE into structured data.
        
        ONLY for credit card invoices - NOT for bank statements.
        """
        
        request = FinancialParsingRequest(
            provider=self.provider_name,
            model=model or self.config.get("model"),
            temperature=temperature,
            text=text,
            document_type="invoice",  # Hardcoded for invoices
            language=language
        )
        
        try:
            response = await self._provider.parse_credit_card_invoice(request)
            return response
            
        except Exception as e:
            logger.error(
                "Credit card invoice parsing failed",
                provider=self.provider_name,
                model=request.model,
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
    
