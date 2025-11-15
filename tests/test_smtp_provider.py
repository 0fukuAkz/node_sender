"""
Tests for SMTP provider management and load balancing
"""

import pytest
import time
from unittest.mock import Mock
from src.email_dispatcher.smtp_provider import (
    SMTPProvider,
    SMTPProviderManager
)
from src.email_dispatcher.types import SMTPProviderConfig
from src.email_dispatcher.exceptions import ConfigurationError


@pytest.fixture
def provider_config() -> SMTPProviderConfig:
    """Fixture for provider configuration."""
    return {
        'name': 'Test Provider',
        'priority': 5,
        'weight': 1.0,
        'enabled': True,
        'smtp_settings': {
            'host': 'smtp.example.com',
            'port': 587,
            'username': 'test@example.com',
            'password': 'password',
            'use_tls': True,
            'use_auth': True
        },
        'max_emails_per_hour': 100,
        'max_emails_per_day': 1000
    }


@pytest.fixture
def multiple_provider_configs() -> list[SMTPProviderConfig]:
    """Fixture for multiple provider configurations."""
    return [
        {
            'name': 'Provider A',
            'priority': 10,
            'weight': 0.5,
            'enabled': True,
            'smtp_settings': {
                'host': 'smtp.a.com',
                'port': 587,
                'username': 'a@example.com',
                'password': 'pass_a',
                'use_tls': True,
                'use_auth': True
            },
            'max_emails_per_hour': 500,
            'max_emails_per_day': 2000
        },
        {
            'name': 'Provider B',
            'priority': 5,
            'weight': 0.3,
            'enabled': True,
            'smtp_settings': {
                'host': 'smtp.b.com',
                'port': 587,
                'username': 'b@example.com',
                'password': 'pass_b',
                'use_tls': True,
                'use_auth': True
            },
            'max_emails_per_hour': 300,
            'max_emails_per_day': 1000
        },
        {
            'name': 'Provider C',
            'priority': 1,
            'weight': 0.2,
            'enabled': True,
            'smtp_settings': {
                'host': 'smtp.c.com',
                'port': 587,
                'username': 'c@example.com',
                'password': 'pass_c',
                'use_tls': True,
                'use_auth': True
            },
            'max_emails_per_hour': 200,
            'max_emails_per_day': 500
        }
    ]


class TestSMTPProvider:
    """Tests for SMTPProvider class."""
    
    def test_provider_initialization(self, provider_config):
        """Test provider initialization."""
        provider = SMTPProvider(provider_config)
        
        assert provider.name == 'Test Provider'
        assert provider.priority == 5
        assert provider.weight == 1.0
        assert provider.enabled is True
        assert provider.max_emails_per_hour == 100
        assert provider.max_emails_per_day == 1000
        assert provider.total_sent == 0
        assert provider.total_failed == 0
    
    def test_can_send_when_enabled(self, provider_config):
        """Test can_send returns True when provider is enabled and within limits."""
        provider = SMTPProvider(provider_config)
        
        assert provider.can_send() is True
    
    def test_can_send_when_disabled(self, provider_config):
        """Test can_send returns False when provider is disabled."""
        provider_config['enabled'] = False
        provider = SMTPProvider(provider_config)
        
        assert provider.can_send() is False
    
    def test_can_send_hourly_limit_reached(self, provider_config):
        """Test can_send returns False when hourly limit is reached."""
        provider = SMTPProvider(provider_config)
        provider.emails_sent_hour = 100  # Reached limit
        
        assert provider.can_send() is False
    
    def test_can_send_daily_limit_reached(self, provider_config):
        """Test can_send returns False when daily limit is reached."""
        provider = SMTPProvider(provider_config)
        provider.emails_sent_day = 1000  # Reached limit
        
        assert provider.can_send() is False
    
    def test_record_send_success(self, provider_config):
        """Test recording successful send."""
        provider = SMTPProvider(provider_config)
        
        provider.record_send(success=True)
        
        assert provider.total_sent == 1
        assert provider.total_failed == 0
        assert provider.emails_sent_hour == 1
        assert provider.emails_sent_day == 1
    
    def test_record_send_failure(self, provider_config):
        """Test recording failed send."""
        provider = SMTPProvider(provider_config)
        
        provider.record_send(success=False)
        
        assert provider.total_sent == 0
        assert provider.total_failed == 1
        assert provider.emails_sent_hour == 1
        assert provider.emails_sent_day == 1
    
    def test_get_load_calculation(self, provider_config):
        """Test load calculation."""
        provider = SMTPProvider(provider_config)
        
        # Send 50 emails (50% of hourly limit)
        for _ in range(50):
            provider.record_send(success=True)
        
        load = provider.get_load()
        assert 0.4 <= load <= 0.6  # Approximately 50%
    
    def test_get_stats(self, provider_config):
        """Test getting provider statistics."""
        provider = SMTPProvider(provider_config)
        provider.record_send(success=True)
        provider.record_send(success=False)
        
        stats = provider.get_stats()
        
        assert stats['name'] == 'Test Provider'
        assert stats['enabled'] is True
        assert stats['total_sent'] == 1
        assert stats['total_failed'] == 1
        assert stats['emails_sent_hour'] == 2


