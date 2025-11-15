"""
Email Dispatcher - Production-grade bulk email sending system
"""

__version__ = "2.0.0"

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

# New modules
from .async_dispatcher import send_email_async, send_bulk_emails_async, AsyncConnectionPool
from .smtp_provider import SMTPProviderManager, SMTPProvider
from .ab_testing import ABTestManager
from .analytics import AnalyticsCollector

# Type exports
from .types import (
    SMTPSettings,
    ProxySettings,
    GeneralSettings,
    EmailIdentity,
    PlaceholderDict,
    ConnectionStats,
    MetricsStats,
    CampaignStats,
    ABTestVariant,
    ABTestConfig,
    SMTPProviderConfig,
    AnalyticsEvent,
    ReportData,
    LoadBalancingStrategy,
    ErrorType,
)

__all__ = [
    # Core
    'Config',
    'send_email_with_pool',
    'init_logger',
    
    # Exceptions
    'ConfigurationError',
    'CredentialError',
    'SMTPTransientError',
    'SMTPPermanentError',
    'SMTPConnectionError',
    'SMTPAuthenticationError',
    'PathSecurityError',
    'TemplateError',
    
    # Async
    'send_email_async',
    'send_bulk_emails_async',
    'AsyncConnectionPool',
    
    # SMTP Providers
    'SMTPProviderManager',
    'SMTPProvider',
    
    # A/B Testing
    'ABTestManager',
    
    # Analytics
    'AnalyticsCollector',
    
    # Types
    'SMTPSettings',
    'ProxySettings',
    'GeneralSettings',
    'EmailIdentity',
    'PlaceholderDict',
    'ConnectionStats',
    'MetricsStats',
    'CampaignStats',
    'ABTestVariant',
    'ABTestConfig',
    'SMTPProviderConfig',
    'AnalyticsEvent',
    'ReportData',
    'LoadBalancingStrategy',
    'ErrorType',
]

