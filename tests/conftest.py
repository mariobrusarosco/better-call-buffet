"""Shared pytest setup."""

# Import every SQLAlchemy model before tests construct loader options. The
# application does this during startup through the same registration module.
from app.db import model_registration as _model_registration  # noqa: F401
