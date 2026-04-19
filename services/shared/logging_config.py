"""
RecSys ML Platform — Shared Logging Configuration.
"""

import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""
    def __init__(self, service_name: str):
        super().__init__()
        self.service_name = service_name

    def format(self, record):
        log_record = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "service": self.service_name,
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "funcName": record.funcName,
        }
        
        # Add exception info if any
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_record)

def setup_logging(service_name: str, level=logging.INFO):
    """Configure structured logging for the given service."""
    logger = logging.getLogger()
    logger.setLevel(level)
    
    # Clear existing handlers to prevent duplicates
    if logger.hasHandlers():
        logger.handlers.clear()
        
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter(service_name))
    logger.addHandler(handler)
    
    # Also set uvicorn and fastapi loggers
    for logger_name in ("uvicorn", "uvicorn.access", "fastapi"):
        l = logging.getLogger(logger_name)
        l.handlers = [handler]
        l.setLevel(level)
        l.propagate = False
