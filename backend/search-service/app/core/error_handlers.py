"""
Error handling and logging utilities for Search Service
"""
import logging
import traceback
from typing import Any, Dict
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from datetime import datetime
import uuid

logger = logging.getLogger("search-service")


class AppException(Exception):
    """Base exception for application errors"""
    def __init__(self, message: str, code: str, status_code: int = 500, details: Dict[str, Any] = None):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


def setup_error_handlers(app: FastAPI):
    """Setup global exception handlers for the FastAPI app"""
    
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        error_id = str(uuid.uuid4())
        logger.error(f"Error ({error_id}): {exc.code}", extra={
            "error_id": error_id,
            "code": exc.code,
            "status_code": exc.status_code
        })
        
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "id": error_id,
                    "code": exc.code,
                    "message": exc.message,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        error_id = str(uuid.uuid4())
        logger.error(f"Unhandled Exception ({error_id})", extra={
            "error_id": error_id,
            "type": type(exc).__name__,
            "message": str(exc)
        }, exc_info=True)
        
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "id": error_id,
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred",
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        )


def setup_logging():
    """Setup logging configuration"""
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        logger.addHandler(handler)
    
    return logger


def setup_request_logging(app: FastAPI):
    """Setup request/response logging middleware"""
    
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        request_id = str(uuid.uuid4())
        logger.info(f"→ {request.method} {request.url.path}", extra={"request_id": request_id})
        
        try:
            response = await call_next(request)
            logger.info(
                f"← {request.method} {request.url.path} - {response.status_code}",
                extra={"request_id": request_id, "status": response.status_code}
            )
            response.headers["X-Request-ID"] = request_id
            return response
        except Exception as exc:
            logger.error(
                f"✗ Exception in {request.method} {request.url.path}",
                extra={"request_id": request_id, "exception": type(exc).__name__},
                exc_info=True
            )
            raise
