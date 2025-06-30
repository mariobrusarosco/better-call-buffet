"""
🎓 EDUCATIONAL: Advanced Middleware for Enterprise-Grade Logging

This module provides comprehensive request/response logging middleware that gives you
complete observability into your FastAPI application. Perfect for learning how
professional APIs handle logging, monitoring, and security.
"""

import time
import uuid
from typing import Callable, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging_config import (
    clear_request_context,
    get_logger,
    log_security_event,
    set_request_context,
)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    🎓 Comprehensive request/response logging middleware.

    Educational Note:
    Middleware in FastAPI processes every request and response, making it perfect
    for cross-cutting concerns like logging, authentication, and monitoring.

    This middleware:
    1. Generates unique request IDs for tracing
    2. Sets up logging context for the entire request
    3. Logs request details (method, path, headers, etc.)
    4. Measures request duration and performance (configurable)
    5. Logs response details (status, duration, errors)
    6. Handles security events and audit logging

    Performance Logging Control:
    - When enable_performance_logging=False (default): Basic request/response logging
    - When enable_performance_logging=True: Adds performance categorization and slow request alerts
    - Controlled via ENABLE_PERFORMANCE_LOGGING environment variable for production flexibility
    """

    def __init__(
        self,
        app,
        log_bodies: bool = False,
        log_headers: bool = True,
        enable_performance_logging: bool = False,
    ):
        """
        Initialize the logging middleware.

        Args:
            app: The FastAPI application instance
            log_bodies: Whether to log request/response bodies (be careful with PII!)
            log_headers: Whether to log request headers (filtered for security)
            enable_performance_logging: Whether to log detailed performance metrics
        """
        super().__init__(app)
        self.log_bodies = log_bodies
        self.log_headers = log_headers
        self.enable_performance_logging = enable_performance_logging
        self.logger = get_logger("app.middleware.request")

        # Headers to exclude from logging for security
        self.sensitive_headers = {
            "authorization",
            "cookie",
            "x-api-key",
            "x-auth-token",
            "x-access-token",
            "x-csrf-token",
            "x-session-token",
        }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        🎓 Process each request through the middleware pipeline.

        Educational Note:
        This method is called for every single HTTP request to your API.
        It's executed BEFORE your route handlers and can modify both
        the request and response.
        """

        # Generate unique request ID for tracing
        request_id = str(uuid.uuid4())
        start_time = time.time()

        # Extract user information if available
        user_id = await self._extract_user_id(request)

        # Set up logging context for this request
        set_request_context(request_id=request_id, user_id=user_id)

        # Log request start
        await self._log_request_start(request, request_id, user_id)

        # Process the request and handle any errors
        try:
            response = await call_next(request)

            # Log successful response
            await self._log_request_success(request, response, start_time)

            return response

        except Exception as exc:
            # Log request failure
            await self._log_request_failure(request, exc, start_time)
            raise

        finally:
            # Clean up request context
            clear_request_context()

    async def _extract_user_id(self, request: Request) -> Optional[str]:
        """
        🎓 Extract user ID from request for logging context.

        Educational Note:
        This function attempts to identify the authenticated user for this request.
        In a real application, you would extract this from JWT tokens, session cookies,
        or other authentication mechanisms.
        """
        # TODO: Implement actual user extraction logic based on your auth system
        # For now, we'll check for a simple header or return None

        # Example implementations:
        # 1. From JWT token: decode and extract user_id
        # 2. From session: lookup user from session ID
        # 3. From API key: lookup user from API key

        # Placeholder implementation
        user_header = request.headers.get("x-user-id")
        if user_header:
            return user_header

        # You could also extract from Authorization header:
        # auth_header = request.headers.get("authorization")
        # if auth_header and auth_header.startswith("Bearer "):
        #     token = auth_header[7:]
        #     user_id = decode_jwt_token(token).get("user_id")
        #     return user_id

        return None

    async def _log_request_start(
        self, request: Request, request_id: str, user_id: Optional[str]
    ) -> None:
        """🎓 Log the start of a request with full context."""

        # Extract client information
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "Unknown")

        # Prepare request headers (filtered for security)
        headers = {}
        if self.log_headers:
            headers = self._filter_sensitive_headers(dict(request.headers))

        # Log request start
        self.logger.info(
            "Request started",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            query_params=str(request.query_params) if request.query_params else None,
            client_ip=client_ip,
            user_agent=user_agent,
            user_id=user_id,
            headers=headers if headers else None,
            content_type=request.headers.get("content-type"),
            content_length=request.headers.get("content-length"),
        )

        # Log security events for sensitive endpoints
        if self._is_sensitive_endpoint(request.url.path):
            log_security_event(
                "sensitive_endpoint_access",
                severity="info",
                user_id=user_id,
                ip_address=client_ip,
                endpoint=request.url.path,
                method=request.method,
            )

    async def _log_request_success(
        self, request: Request, response: Response, start_time: float
    ) -> None:
        """🎓 Log successful request completion with performance metrics."""

        duration_ms = round((time.time() - start_time) * 1000, 2)

        # Determine log level based on performance (only if performance logging enabled)
        if self.enable_performance_logging:
            if duration_ms > 5000:  # > 5 seconds
                log_level = "error"
                performance_category = "very_slow"
            elif duration_ms > 2000:  # > 2 seconds
                log_level = "warning"
                performance_category = "slow"
            elif duration_ms > 1000:  # > 1 second
                log_level = "warning"
                performance_category = "moderate"
            else:
                log_level = "info"
                performance_category = "fast"
        else:
            # When performance logging is disabled, always use info level
            log_level = "info"
            performance_category = None

        # Prepare log data
        log_data = {
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
            "response_size": response.headers.get("content-length"),
            "content_type": response.headers.get("content-type"),
        }

        # Add performance category only if performance logging is enabled
        if self.enable_performance_logging and performance_category:
            log_data["performance_category"] = performance_category

        # Log request completion
        getattr(self.logger, log_level)("Request completed", **log_data)

        # Log performance alerts for slow requests (only if performance logging is enabled)
        if self.enable_performance_logging and duration_ms > 2000:
            self.logger.warning(
                "Slow request detected",
                method=request.method,
                path=request.url.path,
                duration_ms=duration_ms,
                status_code=response.status_code,
                performance_alert=True,
            )

    async def _log_request_failure(
        self, request: Request, exception: Exception, start_time: float
    ) -> None:
        """🎓 Log failed request with error details."""

        duration_ms = round((time.time() - start_time) * 1000, 2)

        # Log the error with full context
        self.logger.error(
            "Request failed",
            method=request.method,
            path=request.url.path,
            duration_ms=duration_ms,
            error_type=type(exception).__name__,
            error_message=str(exception),
            client_ip=self._get_client_ip(request),
        )

        # Check for potential security threats
        if self._is_potential_attack(request, exception):
            log_security_event(
                "potential_attack_detected",
                severity="warning",
                ip_address=self._get_client_ip(request),
                endpoint=request.url.path,
                method=request.method,
                error_type=type(exception).__name__,
                error_message=str(exception),
            )

    def _get_client_ip(self, request: Request) -> str:
        """
        🎓 Extract the real client IP address.

        Educational Note:
        In production, requests often go through proxies, load balancers, and CDNs.
        This function checks various headers to find the original client IP.
        """
        # Check for forwarded IP (most common in production)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # X-Forwarded-For can contain multiple IPs, first one is the original client
            return forwarded_for.split(",")[0].strip()

        # Check for real IP (some proxies use this)
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        # Fallback to direct connection IP
        if request.client:
            return request.client.host

        return "unknown"

    def _filter_sensitive_headers(self, headers: dict) -> dict:
        """🎓 Remove sensitive headers from logging for security."""
        return {
            key: value
            for key, value in headers.items()
            if key.lower() not in self.sensitive_headers
        }

    def _is_sensitive_endpoint(self, path: str) -> bool:
        """🎓 Identify endpoints that handle sensitive operations."""
        sensitive_patterns = [
            "/auth/",
            "/login",
            "/password",
            "/admin/",
            "/users/",
        ]
        return any(pattern in path.lower() for pattern in sensitive_patterns)

    def _is_potential_attack(self, request: Request, exception: Exception) -> bool:
        """
        🎓 Detect potential security attacks based on request patterns.

        Educational Note:
        This is a basic implementation. In production, you'd use more sophisticated
        detection algorithms and possibly integrate with security services.
        """
        suspicious_patterns = [
            # SQL injection attempts
            "union select",
            "drop table",
            "insert into",
            # XSS attempts
            "<script",
            "javascript:",
            # Path traversal
            "../",
            "..\\",
            # Command injection
            "; rm -rf",
            "; cat /etc/passwd",
        ]

        # Check URL path
        path_lower = request.url.path.lower()
        if any(pattern in path_lower for pattern in suspicious_patterns):
            return True

        # Check query parameters
        query_string = str(request.query_params).lower()
        if any(pattern in query_string for pattern in suspicious_patterns):
            return True

        # Check specific exception types that might indicate attacks
        attack_exceptions = [
            "ValidationError",
            "SQLAlchemyError",
            "FileNotFoundError",
        ]
        if type(exception).__name__ in attack_exceptions:
            return True

        return False


