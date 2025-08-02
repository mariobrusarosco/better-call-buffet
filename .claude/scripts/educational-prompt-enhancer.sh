#!/bin/bash

# Educational Prompt Enhancer Hook
# Detects backend concepts and adds educational context

# Read the input JSON from stdin
input=$(cat)

# Extract the user's prompt from the JSON
user_prompt=$(echo "$input" | jq -r '.prompt // empty')

# Define educational trigger concepts
educational_triggers=(
    "repository pattern" "dependency injection" "cqrs" "event-driven"
    "layered architecture" "factory pattern" "strategy pattern"
    "n+1 queries" "indexing" "connection pooling" "transactions"
    "caching" "migrations" "query optimization" "sharding"
    "rest principles" "pagination" "rate limiting" "versioning"
    "status codes" "documentation" "content negotiation"
    "custom exceptions" "structured logging" "circuit breakers"
    "retry mechanisms" "health checks" "graceful degradation"
    "authentication" "authorization" "jwt" "oauth" "input validation"
    "sql injection" "cors" "secret management"
    "async processing" "load balancing" "profiling" "memory management"
    "scaling strategies" "service layer" "domain model"
)

# Check if user prompt contains educational triggers
educational_context=""
for trigger in "${educational_triggers[@]}"; do
    if echo "$user_prompt" | grep -qi "$trigger"; then
        educational_context="

🎓 EDUCATIONAL MODE ACTIVATED: This request involves '$trigger' - a key backend concept.

Please provide:
1. 📐 EXPLAIN THE WHY - Architectural reasoning behind the implementation
2. 🔄 SHOW BEFORE/AFTER - Demonstrate the transformation with concrete examples
3. 💡 LIST BENEFITS - Explain specific advantages and trade-offs
4. 🌊 SHOW DATA FLOW - Illustrate how data/errors/requests move through layers
5. 🎯 PROVIDE CONTEXT - Connect to broader backend patterns and best practices

Remember: Every code change is a teaching opportunity!"
        break
    fi
done

# Check for "LOG THE FIX" command
if echo "$user_prompt" | grep -qi "log the fix"; then
    educational_context="$educational_context

📝 LOG THE FIX DETECTED: Please create a markdown file in docs/fixing-log/ documenting:
- Context of the issue
- Root cause analysis
- Solution implemented
- Lessons learned"
fi

# Return the educational context if triggers found
if [ -n "$educational_context" ]; then
    echo "{\"context\": \"$educational_context\"}"
    exit 0
else
    exit 0
fi