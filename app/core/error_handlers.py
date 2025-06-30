"""
🎓 Centralized Error Handling System

This module provides comprehensive error handling for the FastAPI application,
ensuring consistent, secure, and helpful error responses across all endpoints.

Educational Focus:
- Exception handling patterns and inheritance
- HTTP status code semantics
- Security considerations in error responses
- Structured error response design
"""

import logging
import traceback
from typing import Any, Dict, Optional, Union
from uuid import uuid4

from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

# Configure logger for this module
from app.core.logging_config import get_logger

logger = get_logger(__name__)


# ============================================================================
# 🎓 CUSTOM EXCEPTION BASE CLASSES
# ============================================================================


class AppException(Exception):
    """
    🎓 Base exception class for all application-specific errors.

    Educational Note:
    This provides a common interface for all our custom exceptions,
    making it easier to handle them consistently and add common functionality.
    """

    def __init__(
        self,
        message: str,
        error_code: str = "APP_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class BusinessLogicError(AppException):
    """
    🎓 Base class for business logic violations.

    These are errors that occur when business rules are violated,
    typically resulting in 400 Bad Request responses.
    """

    def __init__(
        self, message: str, error_code: str = "BUSINESS_LOGIC_ERROR", **kwargs
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=status.HTTP_400_BAD_REQUEST,
            **kwargs,
        )


class NotFoundError(AppException):
    """
    🎓 Base class for resource not found errors.

    Used when a requested resource doesn't exist or user doesn't have access.
    """

    def __init__(self, message: str, error_code: str = "RESOURCE_NOT_FOUND", **kwargs):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=status.HTTP_404_NOT_FOUND,
            **kwargs,
        )


class AccessDeniedError(AppException):
    """
    🎓 Base class for access control violations.

    Used when user doesn't have permission to access a resource.
    """

    def __init__(self, message: str, error_code: str = "ACCESS_DENIED", **kwargs):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=status.HTTP_403_FORBIDDEN,
            **kwargs,
        )


class ValidationError(AppException):
    """
    🎓 Base class for data validation errors.

    Used for custom validation logic beyond what Pydantic provides.
    """

    def __init__(self, message: str, error_code: str = "VALIDATION_ERROR", **kwargs):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            **kwargs,
        )


# ============================================================================
# 🎓 DOMAIN-SPECIFIC EXCEPTION MAPPING
# ============================================================================

# Map existing domain exceptions to our new base classes
DOMAIN_EXCEPTION_MAP = {
    # Credit Cards domain
    "AccountNotFoundError": (NotFoundError, "ACCOUNT_NOT_FOUND"),
    "AccountAccessDeniedError": (AccessDeniedError, "ACCOUNT_ACCESS_DENIED"),
    "CreditCardNotFoundError": (NotFoundError, "CREDIT_CARD_NOT_FOUND"),
    "CreditCardAccessDeniedError": (AccessDeniedError, "CREDIT_CARD_ACCESS_DENIED"),
    # Invoices domain
    "InvoiceCreditCardNotFoundError": (NotFoundError, "INVOICE_CREDIT_CARD_NOT_FOUND"),
    "InvoiceBrokerNotFoundError": (NotFoundError, "INVOICE_BROKER_NOT_FOUND"),
    "InvoiceRawInvoiceEmptyError": (ValidationError, "INVOICE_RAW_EMPTY"),
    # Add more domain exceptions as needed
    # Transactions domain
    "TransactionAccountAndCreditCardNotFoundError": (
        NotFoundError,
        "TRANSACTION_ACCOUNT_AND_CREDIT_CARD_NOT_FOUND",
    ),
}


def map_domain_exception(exc: Exception) -> AppException:
    """
    🎓 Map domain-specific exceptions to standardized app exceptions.

    This function allows us to gradually migrate existing domain exceptions
    to our new standardized error handling system.
    """
    exc_name = exc.__class__.__name__

    if exc_name in DOMAIN_EXCEPTION_MAP:
        exception_class, error_code = DOMAIN_EXCEPTION_MAP[exc_name]
        return exception_class(message=str(exc), error_code=error_code)

    # Default to generic business logic error for unknown domain exceptions
    return BusinessLogicError(message=str(exc), error_code="UNKNOWN_BUSINESS_ERROR")


# ============================================================================
# 🎓 STANDARDIZED ERROR RESPONSE FORMAT
# ============================================================================


def create_error_response(
    error_code: str,
    message: str,
    status_code: int,
    request_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    include_trace: bool = False,
) -> Dict[str, Any]:
    """
    🎓 Create a standardized error response format.

    Educational Note:
    Consistent error response format makes it easier for clients to handle errors
    and provides useful information for debugging without exposing sensitive details.

    Args:
        error_code: Machine-readable error identifier
        message: Human-readable error description
        status_code: HTTP status code
        request_id: Unique identifier for this request (for tracing)
        details: Additional error context (sanitized)
        include_trace: Whether to include stack trace (dev mode only)

    Returns:
        Standardized error response dictionary
    """

    response = {
        "error": {
            "code": error_code,
            "message": message,
            "timestamp": None,  # Will be set by logging middleware
            "request_id": request_id or str(uuid4()),
        }
    }

    # Add details if provided
    if details:
        response["error"]["details"] = details

    # Add stack trace only in development mode
    if include_trace:
        response["error"]["trace"] = traceback.format_exc()

    return response


