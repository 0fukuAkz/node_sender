"""
Type definitions for Email Dispatcher
"""

from typing import TypedDict, Dict, List, Optional, Union, Literal, Any
from enum import Enum


class SMTPSettings(TypedDict):
    """SMTP configuration settings."""
    host: str
    port: int
    username: str
    password: str
    use_tls: bool
    use_auth: bool


class ProxySettings(TypedDict, total=False):
    """Proxy configuration settings."""
    type: Literal['socks4', 'socks5', 'http']
    host: str
    port: int
    username: str
    password: str


class GeneralSettings(TypedDict, total=False):
    """General application settings."""
    mode: str
    concurrency: int
    retry_limit: int
    log_path: str
    dry_run: bool
    subject: str
    rate_per_minute: int
    rate_per_hour: int
    template_path: str
    attachment_path: str
    leads_path: str
    suppression_path: str
    reply_to: str
    list_unsubscribe: str
    from_email: str
    connection_pool_size: int
    batch_size: int
    checkpoint_interval: int
    max_retries_per_email: int
    circuit_breaker_threshold: int
    enable_progress_bar: bool
    state_db_path: str
    structured_logging: bool


class EmailIdentity(TypedDict):
    """Generated email identity."""
    full_name: str
    email: str
    company: str
    uuid: str


class PlaceholderDict(TypedDict, total=False):
    """Template placeholder values."""
    recipient: str
    full_name: str
    email: str
    company: str
    uuid: str


class ConnectionStats(TypedDict):
    """Connection pool statistics."""
    total_created: int
    total_closed: int
    active_connections: int
    pool_size: int
    total_uses: int
    pool_hit_rate: float


class MetricsStats(TypedDict):
    """Metrics statistics."""
    total_processed: int
    total_success: int
    total_failed: int
    success_rate: float
    throughput: float
    elapsed_time: float


class CampaignStats(TypedDict):
    """Campaign statistics."""
    total_emails: int
    completed_emails: int
    failed_emails: int
    pending_emails: int
    elapsed_seconds: float


class ABTestVariant(TypedDict):
    """A/B test variant configuration."""
    name: str
    weight: float
    template_path: str
    subject: str
    metadata: Dict[str, Any]


class ABTestConfig(TypedDict):
    """A/B test configuration."""
    test_name: str
    variants: List[ABTestVariant]
    control_variant: str


class SMTPProviderConfig(TypedDict):
    """SMTP provider configuration."""
    name: str
    priority: int
    weight: int
    enabled: bool
    smtp_settings: SMTPSettings
    max_emails_per_hour: Optional[int]
    max_emails_per_day: Optional[int]


class AnalyticsEvent(TypedDict):
    """Analytics event data."""
    event_type: str
    timestamp: float
    email_address: str
    campaign_id: str
    variant_name: Optional[str]
    metadata: Dict[str, Any]


class ReportData(TypedDict):
    """Report data structure."""
    campaign_id: str
    start_time: float
    end_time: float
    total_sent: int
    total_failed: int
    success_rate: float
    avg_send_time: float
    variants: List[Dict[str, Any]]
    errors: List[Dict[str, Any]]


# Load balancing strategies
LoadBalancingStrategy = Literal['round_robin', 'weighted', 'priority', 'least_loaded', 'random']

# Error types
ErrorType = Literal['transient', 'permanent', 'connection_error', 'authentication_error', 'unknown']

