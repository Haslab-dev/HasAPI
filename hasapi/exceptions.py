"""
HasAPI Exceptions

Custom exception classes for the framework.
"""

from typing import Optional, Any, Dict


class HTTPException(Exception):
    """
    Base HTTP exception class.
    
    Used for returning HTTP error responses with status codes and details.
    """
    
    def __init__(
        self, 
        status_code: int, 
        detail: Optional[str] = None, 
        headers: Optional[Dict[str, str]] = None
    ):
        self.status_code = status_code
        self.detail = detail or self._default_detail()
        self.headers = headers
        super().__init__(self.detail)
    
    def _default_detail(self) -> str:
        """Get default detail message based on status code"""
        status_messages = {
            400: "Bad Request",
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found",
            405: "Method Not Allowed",
            409: "Conflict",
            422: "Unprocessable Entity",
            429: "Too Many Requests",
            500: "Internal Server Error",
            502: "Bad Gateway",
            503: "Service Unavailable",
            504: "Gateway Timeout"
        }
        return status_messages.get(self.status_code, "HTTP Error")
    
    def __repr__(self) -> str:
        return f"HTTPException(status_code={self.status_code}, detail='{self.detail}')"


class RequestValidationError(HTTPException):
    """
    Exception raised when request validation fails.
    """
    
    def __init__(self, detail: Optional[str] = None, errors: Optional[list] = None):
        super().__init__(status_code=422, detail=detail or "Validation error")
        self.errors = errors or []


class ResponseValidationError(HTTPException):
    """
    Exception raised when response validation fails.
    """
    
    def __init__(self, detail: Optional[str] = None):
        super().__init__(status_code=500, detail=detail or "Response validation error")


class NotFoundException(HTTPException):
    """
    Exception raised when a resource is not found.
    """
    
    def __init__(self, detail: Optional[str] = None):
        super().__init__(status_code=404, detail=detail or "Resource not found")


class UnauthorizedException(HTTPException):
    """
    Exception raised when authentication is required but not provided.
    """
    
    def __init__(self, detail: Optional[str] = None):
        super().__init__(status_code=401, detail=detail or "Authentication required")


class ForbiddenException(HTTPException):
    """
    Exception raised when a user doesn't have permission to access a resource.
    """
    
    def __init__(self, detail: Optional[str] = None):
        super().__init__(status_code=403, detail=detail or "Permission denied")


class BadRequestException(HTTPException):
    """
    Exception raised when the request is malformed.
    """
    
    def __init__(self, detail: Optional[str] = None):
        super().__init__(status_code=400, detail=detail or "Bad request")


class ConflictException(HTTPException):
    """
    Exception raised when there's a conflict with the current state of the resource.
    """
    
    def __init__(self, detail: Optional[str] = None):
        super().__init__(status_code=409, detail=detail or "Conflict")


class TooManyRequestsException(HTTPException):
    """
    Exception raised when rate limit is exceeded.
    """
    
    def __init__(self, detail: Optional[str] = None, retry_after: Optional[int] = None):
        super().__init__(status_code=429, detail=detail or "Too many requests")
        if retry_after is not None:
            self.headers = {"Retry-After": str(retry_after)}


class InternalServerErrorException(HTTPException):
    """
    Exception raised when an unexpected server error occurs.
    """
    
    def __init__(self, detail: Optional[str] = None):
        super().__init__(status_code=500, detail=detail or "Internal server error")


class ServiceUnavailableException(HTTPException):
    """
    Exception raised when a service is temporarily unavailable.
    """
    
    def __init__(self, detail: Optional[str] = None, retry_after: Optional[int] = None):
        super().__init__(status_code=503, detail=detail or "Service unavailable")
        if retry_after is not None:
            self.headers = {"Retry-After": str(retry_after)}


class WebSocketException(Exception):
    """
    Base WebSocket exception class.
    """
    
    def __init__(self, code: int = 1000, reason: str = ""):
        self.code = code
        self.reason = reason
        super().__init__(f"WebSocket error: {code} {reason}")


class APIException(Exception):
    """
    Base API exception for application-specific errors.
    """
    
    def __init__(
        self, 
        message: str, 
        error_code: Optional[str] = None, 
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(message)


class ConfigurationError(Exception):
    """
    Exception raised when there's a configuration error.
    """
    
    def __init__(self, message: str):
        self.message = message
        super().__init__(f"Configuration error: {message}")


class DependencyError(Exception):
    """
    Exception raised when a required dependency is missing.
    """
    
    def __init__(self, dependency_name: str, message: Optional[str] = None):
        self.dependency_name = dependency_name
        self.message = message or f"Missing required dependency: {dependency_name}"
        super().__init__(self.message)


class ValidationError(Exception):
    """
    Exception raised when data validation fails.
    """
    
    def __init__(self, message: str, field: Optional[str] = None, value: Optional[Any] = None):
        self.message = message
        self.field = field
        self.value = value
        super().__init__(message)


class MiddlewareError(Exception):
    """
    Exception raised when middleware encounters an error.
    """
    
    def __init__(self, message: str, middleware_name: Optional[str] = None):
        self.message = message
        self.middleware_name = middleware_name
        super().__init__(f"Middleware error: {message}")


class RoutingError(Exception):
    """
    Exception raised when there's a routing error.
    """
    
    def __init__(self, message: str):
        self.message = message
        super().__init__(f"Routing error: {message}")


class TemplateError(Exception):
    """
    Exception raised when template rendering fails.
    """
    
    def __init__(self, message: str, template_name: Optional[str] = None):
        self.message = message
        self.template_name = template_name
        super().__init__(f"Template error: {message}")


class FileError(Exception):
    """
    Exception raised when file operations fail.
    """
    
    def __init__(self, message: str, file_path: Optional[str] = None):
        self.message = message
        self.file_path = file_path
        super().__init__(f"File error: {message}")


class DatabaseError(Exception):
    """
    Exception raised when database operations fail.
    """
    
    def __init__(self, message: str, operation: Optional[str] = None):
        self.message = message
        self.operation = operation
        super().__init__(f"Database error: {message}")


class CacheError(Exception):
    """
    Exception raised when cache operations fail.
    """
    
    def __init__(self, message: str, operation: Optional[str] = None):
        self.message = message
        self.operation = operation
        super().__init__(f"Cache error: {message}")


class AuthenticationError(Exception):
    """
    Exception raised when authentication fails.
    """
    
    def __init__(self, message: str = "Authentication failed"):
        self.message = message
        super().__init__(message)


class AuthorizationError(Exception):
    """
    Exception raised when authorization fails.
    """
    
    def __init__(self, message: str = "Access denied"):
        self.message = message
        super().__init__(message)


class RateLimitError(Exception):
    """
    Exception raised when rate limit is exceeded.
    """
    
    def __init__(self, message: str = "Rate limit exceeded", retry_after: Optional[int] = None):
        self.message = message
        self.retry_after = retry_after
        super().__init__(message)


class TimeoutError(Exception):
    """
    Exception raised when an operation times out.
    """
    
    def __init__(self, message: str = "Operation timed out", timeout: Optional[float] = None):
        self.message = message
        self.timeout = timeout
        super().__init__(message)