class TestSMTPProviderManager:
    """Tests for SMTPProviderManager class."""
    
    def test_manager_initialization(self, multiple_provider_configs):
        """Test manager initialization."""
        manager = SMTPProviderManager(
            providers=multiple_provider_configs,
            strategy='round_robin'
        )
        
        assert len(manager.providers) == 3
        assert manager.strategy == 'round_robin'
    
    def test_manager_no_providers_raises_error(self):
        """Test manager raises error with no providers."""
        with pytest.raises(ConfigurationError):
            SMTPProviderManager(providers=[], strategy='round_robin')
    
    def test_manager_duplicate_names_raises_error(self, provider_config):
        """Test manager raises error with duplicate provider names."""
        configs = [provider_config, provider_config]  # Same config twice
        
        with pytest.raises(ConfigurationError):
            SMTPProviderManager(providers=configs, strategy='round_robin')
    
    def test_round_robin_strategy(self, multiple_provider_configs):
        """Test round-robin load balancing strategy."""
        manager = SMTPProviderManager(
            providers=multiple_provider_configs,
            strategy='round_robin'
        )
        
        # Get providers in sequence
        p1 = manager.get_provider()
        p2 = manager.get_provider()
        p3 = manager.get_provider()
        p4 = manager.get_provider()  # Should wrap around
        
        assert p1.name != p2.name
        assert p2.name != p3.name
        assert p1.name == p4.name  # Wrapped around
    
    def test_priority_strategy(self, multiple_provider_configs):
        """Test priority-based load balancing strategy."""
        manager = SMTPProviderManager(
            providers=multiple_provider_configs,
            strategy='priority'
        )
        
        # Should always return highest priority provider (Provider A with priority 10)
        provider = manager.get_provider()
        
        assert provider.name == 'Provider A'
        assert provider.priority == 10
    
    def test_weighted_strategy(self, multiple_provider_configs):
        """Test weighted random load balancing strategy."""
        manager = SMTPProviderManager(
            providers=multiple_provider_configs,
            strategy='weighted'
        )
        
        # Get multiple providers and check distribution
        selections = {}
        for _ in range(100):
            provider = manager.get_provider()
            selections[provider.name] = selections.get(provider.name, 0) + 1
        
        # Provider A (weight 0.5) should be selected most often
        assert selections.get('Provider A', 0) > selections.get('Provider B', 0)
        assert selections.get('Provider A', 0) > selections.get('Provider C', 0)
    
    def test_least_loaded_strategy(self, multiple_provider_configs):
        """Test least loaded load balancing strategy."""
        manager = SMTPProviderManager(
            providers=multiple_provider_configs,
            strategy='least_loaded'
        )
        
        # Initially all have zero load
        provider = manager.get_provider()
        assert provider is not None
        
        # Record some sends to increase load
        provider.record_send(success=True)
        provider.record_send(success=True)
        
        # Next provider should be different (less loaded)
        next_provider = manager.get_provider()
        assert next_provider.name != provider.name
    
    def test_random_strategy(self, multiple_provider_configs):
        """Test random load balancing strategy."""
        manager = SMTPProviderManager(
            providers=multiple_provider_configs,
            strategy='random'
        )
        
        # Get random providers
        provider1 = manager.get_provider()
        provider2 = manager.get_provider()
        
        assert provider1 is not None
        assert provider2 is not None
    
    def test_get_smtp_settings(self, multiple_provider_configs):
        """Test getting SMTP settings from provider."""
        manager = SMTPProviderManager(
            providers=multiple_provider_configs,
            strategy='priority'
        )
        
        smtp_settings = manager.get_smtp_settings()
        
        assert smtp_settings is not None
        assert smtp_settings['host'] == 'smtp.a.com'  # Highest priority
    
    def test_record_send_by_name(self, multiple_provider_configs):
        """Test recording send for specific provider."""
        manager = SMTPProviderManager(
            providers=multiple_provider_configs,
            strategy='round_robin'
        )
        
        manager.record_send('Provider B', success=True)
        
        provider_b = manager.get_provider_by_name('Provider B')
        assert provider_b.total_sent == 1
    
    def test_enable_disable_provider(self, multiple_provider_configs):
        """Test enabling and disabling providers."""
        manager = SMTPProviderManager(
            providers=multiple_provider_configs,
            strategy='round_robin'
        )
        
        # Disable Provider A
        manager.disable_provider('Provider A')
        provider_a = manager.get_provider_by_name('Provider A')
        assert provider_a.enabled is False
        
        # Enable Provider A
        manager.enable_provider('Provider A')
        assert provider_a.enabled is True
    
    def test_get_all_stats(self, multiple_provider_configs):
        """Test getting statistics for all providers."""
        manager = SMTPProviderManager(
            providers=multiple_provider_configs,
            strategy='round_robin'
        )
        
        # Record some activity
        manager.record_send('Provider A', success=True)
        manager.record_send('Provider B', success=False)
        
        stats = manager.get_all_stats()
        
        assert len(stats) == 3
        assert all('name' in s for s in stats)
        assert all('total_sent' in s for s in stats)
    
    def test_no_available_providers(self, multiple_provider_configs):
        """Test behavior when no providers are available."""
        # Disable all providers
        for config in multiple_provider_configs:
            config['enabled'] = False
        
        with pytest.raises(ConfigurationError):
            SMTPProviderManager(
                providers=multiple_provider_configs,
                strategy='round_robin'
            )

