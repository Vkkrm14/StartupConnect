"""
Shared error handling and logging utilities for all services
"""
import logging
import traceback
from typing import Any, Dict
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from datetime import datetime
import uuid


class AppException(Exception):
    """Base exception for application errors"""
    def __init__(self, message: str, code: str, status_code: int = 500, details: Dict[str, Any] = None):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationException(AppException):
    """Raised when input validation fails"""
    def __init__(self, message: str, details: Dict[str, Any] = None):
        super().__init__(message, "VALIDATION_ERROR", 400, details)


class ResourceNotFoundException(AppException):
    """Raised when a resource is not found"""
    def __init__(self, resource: str, resource_id: str):
        message = f"{resource} with ID '{resource_id}' not found"
        super().__init__(message, "RESOURCE_NOT_FOUND", 404)


class ServiceUnavailableException(AppException):
    """Raised when a service is unavailable"""
    def __init__(self, service_name: str, details: str = ""):
        message = f"Service '{service_name}' is unavailable"
        if details:
            message += f": {details}"
        super().__init__(message, "SERVICE_UNAVAILABLE", 503)


class AuthenticationException(AppException):
    """Raised when authentication fails"""
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, "AUTH_ERROR", 401)


class AuthorizationException(AppException):
    """Raised when user lacks permissions"""
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(message, "AUTHZ_ERROR", 403)


def setup_logging(service_name: str, log_level: str = "INFO") -> logging.Logger:
    """
    Setup comprehensive logging configuration for a service
    
    Args:
        service_name: Name of the service
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(service_name)
    logger.setLevel(getattr(logging, log_level.upper()))
    
    if not logger.handlers:
        # Console handler with detailed format
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, log_level.upper()))
        
        # Detailed formatter with timestamp and service name
        formatter = logging.Formatter(
            fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    return logger


def setup_exception_handlers(app: FastAPI, logger: logging.Logger):
    """
    Setup global exception handlers for the FastAPI app
    
    Args:
        app: FastAPI application instance
        logger: Logger instance for the service
    """
    
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        """Handle custom application exceptions"""
        error_id = str(uuid.uuid4())
        
        logger.error(
            f"Application Error ({error_id})",
            extra={
                "error_code": exc.code,
                "status_code": exc.status_code,
                "path": request.url.path,
                "method": request.method,
                "details": exc.details,
                "traceback": traceback.format_exc()
            }
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "id": error_id,
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        )
    
    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        """Handle ValueError exceptions"""
        error_id = str(uuid.uuid4())
        
        logger.error(
            f"Validation Error ({error_id}): {str(exc)}",
            extra={
                "path": request.url.path,
                "method": request.method,
                "traceback": traceback.format_exc()
            }
        )
        
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "id": error_id,
                    "code": "VALIDATION_ERROR",
                    "message": str(exc),
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle unexpected exceptions"""
        error_id = str(uuid.uuid4())
        
        logger.error(
            f"Unhandled Exception ({error_id})",
            extra={
                "exception_type": type(exc).__name__,
                "message": str(exc),
                "path": request.url.path,
                "method": request.method,
                "traceback": traceback.format_exc()
            }
        )
        
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "id": error_id,
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred. Please contact support with error ID.",
                    "error_id": error_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        )


def setup_request_logging_middleware(app: FastAPI, logger: logging.Logger):
    """
    Setup middleware for detailed request/response logging
    
    Args:
        app: FastAPI application instance
        logger: Logger instance for the service
    """
    
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        """Log all HTTP requests and responses"""
        request_id = str(uuid.uuid4())
        
        # Log incoming request
        logger.info(
            f"→ {request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "query_params": dict(request.query_params),
                "client": request.client.host if request.client else "unknown"
            }
        )
        
        try:
            response = await call_next(request)
            
            # Log outgoing response
            logger.info(
                f"← {request.method} {request.url.path} - {response.status_code}",
                extra={
                    "request_id": request_id,
                    "status_code": response.status_code,
                    "method": request.method,
                    "path": request.url.path
                }
            )
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            return response
        
        except Exception as exc:
            logger.error(
                f"✗ {request.method} {request.url.path} - Exception",
                extra={
                    "request_id": request_id,
                    "exception_type": type(exc).__name__,
                    "message": str(exc),
                    "traceback": traceback.format_exc()
                }
            )
            raise
