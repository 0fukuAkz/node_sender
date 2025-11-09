"""
Custom exception hierarchy for Email Dispatcher
"""


class EmailDispatcherError(Exception):
    """Base exception for all email dispatcher errors"""
    pass


class ConfigurationError(EmailDispatcherError):
    """Raised when configuration is invalid or missing"""
    pass


class SecurityError(EmailDispatcherError):
    """Raised when security validation fails"""
    pass


class PathSecurityError(SecurityError):
    """Raised when path validation fails (potential path traversal)"""
    pass


class CredentialError(ConfigurationError):
    """Raised when credentials are invalid or insecure"""
    pass


class SMTPError(EmailDispatcherError):
    """Base exception for SMTP-related errors"""
    pass


class SMTPConnectionError(SMTPError):
    """Raised when SMTP connection fails"""
    pass


class SMTPAuthenticationError(SMTPError):
    """Raised when SMTP authentication fails"""
    pass


class SMTPTransientError(SMTPError):
    """Raised for temporary SMTP errors that can be retried"""
    pass


class SMTPPermanentError(SMTPError):
    """Raised for permanent SMTP errors that should not be retried"""
    pass


class RateLimitError(EmailDispatcherError):
    """Raised when rate limit is exceeded"""
    pass


class TemplateError(EmailDispatcherError):
    """Raised when template processing fails"""
    pass


class ValidationError(EmailDispatcherError):
    """Raised when input validation fails"""
    pass


class StateError(EmailDispatcherError):
    """Raised when state management operations fail"""
    pass


class RetryQueueError(EmailDispatcherError):
    """Raised when retry queue operations fail"""
    pass

