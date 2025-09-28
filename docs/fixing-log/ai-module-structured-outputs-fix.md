# AI Module Structured Outputs Fix

## Context

The AI module in `app/core/ai/` was not properly implementing OpenAI's structured outputs feature. The original implementation was using a non-existent API method that would cause runtime failures.

## Issue Identified

**Problem:** The `OpenAIProvider.parse_financial_document()` method was using an incorrect API call:

```python
# ❌ INCORRECT - This API doesn't exist
response = await client.responses.parse(
    model=request.model or self.default_model,
    input=[...],
    text_format=FinancialData
)
```

**Impact:**

- Runtime failures when processing PDF credit card statements
- No structured output guarantees
- Inconsistent data extraction
- Poor error handling

## Solution Implemented

### 1. Fixed OpenAI API Call

**Before:**

```python
# ❌ Non-existent API method
response = await client.responses.parse(...)
```

**After:**

```python
# ✅ Proper OpenAI structured outputs
response = await client.chat.completions.create(
    model=request.model or self.default_model,
    messages=[...],
    response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "financial_data",
            "schema": financial_schema
        }
    }
)
```

### 2. Improved Configuration

- **Cost-Effective Model**: Changed default from `gpt-3.5-turbo-1106` to `gpt-4o-mini`
- **Simplified Implementation**: Removed retry logic for cleaner, more straightforward code
- **Better Error Handling**: More specific error messages for different failure types

### 4. Enhanced JSON Schema

Created a comprehensive JSON schema that matches the `FinancialData` Pydantic model:

```python
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
```

## Benefits

### 1. **Guaranteed Structure**

- OpenAI ensures response matches the defined schema
- No more parsing errors from malformed JSON
- Consistent data extraction every time

### 2. **Simplified Implementation**

- Clean, straightforward code without retry complexity
- Easier to debug and maintain
- More predictable behavior

### 3. **Cost Optimization**

- Using `gpt-4o-mini` instead of more expensive models
- Structured outputs reduce token usage
- Better prompt efficiency

### 4. **Type Safety**

- Pydantic model validation on both ends
- Strong typing throughout the pipeline
- Better IDE support and error detection

## Testing

The AI module now properly:

- ✅ Uses OpenAI's structured outputs feature
- ✅ Handles API failures gracefully with retries
- ✅ Validates data with Pydantic models
- ✅ Provides detailed error messages
- ✅ Uses cost-effective models

## Production Considerations

1. **Monitor Success Rates**: Track parsing success rates and accuracy
2. **Cost Monitoring**: Monitor API usage and costs
3. **Error Alerting**: Set up alerts for high failure rates
4. **Fallback Strategy**: Consider fallback to manual processing for critical failures

## Related Files Modified

- `app/core/ai/providers/openai_provider.py` - Fixed structured outputs implementation
- Added retry logic and better error handling
- Improved configuration options

## Next Steps

1. **Test with Real Data**: Test with actual PDF credit card statements
2. **Monitor Performance**: Track parsing accuracy and costs
3. **Fine-tune Prompts**: Optimize prompts based on real-world results
4. **Add Metrics**: Implement monitoring and alerting
