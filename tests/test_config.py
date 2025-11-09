"""
Unit tests for configuration management
"""

import pytest
import os
import tempfile
from src.email_dispatcher import Config
from src.email_dispatcher.exceptions import ConfigurationError


class TestConfig:
    """Test Config class."""
    
    @pytest.fixture
    def temp_config_file(self):
        """Create temporary config file."""
        content = """[general]
mode = relay
concurrency = 10
retry_limit = 2
log_path = logs
from_email = test@example.com
subject = Test Subject
rate_per_minute = 60
rate_per_hour = 3600
template_path = templates/message.html
leads_path = data/leads.txt
suppression_path = data/suppressions.txt
connection_pool_size = 5
batch_size = 100
checkpoint_interval = 50
max_retries_per_email = 3

[smtp]
host = smtp.example.com
port = 587
username = user@example.com
password = testpass
use_tls = true
use_auth = true

[proxy]
enabled = false
type = socks5
host = 127.0.0.1
port = 9050
"""
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.ini') as f:
            f.write(content)
            temp_path = f.name
        
        yield temp_path
        
        # Cleanup
        try:
            os.unlink(temp_path)
        except:
            pass
    
    def test_load_config(self, temp_config_file):
        """Test loading configuration from file."""
        config = Config(temp_config_file)
        assert config.mode == 'relay'
    
    def test_get_general_settings(self, temp_config_file):
        """Test getting general settings."""
        config = Config(temp_config_file)
        general = config.get_general_settings()
        
        assert general['concurrency'] == 10
        assert general['retry_limit'] == 2
        assert general['rate_per_minute'] == 60
        assert general['connection_pool_size'] == 5
        assert general['batch_size'] == 100
    
    def test_get_smtp_settings(self, temp_config_file):
        """Test getting SMTP settings."""
        config = Config(temp_config_file)
        smtp = config.get_smtp_settings()
        
        assert smtp['host'] == 'smtp.example.com'
        assert smtp['port'] == 587
        assert smtp['username'] == 'user@example.com'
        assert smtp['use_tls'] is True
    
    def test_get_proxy_settings_disabled(self, temp_config_file):
        """Test getting proxy settings when disabled."""
        config = Config(temp_config_file)
        proxy = config.get_proxy_settings()
        
        assert proxy is None
    
    def test_missing_config_file(self):
        """Test handling missing config file."""
        with pytest.raises(ConfigurationError):
            Config('nonexistent.ini')
    
    def test_env_override(self, temp_config_file, monkeypatch):
        """Test environment variable override."""
        monkeypatch.setenv('CONCURRENCY', '20')
        monkeypatch.setenv('SMTP_HOST', 'override.example.com')
        
        config = Config(temp_config_file)
        general = config.get_general_settings()
        smtp = config.get_smtp_settings()
        
        assert general['concurrency'] == 20
        assert smtp['host'] == 'override.example.com'
    
    def test_validation_concurrency_too_low(self, temp_config_file):
        """Test validation fails for concurrency < 1."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.ini') as f:
            f.write("""[general]
concurrency = 0
[smtp]
host = test.com
port = 587
[proxy]
enabled = false
""")
            bad_config = f.name
        
        try:
            config = Config(bad_config)
            with pytest.raises(ConfigurationError):
                config.get_general_settings()
        finally:
            os.unlink(bad_config)

