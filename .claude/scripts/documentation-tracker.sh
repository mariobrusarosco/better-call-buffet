#!/bin/bash

# Documentation Tracker Hook
# Ensures proper documentation practices are followed

# Read the input JSON from stdin
input=$(cat)

# Extract relevant information
tool_name=$(echo "$input" | jq -r '.tool // empty')
file_path=$(echo "$input" | jq -r '.parameters.file_path // empty')
user_prompt=$(echo "$input" | jq -r '.prompt // empty')

documentation_reminders=""

# Check for ADR creation triggers
adr_triggers=("decision" "architecture" "technology choice" "design pattern" "database schema")
for trigger in "${adr_triggers[@]}"; do
    if echo "$user_prompt" | grep -qi "$trigger"; then
        documentation_reminders="$documentation_reminders
📚 ADR REMINDER: This appears to involve an architectural decision. Consider creating an ADR in docs/decisions/ if this represents a significant technology or design choice."
        break
    fi
done

# Check for guide creation opportunities
if echo "$user_prompt" | grep -qi "how to\|guide\|tutorial\|setup"; then
    documentation_reminders="$documentation_reminders
📖 GUIDE OPPORTUNITY: Consider creating a developer guide in docs/guides/ if this involves a process that others will need to follow."
fi

# Check for phase planning
if echo "$user_prompt" | grep -qi "phase\|plan\|roadmap\|milestone"; then
    documentation_reminders="$documentation_reminders
📋 PHASE PLANNING: Consider documenting this plan in docs/plans/ with a checklist to track progress."
fi

# Check if creating files in documentation directories
if [ -n "$file_path" ]; then
    if [[ "$file_path" == *"/docs/decisions/"* ]]; then
        documentation_reminders="$documentation_reminders
✅ ADR: Creating architectural decision record - ensure it follows the template in docs/decisions/000-decision-template.md"
    elif [[ "$file_path" == *"/docs/fixing-log/"* ]]; then
        documentation_reminders="$documentation_reminders
🔧 FIX LOG: Creating fix documentation - include context, root cause, solution, and lessons learned"
    elif [[ "$file_path" == *"/docs/plans/"* ]]; then
        documentation_reminders="$documentation_reminders
📝 PHASE PLAN: Creating project phase plan - include tasks and checklist for tracking progress"
    fi
fi

# Return documentation reminders if any found
if [ -n "$documentation_reminders" ]; then
    echo "{\"context\": \"$documentation_reminders\"}"
    exit 0
else
    exit 0
fi