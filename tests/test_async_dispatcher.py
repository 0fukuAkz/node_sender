"""
Tests for async email dispatcher
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from src.email_dispatcher.async_dispatcher import (
    send_email_async,
    send_bulk_emails_async,
    AsyncSMTPConnection,
    AsyncConnectionPool,
    categorize_smtp_error_async
)
from src.email_dispatcher.types import SMTPSettings, GeneralSettings, PlaceholderDict
from src.email_dispatcher.exceptions import SMTPTransientError, SMTPPermanentError


@pytest.fixture
def smtp_settings() -> SMTPSettings:
    """Fixture for SMTP settings."""
    return {
        'host': 'smtp.example.com',
        'port': 587,
        'username': 'test@example.com',
        'password': 'password123',
        'use_tls': True,
        'use_auth': True
    }


@pytest.fixture
def general_settings() -> GeneralSettings:
    """Fixture for general settings."""
    return {
        'dry_run': True,
        'subject': 'Test Subject',
        'from_email': 'test@example.com',
        'log_path': 'logs',
        'template_path': 'templates/message.html',
        'attachment_path': '',
        'reply_to': '',
        'list_unsubscribe': '',
        'mode': 'relay',
        'concurrency': 10,
        'retry_limit': 2,
        'rate_per_minute': 0,
        'rate_per_hour': 0,
        'leads_path': 'data/leads.txt',
        'suppression_path': 'data/suppressions.txt'
    }


@pytest.fixture
def placeholders() -> PlaceholderDict:
    """Fixture for placeholders."""
    return {
        'company': 'Test Company',
        'product': 'Test Product'
    }


class TestCategorizeSmtpErrorAsync:
    """Tests for error categorization."""
    
    def test_transient_timeout(self):
        """Test timeout error is categorized as transient."""
        error = Exception('Connection timeout')
        is_transient, error_type = categorize_smtp_error_async(error)
        
        assert is_transient is True
        assert error_type == 'transient'
    
    def test_permanent_mailbox_error(self):
        """Test mailbox error is categorized as permanent."""
        error = Exception('Mailbox does not exist')
        is_transient, error_type = categorize_smtp_error_async(error)
        
        assert is_transient is False
        assert error_type == 'permanent'
    
    def test_unknown_error_defaults_transient(self):
        """Test unknown error defaults to transient."""
        error = Exception('Unknown error')
        is_transient, error_type = categorize_smtp_error_async(error)
        
        assert is_transient is True
        assert error_type == 'unknown'


class TestAsyncSMTPConnection:
    """Tests for AsyncSMTPConnection."""
    
    @pytest.mark.asyncio
    async def test_connection_initialization(self, smtp_settings):
        """Test async connection initialization."""
        conn = AsyncSMTPConnection(smtp_settings)
        
        assert conn.smtp_settings == smtp_settings
        assert conn.is_connected is False
        assert conn.client is None
    
    @pytest.mark.asyncio
    async def test_connect_success(self, smtp_settings):
        """Test successful connection."""
        conn = AsyncSMTPConnection(smtp_settings)
        
        with patch('aiosmtplib.SMTP') as mock_smtp:
            mock_client = AsyncMock()
            mock_smtp.return_value = mock_client
            
            await conn.connect()
            
            assert conn.is_connected is True


class TestAsyncConnectionPool:
    """Tests for AsyncConnectionPool."""
    
    @pytest.mark.asyncio
    async def test_pool_initialization(self, smtp_settings):
        """Test connection pool initialization."""
        pool = AsyncConnectionPool(smtp_settings, pool_size=3)
        
        assert pool.smtp_settings == smtp_settings
        assert pool.pool_size == 3
        assert len(pool.connections) == 0
    
    @pytest.mark.asyncio
    async def test_get_connection_creates_new(self, smtp_settings):
        """Test getting connection creates new one when pool is empty."""
        pool = AsyncConnectionPool(smtp_settings, pool_size=3)
        
        with patch.object(AsyncSMTPConnection, 'connect', new_callable=AsyncMock):
            conn = await pool.get_connection()
            
            assert conn is not None
            assert len(pool.connections) == 1
    
    @pytest.mark.asyncio
    async def test_close_all_connections(self, smtp_settings):
        """Test closing all connections."""
        pool = AsyncConnectionPool(smtp_settings, pool_size=2)
        
        with patch.object(AsyncSMTPConnection, 'connect', new_callable=AsyncMock):
            with patch.object(AsyncSMTPConnection, 'close', new_callable=AsyncMock):
                # Create connections
                await pool.get_connection()
                await pool.get_connection()
                
                # Close all
                await pool.close_all()
                
                assert len(pool.connections) == 0


class TestSendEmailAsync:
    """Tests for send_email_async function."""
    
    @pytest.mark.asyncio
    async def test_send_email_dry_run(
        self,
        smtp_settings,
        general_settings,
        placeholders
    ):
        """Test sending email in dry run mode."""
        logger = Mock()
        
        with patch('src.email_dispatcher.async_dispatcher.load_template', return_value='<html>Test</html>'):
            with patch('src.email_dispatcher.async_dispatcher.apply_placeholders', return_value='<html>Test</html>'):
                result = await send_email_async(
                    recipient='test@example.com',
                    smtp_settings=smtp_settings,
                    general=general_settings,
                    logger=logger,
                    template_path='templates/message.html',
                    attachment_path=None,
                    placeholders=placeholders
                )
                
                assert result is True
                logger.info.assert_called()
    
    @pytest.mark.asyncio
    async def test_send_email_template_error(
        self,
        smtp_settings,
        general_settings,
        placeholders
    ):
        """Test template error raises TemplateError."""
        logger = Mock()
        general_settings['dry_run'] = False
        
        with patch('src.email_dispatcher.async_dispatcher.load_template', side_effect=Exception('Template not found')):
            with pytest.raises(SMTPTransientError):
                await send_email_async(
                    recipient='test@example.com',
                    smtp_settings=smtp_settings,
                    general=general_settings,
                    logger=logger,
                    template_path='templates/message.html',
                    attachment_path=None,
                    placeholders=placeholders
                )


class TestSendBulkEmailsAsync:
    """Tests for send_bulk_emails_async function."""
    
    @pytest.mark.asyncio
    async def test_send_bulk_emails(
        self,
        smtp_settings,
        general_settings,
        placeholders
    ):
        """Test sending bulk emails asynchronously."""
        logger = Mock()
        recipients = ['user1@example.com', 'user2@example.com', 'user3@example.com']
        
        with patch('src.email_dispatcher.async_dispatcher.send_email_async', new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True
            
            success_count, failure_count = await send_bulk_emails_async(
                recipients=recipients,
                smtp_settings=smtp_settings,
                general=general_settings,
                logger=logger,
                template_path='templates/message.html',
                attachment_path=None,
                placeholders=placeholders,
                concurrency=5
            )
            
            assert success_count == 3
            assert failure_count == 0
            assert mock_send.call_count == 3
    
    @pytest.mark.asyncio
    async def test_send_bulk_emails_with_failures(
        self,
        smtp_settings,
        general_settings,
        placeholders
    ):
        """Test sending bulk emails with some failures."""
        logger = Mock()
        recipients = ['user1@example.com', 'user2@example.com', 'user3@example.com']
        
        # Mock send to fail for second recipient
        async def mock_send_side_effect(*args, **kwargs):
            if kwargs.get('recipient') == 'user2@example.com':
                raise SMTPPermanentError('Failed')
            return True
        
        with patch('src.email_dispatcher.async_dispatcher.send_email_async', new_callable=AsyncMock) as mock_send:
            mock_send.side_effect = mock_send_side_effect
            
            success_count, failure_count = await send_bulk_emails_async(
                recipients=recipients,
                smtp_settings=smtp_settings,
                general=general_settings,
                logger=logger,
                template_path='templates/message.html',
                attachment_path=None,
                placeholders=placeholders,
                concurrency=5
            )
            
            assert success_count == 2
            assert failure_count == 1

