"""Common prompt templates for AI operations"""
from typing import Dict, Any, List
import json


def create_extraction_prompt(schema: Dict[str, Any], instructions: str) -> str:
    """Create prompt for structured data extraction"""
    schema_str = json.dumps(schema, indent=2)
    
    return f"""
You are a data extraction assistant. Your task is to extract structured information from the provided text according to the specified schema and instructions.

INSTRUCTIONS:
{instructions}

OUTPUT SCHEMA:
The response must be a valid JSON object that follows this exact schema:
{schema_str}

IMPORTANT:
- Return ONLY valid JSON, no additional text or explanations
- If a field cannot be found, use null or empty values as appropriate for the data type
- Ensure all required fields are present in the response
- Follow the data types specified in the schema exactly
"""


def create_classification_prompt(categories: List[str], multi_label: bool = False) -> str:
    """Create prompt for text classification"""
    categories_str = ", ".join(f'"{cat}"' for cat in categories)
    
    if multi_label:
        return f"""
You are a text classification assistant. Your task is to classify the provided text into one or more of the following categories: {categories_str}.

The response must be a valid JSON object with this structure:
{{
  "predictions": [
    {{
      "category": "category_name",
      "confidence": 0.95
    }}
  ]
}}

IMPORTANT:
- Multiple categories can be assigned (multi-label classification)
- Confidence scores should be between 0.0 and 1.0
- Only include categories that are relevant to the text
- Return ONLY valid JSON, no additional text
"""
    else:
        return f"""
You are a text classification assistant. Your task is to classify the provided text into exactly ONE of the following categories: {categories_str}.

The response must be a valid JSON object with this structure:
{{
  "predictions": [
    {{
      "category": "category_name",
      "confidence": 0.95
    }}
  ]
}}

IMPORTANT:
- Select only the SINGLE most appropriate category
- Confidence score should be between 0.0 and 1.0
- Return ONLY valid JSON, no additional text
"""


def create_summarization_prompt(max_length: int = 200, style: str = "neutral") -> str:
    """Create prompt for text summarization"""
    style_instructions = {
        "neutral": "Provide a neutral, objective summary",
        "bullet": "Provide a summary in bullet point format",
        "executive": "Provide an executive summary focusing on key insights",
        "technical": "Provide a technical summary with specific details"
    }
    
    instruction = style_instructions.get(style, style_instructions["neutral"])
    
    return f"""
You are a text summarization assistant. Your task is to create a concise summary of the provided text.

REQUIREMENTS:
- {instruction}
- Maximum length: {max_length} characters
- Maintain the key information and context
- Use clear, concise language
- Focus on the most important points

Return only the summary text, no additional formatting or explanations.
"""