class PerformanceMonitoringMiddleware(BaseHTTPMiddleware):
    """
    🎓 Specialized middleware for performance monitoring.

    Educational Note:
    This middleware focuses specifically on performance metrics and can be used
    alongside the general logging middleware for comprehensive monitoring.
    """

    def __init__(self, app, slow_request_threshold: float = 1.0):
        super().__init__(app)
        self.slow_request_threshold = slow_request_threshold
        self.logger = get_logger("app.middleware.performance")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()

        response = await call_next(request)

        duration = time.time() - start_time

        if duration > self.slow_request_threshold:
            self.logger.warning(
                f"Slow request detected: {request.method} {request.url.path}",
                duration_seconds=duration,
                threshold_seconds=self.slow_request_threshold,
            )

        return response


class SecurityAuditMiddleware(BaseHTTPMiddleware):
    """
    🎓 Specialized middleware for security auditing.

    Educational Note:
    This middleware focuses on security-related logging and can help detect
    suspicious activity patterns in your API.
    """

    def __init__(self, app):
        super().__init__(app)
        self.logger = get_logger("app.middleware.security")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Log security-relevant information
        client_ip = self._get_client_ip(request)

        self.logger.info(
            "Security audit log",
            client_ip=client_ip,
            method=request.method,
            path=request.url.path,
            user_agent=request.headers.get("user-agent"),
            referer=request.headers.get("referer"),
        )

        return await call_next(request)

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP for security logging."""
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        if request.client:
            return request.client.host

        return "unknown"