# ============================================================================
# 🎓 EXCEPTION HANDLERS
# ============================================================================


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """
    🎓 Handle custom application exceptions.

    This handler processes our custom AppException hierarchy and returns
    structured responses with appropriate HTTP status codes.
    """

    # Generate request ID for tracing
    request_id = getattr(request.state, "request_id", str(uuid4()))

    # Log the exception with context
    logger.warning(
        f"Application exception occurred",
        extra={
            "error_code": exc.error_code,
            "message": exc.message,
            "status_code": exc.status_code,
            "request_id": request_id,
            "path": str(request.url),
            "method": request.method,
            "details": exc.details,
        },
    )

    # Create standardized response
    response_data = create_error_response(
        error_code=exc.error_code,
        message=exc.message,
        status_code=exc.status_code,
        request_id=request_id,
        details=exc.details,
    )

    return JSONResponse(status_code=exc.status_code, content=response_data)


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """
    🎓 Handle Pydantic validation errors.

    Educational Note:
    Pydantic validation errors contain detailed information about what went wrong.
    We transform these into user-friendly messages while preserving technical details.
    """

    request_id = getattr(request.state, "request_id", str(uuid4()))

    # Extract and format validation errors
    formatted_errors = []
    for error in exc.errors():
        field_path = " -> ".join(str(loc) for loc in error["loc"])
        formatted_errors.append(
            {"field": field_path, "message": error["msg"], "type": error["type"]}
        )

    # Log validation error
    logger.warning(
        f"Validation error occurred",
        extra={
            "error_code": "VALIDATION_ERROR",
            "request_id": request_id,
            "path": str(request.url),
            "method": request.method,
            "validation_errors": formatted_errors,
        },
    )

    # Create user-friendly response
    response_data = create_error_response(
        error_code="VALIDATION_ERROR",
        message="Request data validation failed",
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        request_id=request_id,
        details={"validation_errors": formatted_errors},
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=response_data
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    🎓 Handle FastAPI HTTP exceptions.

    This ensures even FastAPI's built-in HTTP exceptions follow our
    standardized response format.
    """

    request_id = getattr(request.state, "request_id", str(uuid4()))

    # Map HTTP status codes to error codes
    status_code_map = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        500: "INTERNAL_SERVER_ERROR",
    }

    error_code = status_code_map.get(exc.status_code, "HTTP_ERROR")

    # Log HTTP exception
    logger.warning(
        f"HTTP exception occurred",
        extra={
            "error_code": error_code,
            "status_code": exc.status_code,
            "detail": exc.detail,
            "request_id": request_id,
            "path": str(request.url),
            "method": request.method,
        },
    )

    # Create standardized response
    response_data = create_error_response(
        error_code=error_code,
        message=str(exc.detail),
        status_code=exc.status_code,
        request_id=request_id,
    )

    return JSONResponse(status_code=exc.status_code, content=response_data)


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    🎓 Handle unexpected exceptions (catch-all).

    Educational Note:
    This is our safety net for any unhandled exceptions. We log the full error
    for debugging but return a generic message to clients for security.
    """

    request_id = getattr(request.state, "request_id", str(uuid4()))

    # Check if this is a domain exception we can map
    if exc.__class__.__name__ in DOMAIN_EXCEPTION_MAP:
        mapped_exc = map_domain_exception(exc)
        return await app_exception_handler(request, mapped_exc)

    # Log the unexpected exception with full details
    logger.error(
        f"Unexpected exception occurred",
        extra={
            "error_code": "INTERNAL_SERVER_ERROR",
            "exception_type": exc.__class__.__name__,
            "exception_message": str(exc),
            "request_id": request_id,
            "path": str(request.url),
            "method": request.method,
        },
        exc_info=True,  # Include full stack trace in logs
    )

    # Return generic error to client (security consideration)
    response_data = create_error_response(
        error_code="INTERNAL_SERVER_ERROR",
        message="An unexpected error occurred. Please try again later.",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        request_id=request_id,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=response_data
    )


# ============================================================================
# 🎓 UTILITY FUNCTIONS
# ============================================================================


def raise_not_found(
    resource_name: str, resource_id: Optional[Union[str, int]] = None
) -> None:
    """
    🎓 Utility function to raise standardized not found errors.

    Usage:
        raise_not_found("Credit Card", credit_card_id)
        raise_not_found("Account")
    """
    if resource_id:
        message = f"{resource_name} with ID '{resource_id}' not found"
    else:
        message = f"{resource_name} not found"

    raise NotFoundError(
        message=message,
        error_code=f"{resource_name.upper().replace(' ', '_')}_NOT_FOUND",
    )


def raise_access_denied(resource_name: str, action: str = "access") -> None:
    """
    🎓 Utility function to raise standardized access denied errors.

    Usage:
        raise_access_denied("Credit Card", "update")
        raise_access_denied("Account")
    """
    message = f"Access denied: insufficient permissions to {action} {resource_name}"

    raise AccessDeniedError(
        message=message,
        error_code=f"{resource_name.upper().replace(' ', '_')}_ACCESS_DENIED",
    )


def raise_validation_error(field_name: str, issue: str) -> None:
    """
    🎓 Utility function to raise standardized validation errors.

    Usage:
        raise_validation_error("email", "must be a valid email address")
        raise_validation_error("amount", "must be greater than zero")
    """
    message = f"Validation failed for field '{field_name}': {issue}"

    raise ValidationError(
        message=message,
        error_code="FIELD_VALIDATION_ERROR",
        details={"field": field_name, "issue": issue},
    )
