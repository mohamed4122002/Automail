import logging
import sys
import json
import os
from datetime import datetime

class JsonFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""
    def format(self, record):
        log_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields if present
        if hasattr(record, "extra_fields"):
            log_record.update(record.extra_fields)
            
        return json.dumps(log_record)

def setup_logging():
    """Configure system-wide logging with support for JSON or Standard format."""
    log_format = os.getenv("LOG_FORMAT", "standard").lower()
    
    # Default handler
    handler = logging.StreamHandler(sys.stdout)
    
    if log_format == "json":
        handler.setFormatter(JsonFormatter())
    else:
        # Professional standard format
        fmt = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        handler.setFormatter(logging.Formatter(fmt))

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(handler)
    
    # Set levels for noisy libraries
    logging.getLogger('uvicorn').setLevel(logging.INFO)
    logging.getLogger('motor').setLevel(logging.WARNING)
    logging.getLogger('connect.main').setLevel(logging.WARNING) # Noisy sometimes

def get_logger(name: str):
    """Get a logger instance for a specific module."""
    return logging.getLogger(name)
