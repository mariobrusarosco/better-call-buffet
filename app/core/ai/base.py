from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

from .models.requests import (
    ChatRequest, 
    FinancialParsingRequest, 
    StructuredExtractionRequest, 
    TextClassificationRequest
)
from .models.responses import (
    ChatResponse, 
    FinancialParsingResponse, 
    StructuredExtractionResponse, 
    TextClassificationResponse
)


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
    async def chat_completion(self, request: ChatRequest) -> ChatResponse:
        """Generate chat completion"""
        pass
    
    @abstractmethod
    async def parse_financial_document(self, request: FinancialParsingRequest) -> FinancialParsingResponse:
        """Parse financial documents into structured data"""
        pass
    
    async def structured_extraction(self, request: StructuredExtractionRequest) -> StructuredExtractionResponse:
        """Extract structured data from text (default implementation using chat)"""
        # Most providers can implement this using chat completion
        # Override if provider has specialized structured extraction
        from .prompts.common import create_extraction_prompt
        
        chat_request = ChatRequest(
            provider=request.provider,
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            messages=[
                {"role": "system", "content": create_extraction_prompt(request.schema, request.instructions)},
                {"role": "user", "content": request.text}
            ],
            response_format={"type": "json_object"} if self._supports_json_mode() else None
        )
        
        chat_response = await self.chat_completion(chat_request)
        
        if not chat_response.success:
            return StructuredExtractionResponse(
                provider=self.provider_name,
                model=request.model,
                success=False,
                error=chat_response.error
            )
        
        try:
            import json
            extracted_data = json.loads(chat_response.content) if chat_response.content else None
            return StructuredExtractionResponse(
                provider=self.provider_name,
                model=request.model,
                success=True,
                extracted_data=extracted_data
            )
        except json.JSONDecodeError as e:
            return StructuredExtractionResponse(
                provider=self.provider_name,
                model=request.model,
                success=False,
                error=f"Invalid JSON response: {str(e)}"
            )
    
    async def text_classification(self, request: TextClassificationRequest) -> TextClassificationResponse:
        """Classify text into categories (default implementation using chat)"""
        from .prompts.common import create_classification_prompt
        
        chat_request = ChatRequest(
            provider=request.provider,
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            messages=[
                {"role": "system", "content": create_classification_prompt(request.categories, request.multi_label)},
                {"role": "user", "content": request.text}
            ],
            response_format={"type": "json_object"} if self._supports_json_mode() else None
        )
        
        chat_response = await self.chat_completion(chat_request)
        
        if not chat_response.success:
            return TextClassificationResponse(
                provider=self.provider_name,
                model=request.model,
                success=False,
                error=chat_response.error
            )
        
        try:
            import json
            from .models.responses import ClassificationResult
            
            result = json.loads(chat_response.content) if chat_response.content else {}
            predictions = []
            
            if "predictions" in result:
                for pred in result["predictions"]:
                    predictions.append(ClassificationResult(
                        category=pred.get("category", ""),
                        confidence=pred.get("confidence", 0.0)
                    ))
            
            return TextClassificationResponse(
                provider=self.provider_name,
                model=request.model,
                success=True,
                predictions=predictions
            )
        except (json.JSONDecodeError, KeyError) as e:
            return TextClassificationResponse(
                provider=self.provider_name,
                model=request.model,
                success=False,
                error=f"Invalid classification response: {str(e)}"
            )
    
    def _supports_json_mode(self) -> bool:
        """Check if provider supports JSON mode"""
        # Override in provider implementations
        return False
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if provider is available"""
        pass