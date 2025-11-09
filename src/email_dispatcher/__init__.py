"""
Email Dispatcher - Production-grade bulk email sending system
"""

__version__ = "1.0.0"

from .config import Config
from .dispatcher import send_email_with_pool
from .logger import init_logger
from .exceptions import (
    ConfigurationError,
    CredentialError,
    SMTPTransientError,
    SMTPPermanentError,
    SMTPConnectionError,
    SMTPAuthenticationError,
    PathSecurityError,
    TemplateError,
)

__all__ = [
    'Config',
    'send_email_with_pool',
    'init_logger',
    'ConfigurationError',
    'CredentialError',
    'SMTPTransientError',
    'SMTPPermanentError',
    'SMTPConnectionError',
    'SMTPAuthenticationError',
    'PathSecurityError',
    'TemplateError',
]

