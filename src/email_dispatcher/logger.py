import logging
import logging.handlers
import os
import json
from typing import Optional, Dict


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            'timestamp': self.formatTime(record, self.datefmt),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
        }
        
        # Add extra fields
        if hasattr(record, 'correlation_id'):
            log_data['correlation_id'] = record.correlation_id
        
        if hasattr(record, 'email_address'):
            log_data['email_address'] = record.email_address
        
        if hasattr(record, 'error_type'):
            log_data['error_type'] = record.error_type
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)


def init_logger(log_dir: str, structured: bool = False, level: str = 'INFO') -> logging.Logger:
    """
    Initialize logger with file and console handlers.
    
    Args:
        log_dir: Directory for log files
        structured: Use JSON structured logging
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        
    Returns:
        Configured logger instance
    """
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, 'email_sender.log')

    logger = logging.getLogger('EmailSender')
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Avoid duplicate handlers when called multiple times
    if not logger.handlers:
        # File handler
        file_handler = logging.handlers.RotatingFileHandler(
            log_path, maxBytes=10_000_000, backupCount=5, encoding='utf-8'
        )
        
        if structured:
            file_handler.setFormatter(StructuredFormatter())
        else:
            file_handler.setFormatter(
                logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            )
        
        logger.addHandler(file_handler)

        # Console handler
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        
        if structured:
            console.setFormatter(StructuredFormatter())
        else:
            console.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))
        
        logger.addHandler(console)

    return logger


def log_with_context(
    logger: logging.Logger,
    level: str,
    message: str,
    correlation_id: Optional[str] = None,
    email_address: Optional[str] = None,
    error_type: Optional[str] = None,
    **kwargs
) -> None:
    """
    Log message with additional context fields.
    
    Args:
        logger: Logger instance
        level: Log level (info, warning, error, etc.)
        message: Log message
        correlation_id: Unique correlation ID
        email_address: Email address being processed
        error_type: Type of error
        **kwargs: Additional context fields
    """
    extra = {}
    
    if correlation_id:
        extra['correlation_id'] = correlation_id
    
    if email_address:
        extra['email_address'] = email_address
    
    if error_type:
        extra['error_type'] = error_type
    
    # Add any additional kwargs
    extra.update(kwargs)
    
    log_func = getattr(logger, level.lower(), logger.info)
    log_func(message, extra=extra)