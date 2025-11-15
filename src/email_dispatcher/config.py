import configparser
import os
import stat
import warnings
from typing import Optional
from .exceptions import ConfigurationError, CredentialError
from .types import SMTPSettings, ProxySettings, GeneralSettings


class Config:
    def __init__(self, config_path='email_config.ini'):
        self.config_path = config_path
        self.parser = configparser.ConfigParser()
        
        if not os.path.exists(config_path):
            raise ConfigurationError(f"Configuration file not found: {config_path}")
        
        # Check file permissions (Unix-like systems)
        if hasattr(os, 'stat'):
            try:
                file_stat = os.stat(config_path)
                file_mode = file_stat.st_mode
                
                # Check if file is world-readable (others have read permission)
                if file_mode & stat.S_IROTH:
                    warnings.warn(
                        f"Security Warning: Configuration file {config_path} is world-readable. "
                        "This may expose sensitive credentials. "
                        "Run: chmod 600 {config_path}",
                        UserWarning
                    )
                
                # Check if file is group-readable
                if file_mode & stat.S_IRGRP:
                    warnings.warn(
                        f"Security Warning: Configuration file {config_path} is group-readable. "
                        "Consider restricting permissions with: chmod 600 {config_path}",
                        UserWarning
                    )
            except (OSError, AttributeError):
                pass  # Skip permission check on Windows or if stat fails
        
        self.parser.read(config_path)
        self.mode = self.parser.get('general', 'mode', fallback='relay')
        
        # Validate credentials on initialization
        self._validate_credentials()

    def get_general_settings(self) -> GeneralSettings:
        general = {
            'mode': self.mode,
            'concurrency': int(os.getenv('CONCURRENCY', self.parser.getint('general', 'concurrency', fallback=10))),
            'retry_limit': int(os.getenv('RETRY_LIMIT', self.parser.getint('general', 'retry_limit', fallback=1))),
            'log_path': os.getenv('LOG_PATH', self.parser.get('general', 'log_path', fallback='logs/')),
            'dry_run': self._get_bool_env('DRY_RUN', self.parser.getboolean('general', 'dry_run', fallback=False)),
            'subject': os.getenv('SUBJECT', self.parser.get('general', 'subject', fallback='Important message')),
            'rate_per_minute': int(os.getenv('RATE_PER_MINUTE', self.parser.getint('general', 'rate_per_minute', fallback=0))),
            'rate_per_hour': int(os.getenv('RATE_PER_HOUR', self.parser.getint('general', 'rate_per_hour', fallback=0))),
            'template_path': os.getenv('TEMPLATE_PATH', self.parser.get('general', 'template_path', fallback='templates/message.html')),
            'attachment_path': os.getenv('ATTACHMENT_PATH', self.parser.get('general', 'attachment_path', fallback='templates/attachment.html')),
            'leads_path': os.getenv('LEADS_PATH', self.parser.get('general', 'leads_path', fallback='data/leads.txt')),
            'suppression_path': os.getenv('SUPPRESSION_PATH', self.parser.get('general', 'suppression_path', fallback='data/suppressions.txt')),
            'reply_to': os.getenv('REPLY_TO', self.parser.get('general', 'reply_to', fallback='')),
            'list_unsubscribe': os.getenv('LIST_UNSUBSCRIBE', self.parser.get('general', 'list_unsubscribe', fallback='')),
            
            # Production scale settings
            'connection_pool_size': int(os.getenv('CONNECTION_POOL_SIZE', self.parser.getint('general', 'connection_pool_size', fallback=5))),
            'batch_size': int(os.getenv('BATCH_SIZE', self.parser.getint('general', 'batch_size', fallback=100))),
            'checkpoint_interval': int(os.getenv('CHECKPOINT_INTERVAL', self.parser.getint('general', 'checkpoint_interval', fallback=50))),
            'max_retries_per_email': int(os.getenv('MAX_RETRIES_PER_EMAIL', self.parser.getint('general', 'max_retries_per_email', fallback=3))),
            'circuit_breaker_threshold': int(os.getenv('CIRCUIT_BREAKER_THRESHOLD', self.parser.getint('general', 'circuit_breaker_threshold', fallback=10))),
            'enable_progress_bar': self._get_bool_env('ENABLE_PROGRESS_BAR', self.parser.getboolean('general', 'enable_progress_bar', fallback=True)),
            'state_db_path': os.getenv('STATE_DB_PATH', self.parser.get('general', 'state_db_path', fallback='logs/state.db')),
            'structured_logging': self._get_bool_env('STRUCTURED_LOGGING', self.parser.getboolean('general', 'structured_logging', fallback=False)),
        }
        
        # Validate settings
        if general['concurrency'] < 1:
            raise ConfigurationError("Concurrency must be at least 1")
        if general['concurrency'] > 100:
            warnings.warn("Concurrency > 100 may cause performance issues", UserWarning)
        if general['batch_size'] < 1:
            raise ConfigurationError("Batch size must be at least 1")
        if general['connection_pool_size'] < 1:
            raise ConfigurationError("Connection pool size must be at least 1")
        
        # Optional from address override
        from_email = os.getenv('FROM_EMAIL', self.parser.get('general', 'from_email', fallback=''))
        if from_email:
            general['from_email'] = from_email
        return general

    def get_smtp_settings(self) -> SMTPSettings:
        return {
            'host': os.getenv('SMTP_HOST', self.parser.get('smtp', 'host', fallback='')),
            'port': int(os.getenv('SMTP_PORT', self.parser.getint('smtp', 'port', fallback=587))),
            'username': os.getenv('SMTP_USERNAME', self.parser.get('smtp', 'username', fallback='')),
            'password': os.getenv('SMTP_PASSWORD', self.parser.get('smtp', 'password', fallback='')),
            'use_tls': self._get_bool_env('SMTP_USE_TLS', self.parser.getboolean('smtp', 'use_tls', fallback=True)),
            'use_auth': self._get_bool_env('SMTP_USE_AUTH', self.parser.getboolean('smtp', 'use_auth', fallback=True)),
        }

    def get_proxy_settings(self) -> Optional[ProxySettings]:
        if not self.parser.getboolean('proxy', 'enabled', fallback=False):
            return None
        return {
            'type': self.parser.get('proxy', 'type', fallback='socks5'),
            'host': self.parser.get('proxy', 'host'),
            'port': self.parser.getint('proxy', 'port'),
            'username': self.parser.get('proxy', 'username', fallback=''),
            'password': self.parser.get('proxy', 'password', fallback='')
        }

    def _validate_credentials(self) -> None:
        """
        Validate SMTP credentials and warn about security issues.
        
        Raises:
            CredentialError: If credentials are missing or invalid
        """
        # Check if password is stored in INI file (not recommended)
        ini_password = self.parser.get('smtp', 'password', fallback='')
        if ini_password and not os.getenv('SMTP_PASSWORD'):
            warnings.warn(
                "Security Warning: SMTP password is stored in plaintext in configuration file. "
                "Consider using environment variable SMTP_PASSWORD instead for better security.",
                UserWarning
            )
        
        # Validate that credentials are provided (either in INI or env)
        smtp_host = os.getenv('SMTP_HOST', self.parser.get('smtp', 'host', fallback=''))
        smtp_user = os.getenv('SMTP_USERNAME', self.parser.get('smtp', 'username', fallback=''))
        smtp_pass = os.getenv('SMTP_PASSWORD', ini_password)
        
        if not smtp_host:
            warnings.warn(
                "Configuration Warning: SMTP host is not configured. "
                "Email sending will fail.",
                UserWarning
            )
        
        if not smtp_user and self.parser.getboolean('smtp', 'use_auth', fallback=True):
            warnings.warn(
                "Configuration Warning: SMTP authentication is enabled but username is not configured.",
                UserWarning
            )
        
        if not smtp_pass and self.parser.getboolean('smtp', 'use_auth', fallback=True):
            warnings.warn(
                "Configuration Warning: SMTP authentication is enabled but password is not configured.",
                UserWarning
            )
    
    @staticmethod
    def _get_bool_env(env_key: str, default: bool) -> bool:
        val = os.getenv(env_key)
        if val is None:
            return default
        return val.strip().lower() in {"1", "true", "yes", "on"}