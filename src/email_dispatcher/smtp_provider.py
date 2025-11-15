"""
Multiple SMTP provider support with load balancing
"""

import random
import time
import threading
from typing import List, Optional
from logging import Logger

from .types import SMTPProviderConfig, SMTPSettings, LoadBalancingStrategy
from .exceptions import ConfigurationError


class SMTPProvider:
    """SMTP provider with usage tracking."""
    
    def __init__(self, config: SMTPProviderConfig):
        """
        Initialize SMTP provider.
        
        Args:
            config: Provider configuration
        """
        self.name = config['name']
        self.priority = config.get('priority', 0)
        self.weight = config.get('weight', 1)
        self.enabled = config.get('enabled', True)
        self.smtp_settings = config['smtp_settings']
        self.max_emails_per_hour = config.get('max_emails_per_hour')
        self.max_emails_per_day = config.get('max_emails_per_day')
        
        # Usage tracking
        self.emails_sent_hour = 0
        self.emails_sent_day = 0
        self.last_hour_reset = time.time()
        self.last_day_reset = time.time()
        self.total_sent = 0
        self.total_failed = 0
        self.last_used = time.time()
        
        # Lock for thread safety
        self.lock = threading.Lock()
    
    def can_send(self) -> bool:
        """
        Check if provider can send emails.
        
        Returns:
            True if provider can send, False otherwise
        """
        if not self.enabled:
            return False
        
        with self.lock:
            # Reset hourly counter
            current_time = time.time()
            if current_time - self.last_hour_reset >= 3600:
                self.emails_sent_hour = 0
                self.last_hour_reset = current_time
            
            # Reset daily counter
            if current_time - self.last_day_reset >= 86400:
                self.emails_sent_day = 0
                self.last_day_reset = current_time
            
            # Check limits
            if self.max_emails_per_hour and self.emails_sent_hour >= self.max_emails_per_hour:
                return False
            
            if self.max_emails_per_day and self.emails_sent_day >= self.max_emails_per_day:
                return False
            
            return True
    
    def record_send(self, success: bool = True) -> None:
        """
        Record email send attempt.
        
        Args:
            success: Whether send was successful
        """
        with self.lock:
            self.emails_sent_hour += 1
            self.emails_sent_day += 1
            self.last_used = time.time()
            
            if success:
                self.total_sent += 1
            else:
                self.total_failed += 1
    
    def _calculate_load_unsafe(self) -> float:
        """
        Calculate current load (internal, assumes lock is held).
        
        Returns:
            Load value (0.0 to 1.0)
        """
        hour_load = 0.0
        day_load = 0.0
        
        if self.max_emails_per_hour:
            hour_load = self.emails_sent_hour / self.max_emails_per_hour
        
        if self.max_emails_per_day:
            day_load = self.emails_sent_day / self.max_emails_per_day
        
        return max(hour_load, day_load)
    
    def get_load(self) -> float:
        """
        Calculate current load on provider.
        
        Returns:
            Load value (0.0 to 1.0)
        """
        with self.lock:
            return self._calculate_load_unsafe()
    
    def get_stats(self) -> dict:
        """
        Get provider statistics.
        
        Returns:
            Dictionary of statistics
        """
        with self.lock:
            return {
                'name': self.name,
                'enabled': self.enabled,
                'total_sent': self.total_sent,
                'total_failed': self.total_failed,
                'emails_sent_hour': self.emails_sent_hour,
                'emails_sent_day': self.emails_sent_day,
                'current_load': self._calculate_load_unsafe(),
                'last_used': self.last_used
            }


