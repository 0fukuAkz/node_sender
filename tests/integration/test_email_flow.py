"""
Integration tests for email sending flow with mock SMTP server
"""

import pytest
import smtplib
from unittest.mock import Mock, MagicMock, patch
from src.email_dispatcher.dispatcher import send_email_with_pool, categorize_smtp_error
from src.email_dispatcher.connection_pool import SMTPConnectionPool
from src.email_dispatcher.exceptions import SMTPTransientError, SMTPPermanentError


class MockSMTPConnection:
    """Mock SMTP connection for testing."""
    
    def __init__(self, *args, **kwargs):
        self.messages_sent = []
        self.should_fail = False
        self.fail_type = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        pass
    
    def starttls(self, context=None):
        pass
    
    def login(self, username, password):
        if self.fail_type == 'auth':
            raise smtplib.SMTPAuthenticationError(535, 'Authentication failed')
    
    def send_message(self, msg):
        if self.should_fail:
            if self.fail_type == 'transient':
                raise smtplib.SMTPServerDisconnected('Connection lost')
            elif self.fail_type == 'permanent':
                raise smtplib.SMTPRecipientsRefused({'test@example.com': (550, 'User unknown')})
        
        self.messages_sent.append(msg)
    
    def quit(self):
        pass
    
    def noop(self):
        return (250, 'OK')


class TestEmailFlow:
    """Test complete email sending flow."""
    
    @pytest.fixture
    def mock_logger(self):
        """Create mock logger."""
        logger = Mock()
        logger.info = Mock()
        logger.error = Mock()
        logger.warning = Mock()
        return logger
    
    @pytest.fixture
    def smtp_settings(self):
        """SMTP settings for testing."""
        return {
            'host': 'smtp.test.com',
            'port': 587,
            'username': 'test@test.com',
            'password': 'testpass',
            'use_tls': True,
            'use_auth': True
        }
    
    @pytest.fixture
    def general_settings(self, tmp_path):
        """General settings for testing."""
        return {
            'dry_run': False,
            'from_email': 'sender@test.com',
            'subject': 'Test Subject',
            'log_path': str(tmp_path),
            'reply_to': '',
            'list_unsubscribe': ''
        }
    
    @pytest.fixture
    def temp_template(self, tmp_path):
        """Create temporary template file."""
        template_dir = tmp_path / 'templates'
        template_dir.mkdir()
        
        template_file = template_dir / 'test.html'
        template_file.write_text('<html><body>Hello {recipient}!</body></html>')
        
        return str(template_file)
    
    def test_categorize_transient_error(self):
        """Test categorizing transient SMTP errors."""
        error = smtplib.SMTPServerDisconnected('Connection lost')
        is_transient, error_type = categorize_smtp_error(error)
        
        assert is_transient is True
        assert error_type == 'connection_error'
    
    def test_categorize_permanent_error(self):
        """Test categorizing permanent SMTP errors."""
        error = smtplib.SMTPRecipientsRefused({'test@test.com': (550, 'User unknown')})
        is_transient, error_type = categorize_smtp_error(error)
        
        assert is_transient is False
        assert error_type == 'permanent'  # Generic permanent error type
    
    @patch('src.email_dispatcher.connection_pool.smtplib.SMTP')
    @patch('src.email_dispatcher.connection_pool.ssl.create_default_context')
    def test_send_email_success(
        self,
        mock_ssl_context,
        mock_smtp_class,
        smtp_settings,
        general_settings,
        mock_logger,
        temp_template
    ):
        """Test successful email sending."""
        # Setup mock SSL context
        mock_ssl_context.return_value = MagicMock()
        
        # Setup mock SMTP connection with proper interface
        mock_smtp_instance = MagicMock()
        mock_smtp_instance.starttls.return_value = None
        mock_smtp_instance.login.return_value = None
        mock_smtp_instance.send_message.return_value = None
        mock_smtp_instance.quit.return_value = None
        mock_smtp_instance.noop.return_value = (250, 'OK')
        
        # Track sent messages
        sent_messages = []
        def track_send_message(msg):
            sent_messages.append(msg)
            return None
        mock_smtp_instance.send_message.side_effect = track_send_message
        
        mock_smtp_class.return_value = mock_smtp_instance
        
        # Create connection pool and pre-populate with a connection to avoid queue wait
        pool = SMTPConnectionPool(smtp_settings, pool_size=1)
        
        # Pre-create a connection and add it to the pool to avoid the 10s timeout
        from src.email_dispatcher.connection_pool import SMTPConnection
        pre_conn = SMTPConnection(smtp_settings)
        pre_conn.connection = mock_smtp_instance  # Set the mock directly
        pre_conn.is_healthy = True
        pool.return_connection(pre_conn)
        
        # Send email
        try:
            result = send_email_with_pool(
                recipient='recipient@test.com',
                connection_pool=pool,
                general=general_settings,
                logger=mock_logger,
                template_path=temp_template,
                attachment_path=None,
                placeholders={'message': 'Test'}
            )
            
            assert result is True
            # Verify SMTP connection was created (either via mock or pre-populated)
            # Verify message was sent
            assert len(sent_messages) == 1
            assert sent_messages[0]['To'] == 'recipient@test.com'
            
        finally:
            pool.close_all()
    
    def test_send_email_dry_run(
        self,
        smtp_settings,
        general_settings,
        mock_logger,
        temp_template
    ):
        """Test email sending in dry-run mode."""
        general_settings['dry_run'] = True
        
        pool = SMTPConnectionPool(smtp_settings, pool_size=1)
        
        try:
            result = send_email_with_pool(
                recipient='recipient@test.com',
                connection_pool=pool,
                general=general_settings,
                logger=mock_logger,
                template_path=temp_template,
                attachment_path=None,
                placeholders={}
            )
            
            assert result is True
            # Should log dry-run message
            mock_logger.info.assert_called()
            
        finally:
            pool.close_all()


class TestConnectionPool:
    """Test SMTP connection pool."""
    
    def test_pool_initialization(self):
        """Test initializing connection pool."""
        settings = {
            'host': 'smtp.test.com',
            'port': 587,
            'username': 'test@test.com',
            'password': 'testpass',
            'use_tls': True,
            'use_auth': True
        }
        
        pool = SMTPConnectionPool(settings, pool_size=5)
        
        assert pool.pool_size == 5
        assert pool.created_count == 0
        
        pool.close_all()
    
    def test_pool_stats(self):
        """Test getting pool statistics."""
        settings = {
            'host': 'smtp.test.com',
            'port': 587,
            'username': 'test@test.com',
            'password': 'testpass',
            'use_tls': True,
            'use_auth': True
        }
        
        pool = SMTPConnectionPool(settings, pool_size=3)
        stats = pool.get_stats()
        
        assert 'current_size' in stats
        assert 'max_size' in stats
        assert stats['max_size'] == 3
        
        pool.close_all()

