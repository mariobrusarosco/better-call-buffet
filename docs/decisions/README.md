# Architectural Decision Records

This directory contains the Architectural Decision Records (ADRs) for the Better Call Buffet project.

## What is an ADR?

An Architectural Decision Record is a document that captures an important architectural decision made along with its context and consequences.

## Why use ADRs?

We use ADRs to:
- Document significant decisions that affect the architecture
- Provide context and rationale for decisions
- Make the decision-making process transparent
- Help onboard new team members
- Avoid revisiting decisions without proper context

## ADR Format

Each ADR follows this format:
1. **Title and ID**: Clear title and sequential ID
2. **Status**: Current status of the decision
3. **Context**: Background and forces driving the decision
4. **Decision**: Description of the decision
5. **Alternatives**: Options that were considered
6. **Consequences**: Impact of the decision
7. **Implementation Plan**: How to implement the decision
8. **Related Documents**: Links to relevant documentation
9. **Notes**: Additional information or future considerations

## Decision Records Index

* [DR-000: Decision Template](000-decision-template.md)
* [DR-001: NAT Gateway Omission](001-nat-gateway-omission.md)
* [DR-002: IAM Permissions Model](002-iam-permissions-model.md)
* [DR-003: RDS Configuration Choices](003-rds-configuration-choices.md)

## Process for creating new ADRs

1. Copy the template: `000-decision-template.md`
2. Create a new file with the next sequential number
3. Fill in the template with details about your decision
4. Update this README to add your decision to the index
5. Submit a pull request for review

## Status Values

- **Proposed**: Decision is under consideration
- **Accepted**: Decision has been accepted and is being (or has been) implemented
- **Rejected**: Decision was considered but rejected
- **Deprecated**: Decision was once accepted but is no longer relevant
- **Superseded**: Decision has been replaced by a newer decision 