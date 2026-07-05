import logging
import json
import sys
from datetime import datetime
from typing import Any
from app.config import settings

class JSONFormatter(logging.Formatter):
    """
    Formatter that outputs JSON logs.
    """
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "filename": record.filename,
            "line_number": record.lineno,
        }
        
        # Add request_id if available
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
            
        # Redact secrets in message or extra properties
        return json.dumps(self.redact_secrets(log_data))

    def redact_secrets(self, data: Any) -> Any:
        if isinstance(data, dict):
            new_dict = {}
            for k, v in data.items():
                if any(secret_key in k.lower() for secret_key in ["password", "secret", "token", "key"]):
                    new_dict[k] = "[REDACTED]"
                else:
                    new_dict[k] = self.redact_secrets(v)
            return new_dict
        elif isinstance(data, list):
            return [self.redact_secrets(item) for item in data]
        return data

def setup_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO if settings.ENV != "dev" else logging.DEBUG)
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    
    if settings.ENV != "dev":
        console_handler.setFormatter(JSONFormatter())
    else:
        # Standard human-readable console logging in development
        console_handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s [%(levelname)s] (%(module)s:%(lineno)d) - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
        )
        
    logger.addHandler(console_handler)

# Setup on import
setup_logging()
logger = logging.getLogger("truvia")
