#!/bin/bash

# Code Standards Validator Hook
# Ensures adherence to project coding standards

# Read the input JSON from stdin
input=$(cat)

# Extract relevant information
tool_name=$(echo "$input" | jq -r '.tool // empty')
file_path=$(echo "$input" | jq -r '.parameters.file_path // empty')

validation_messages=""

# Check file naming convention (kebab-case)
if [ -n "$file_path" ] && [ "$tool_name" = "Write" ]; then
    filename=$(basename "$file_path")
    # Check if filename contains underscores or camelCase (excluding extensions)
    base_name="${filename%.*}"
    if [[ "$base_name" =~ [A-Z_] && ! "$base_name" =~ ^[a-z0-9-]+$ ]]; then
        validation_messages="$validation_messages
⚠️  FILE NAMING: Use kebab-case for file names. '$filename' should follow the pattern 'my-file-name.ext'"
    fi
fi

# Check for Git commands in bash scripts
if [ "$tool_name" = "Bash" ]; then
    command=$(echo "$input" | jq -r '.parameters.command // empty')
    if echo "$command" | grep -q "git "; then
        validation_messages="$validation_messages
⚠️  GIT COMMANDS: Avoid running git commands in automated scripts per project standards"
    fi
fi

# Check for PowerShell usage
if [ "$tool_name" = "Bash" ]; then
    command=$(echo "$input" | jq -r '.parameters.command // empty')
    if echo "$command" | grep -qi "powershell\|pwsh"; then
        validation_messages="$validation_messages
⚠️  TERMINAL: Use Git Bash instead of PowerShell per project standards"
    fi
fi

# Return validation messages if any issues found
if [ -n "$validation_messages" ]; then
    echo "{\"context\": \"$validation_messages\"}"
    exit 0
else
    exit 0
fi