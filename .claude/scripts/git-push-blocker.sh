#!/bin/bash

# Git Push Blocker Hook
# Prevents Claude from running git push commands

# Read the input JSON from stdin
input=$(cat)

# Extract the command from bash tool usage
tool_name=$(echo "$input" | jq -r '.tool // empty')
command=$(echo "$input" | jq -r '.parameters.command // empty')

# Block git push commands
if [ "$tool_name" = "Bash" ] && echo "$command" | grep -q "git push"; then
    echo "{\"blocked\": true, \"reason\": \"Git push commands are not allowed. Please push manually.\"}"
    exit 1
fi

# Allow other commands
exit 0