class SMTPProviderManager:
    """Manages multiple SMTP providers with load balancing."""
    
    def __init__(
        self,
        providers: List[SMTPProviderConfig],
        strategy: LoadBalancingStrategy = 'round_robin',
        logger: Optional[Logger] = None
    ):
        """
        Initialize SMTP provider manager.
        
        Args:
            providers: List of provider configurations
            strategy: Load balancing strategy
            logger: Logger instance
        """
        if not providers:
            raise ConfigurationError("At least one SMTP provider must be configured")
        
        self.providers = [SMTPProvider(config) for config in providers]
        self.strategy = strategy
        self.logger = logger
        
        # Round-robin state
        self.current_index = 0
        self.lock = threading.Lock()
        
        # Validate providers
        self._validate_providers()
    
    def _validate_providers(self) -> None:
        """Validate provider configurations."""
        enabled_count = sum(1 for p in self.providers if p.enabled)
        if enabled_count == 0:
            raise ConfigurationError("At least one SMTP provider must be enabled")
        
        # Check for duplicate names
        names = [p.name for p in self.providers]
        if len(names) != len(set(names)):
            raise ConfigurationError("Provider names must be unique")
    
    def get_provider(self) -> Optional[SMTPProvider]:
        """
        Get next provider based on load balancing strategy.
        
        Returns:
            SMTPProvider instance or None if no providers available
        """
        if self.strategy == 'round_robin':
            return self._get_round_robin()
        elif self.strategy == 'weighted':
            return self._get_weighted()
        elif self.strategy == 'priority':
            return self._get_priority()
        elif self.strategy == 'least_loaded':
            return self._get_least_loaded()
        elif self.strategy == 'random':
            return self._get_random()
        else:
            return self._get_round_robin()
    
    def _get_round_robin(self) -> Optional[SMTPProvider]:
        """
        Get provider using round-robin strategy.
        
        Returns:
            SMTPProvider instance or None
        """
        with self.lock:
            attempts = 0
            max_attempts = len(self.providers)
            
            while attempts < max_attempts:
                provider = self.providers[self.current_index]
                self.current_index = (self.current_index + 1) % len(self.providers)
                attempts += 1
                
                if provider.can_send():
                    return provider
            
            return None
    
    def _get_weighted(self) -> Optional[SMTPProvider]:
        """
        Get provider using weighted random selection.
        
        Returns:
            SMTPProvider instance or None
        """
        available = [p for p in self.providers if p.can_send()]
        if not available:
            return None
        
        # Calculate total weight
        total_weight = sum(p.weight for p in available)
        
        # Random selection based on weights
        rand = random.uniform(0, total_weight)
        cumulative = 0
        
        for provider in available:
            cumulative += provider.weight
            if rand <= cumulative:
                return provider
        
        return available[-1]
    
    def _get_priority(self) -> Optional[SMTPProvider]:
        """
        Get provider using priority-based selection.
        
        Returns:
            SMTPProvider instance or None
        """
        available = [p for p in self.providers if p.can_send()]
        if not available:
            return None
        
        # Sort by priority (higher priority first)
        available.sort(key=lambda p: p.priority, reverse=True)
        return available[0]
    
    def _get_least_loaded(self) -> Optional[SMTPProvider]:
        """
        Get provider with least load.
        
        Returns:
            SMTPProvider instance or None
        """
        available = [p for p in self.providers if p.can_send()]
        if not available:
            return None
        
        # Sort by load (lowest first)
        available.sort(key=lambda p: p.get_load())
        return available[0]
    
    def _get_random(self) -> Optional[SMTPProvider]:
        """
        Get random available provider.
        
        Returns:
            SMTPProvider instance or None
        """
        available = [p for p in self.providers if p.can_send()]
        if not available:
            return None
        
        return random.choice(available)
    
    def get_smtp_settings(self) -> Optional[SMTPSettings]:
        """
        Get SMTP settings from next available provider.
        
        Returns:
            SMTPSettings or None if no providers available
        """
        provider = self.get_provider()
        if provider:
            return provider.smtp_settings
        return None
    
    def record_send(self, provider_name: str, success: bool = True) -> None:
        """
        Record send for specific provider.
        
        Args:
            provider_name: Name of provider
            success: Whether send was successful
        """
        for provider in self.providers:
            if provider.name == provider_name:
                provider.record_send(success)
                break
    
    def get_all_stats(self) -> List[dict]:
        """
        Get statistics for all providers.
        
        Returns:
            List of provider statistics
        """
        return [p.get_stats() for p in self.providers]
    
    def enable_provider(self, provider_name: str) -> None:
        """
        Enable a provider.
        
        Args:
            provider_name: Name of provider to enable
        """
        for provider in self.providers:
            if provider.name == provider_name:
                provider.enabled = True
                if self.logger:
                    self.logger.info(f"Enabled provider: {provider_name}")
                break
    
    def disable_provider(self, provider_name: str) -> None:
        """
        Disable a provider.
        
        Args:
            provider_name: Name of provider to disable
        """
        for provider in self.providers:
            if provider.name == provider_name:
                provider.enabled = False
                if self.logger:
                    self.logger.warning(f"Disabled provider: {provider_name}")
                break
    
    def get_provider_by_name(self, provider_name: str) -> Optional[SMTPProvider]:
        """
        Get provider by name.
        
        Args:
            provider_name: Name of provider
            
        Returns:
            SMTPProvider instance or None
        """
        for provider in self.providers:
            if provider.name == provider_name:
                return provider
        return None

