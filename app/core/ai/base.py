from abc import ABC, abstractmethod
from typing import Dict, Any

from .models.requests import FinancialParsingRequest
from .models.responses import FinancialParsingResponse


class BaseAIProvider(ABC):
    """Abstract base class for AI providers"""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize provider with configuration"""
        self.config = config
        self.provider_name = self._get_provider_name()
    
    @abstractmethod
    def _get_provider_name(self) -> str:
        """Return the provider name"""
        pass
    
    @abstractmethod
    async def parse_financial_document(self, request: FinancialParsingRequest) -> FinancialParsingResponse:
        """Parse financial documents into structured data"""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if provider is available"""
        pass