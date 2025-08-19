"""
Core authentication module for JWT-based authentication.

This module provides:
- JWT token creation and validation
- Authentication dependencies for FastAPI
- Token response schemas
"""

from app.core.auth.jwt_handler import JWTHandler
from app.core.auth.schemas import TokenResponse, TokenData

__all__ = ["JWTHandler", "TokenResponse", "TokenData"]