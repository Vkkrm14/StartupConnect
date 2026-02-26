"""Structured logging setup"""

import logging
import sys
from datetime import datetime
import json

class JSONFormatter(logging.Formatter):
    """Format logs as JSON for better parsing"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        
        return json.dumps(log_data)

def setup_logging(service_name: str, log_level: str = "INFO"):
    """
    Setup structured logging for service
    
    Args:
        service_name: Name of the service (e.g., "graph-service")
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Console handler with JSON formatting
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(JSONFormatter())
    logger.addHandler(console_handler)
    
    # Add service name to all logs
    logger = logging.getLogger(service_name)
    
    return logger
