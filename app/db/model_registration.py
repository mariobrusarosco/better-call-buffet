"""
Model Registration for Alembic Auto-Discovery

This module ensures all SQLAlchemy models are imported so Alembic can
detect them for automatic migration generation.

🎓 PROFESSIONAL PATTERN: Centralized Model Registration
- All domain models are imported here in one place
- Alembic imports this module to discover all models automatically
- When you add a new domain, just add the import here
- No need to manually update migrations/env.py anymore
"""

from app.db.connection_and_session import Base

# Import all domain models for Alembic auto-discovery
from app.domains.accounts.models import Account
from app.domains.balance_points.models import BalancePoint
from app.domains.brokers.models import Broker
from app.domains.credit_cards.models import CreditCard
from app.domains.invoices.models import Invoice
from app.domains.refresh_tokens.models import RefreshToken
from app.domains.statements.models import Statement
from app.domains.transactions.models import Transaction
from app.domains.users.models import User
from app.domains.categories.models import UserCategory


# Optional: Validate all models are properly registered
def get_registered_models():
    """Return list of all registered model names for debugging"""
    return [table.name for table in Base.metadata.tables.values()]


def validate_model_registration():
    """Validate that all expected models are registered"""
    expected_tables = {
        "users",
        "accounts",
        "brokers",
        "credit_cards",
        "invoices",
        "statements",
        "transactions",
        "balance_points",
        "refresh_tokens",
        "user_categories",
    }
    registered_tables = set(get_registered_models())

    missing = expected_tables - registered_tables
    if missing:
        raise RuntimeError(f"Missing model registrations: {missing}")

    return True


# Automatically validate on import (optional, can be removed if causes issues)
validate_model_registration()
