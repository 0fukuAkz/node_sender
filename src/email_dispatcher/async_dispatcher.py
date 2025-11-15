"""
Async email dispatcher with asyncio support for higher throughput
"""

import asyncio
import aiosmtplib
import os
import mimetypes
from typing import Optional
from email.message import EmailMessage
from email.utils import formataddr, formatdate, make_msgid
from logging import Logger

from .identity import generate_identity
from .template import load_template, apply_placeholders
from .file_io import log_line
from .exceptions import (
    SMTPTransientError, SMTPPermanentError, TemplateError
)
from .types import (
    SMTPSettings, GeneralSettings, PlaceholderDict,
    ErrorType
)


def categorize_smtp_error_async(error: Exception) -> tuple[bool, ErrorType]:
    """
    Categorize SMTP errors as transient or permanent for async operations.
    
    Args:
        error: Exception from SMTP operation
        
    Returns:
        Tuple of (is_transient, error_type)
    """
    error_str = str(error).lower()
    
    # Transient errors that should be retried
    transient_keywords = [
        'timeout', 'temporarily', 'busy', 'try again',
        'rate limit', 'throttl', 'too many', '421', '450', '451', '452'
    ]
    
    # Permanent errors that should not be retried
    permanent_keywords = [
        'mailbox', 'does not exist', 'unknown user', 'invalid',
        'no such', 'disabled', 'blocked', 'spam', 'blacklist',
        '550', '551', '552', '553', '554'
    ]
    
    # Check for transient errors
    if any(keyword in error_str for keyword in transient_keywords):
        return True, 'transient'
    
    # Check for permanent errors
    if any(keyword in error_str for keyword in permanent_keywords):
        return False, 'permanent'
    
    # Check exception types
    if isinstance(error, (aiosmtplib.SMTPServerDisconnected, ConnectionError)):
        return True, 'connection_error'
    
    if isinstance(error, aiosmtplib.SMTPAuthenticationError):
        return False, 'authentication_error'
    
    if isinstance(error, aiosmtplib.SMTPRecipientsRefused):
        return False, 'permanent'
    
    if isinstance(error, aiosmtplib.SMTPDataError):
        return False, 'permanent'
    
    # Default to transient for unknown errors
    return True, 'unknown'


class AsyncSMTPConnection:
    """Async SMTP connection wrapper."""
    
    def __init__(self, smtp_settings: SMTPSettings):
        """
        Initialize async SMTP connection.
        
        Args:
            smtp_settings: SMTP configuration
        """
        self.smtp_settings = smtp_settings
        self.client: Optional[aiosmtplib.SMTP] = None
        self.is_connected = False
    
    async def connect(self) -> None:
        """Establish async SMTP connection."""
        self.client = aiosmtplib.SMTP(
            hostname=self.smtp_settings['host'],
            port=self.smtp_settings['port'],
            use_tls=(self.smtp_settings['port'] == 465)
        )
        
        await self.client.connect()
        
        # Start TLS if needed
        if self.smtp_settings.get('use_tls', True) and self.smtp_settings['port'] != 465:
            await self.client.starttls()
        
        # Authenticate
        if self.smtp_settings.get('use_auth', True):
            await self.client.login(
                self.smtp_settings['username'],
                self.smtp_settings['password']
            )
        
        self.is_connected = True
    
    async def send_message(self, msg: EmailMessage) -> None:
        """
        Send email message asynchronously.
        
        Args:
            msg: EmailMessage to send
        """
        if not self.is_connected or not self.client:
            await self.connect()
        
        await self.client.send_message(msg)
    
    async def close(self) -> None:
        """Close async SMTP connection."""
        if self.client:
            await self.client.quit()
            self.is_connected = False


class AsyncConnectionPool:
    """Async connection pool for SMTP connections."""
    
    def __init__(self, smtp_settings: SMTPSettings, pool_size: int = 5):
        """
        Initialize async connection pool.
        
        Args:
            smtp_settings: SMTP configuration
            pool_size: Maximum number of connections
        """
        self.smtp_settings = smtp_settings
        self.pool_size = pool_size
        self.connections: list[AsyncSMTPConnection] = []
        self.semaphore = asyncio.Semaphore(pool_size)
        self.lock = asyncio.Lock()
    
    async def get_connection(self) -> AsyncSMTPConnection:
        """
        Get connection from pool or create new one.
        
        Returns:
            AsyncSMTPConnection instance
        """
        async with self.lock:
            # Try to find available connection
            for conn in self.connections:
                if conn.is_connected:
                    return conn
            
            # Create new connection if pool not full
            if len(self.connections) < self.pool_size:
                conn = AsyncSMTPConnection(self.smtp_settings)
                await conn.connect()
                self.connections.append(conn)
                return conn
            
            # Use first connection if pool full
            if self.connections:
                conn = self.connections[0]
                if not conn.is_connected:
                    await conn.connect()
                return conn
            
            # Create first connection
            conn = AsyncSMTPConnection(self.smtp_settings)
            await conn.connect()
            self.connections.append(conn)
            return conn
    
    async def close_all(self) -> None:
        """Close all connections in pool."""
        async with self.lock:
            for conn in self.connections:
                await conn.close()
            self.connections.clear()


async def send_email_async(
    recipient: str,
    smtp_settings: SMTPSettings,
    general: GeneralSettings,
    logger: Logger,
    template_path: str,
    attachment_path: Optional[str],
    placeholders: PlaceholderDict,
    correlation_id: Optional[str] = None,
    connection_pool: Optional[AsyncConnectionPool] = None
) -> bool:
    """
    Send email asynchronously.
    
    Args:
        recipient: Email address to send to
        smtp_settings: SMTP configuration
        general: General settings
        logger: Logger instance
        template_path: Path to email template
        attachment_path: Path to attachment (optional)
        placeholders: Template placeholder values
        correlation_id: Correlation ID for tracking
        connection_pool: Optional connection pool
        
    Returns:
        True if sent successfully, False otherwise
        
    Raises:
        SMTPTransientError: For transient errors that should be retried
        SMTPPermanentError: For permanent errors that should not be retried
    """
    try:
        # Identity generation and placeholder merging
        identity = generate_identity()
        merged = {**placeholders, 'recipient': recipient, **identity}
        
        # Use correlation ID from identity if not provided
        if not correlation_id:
            correlation_id = identity['uuid']
        
        # Load and render template
        try:
            html = apply_placeholders(load_template(template_path), merged)
        except Exception as e:
            raise TemplateError(f"Template processing failed: {e}")
        
        # Email construction
        from_email = general.get('from_email', smtp_settings.get('username', identity['email']))
        from_name = identity['full_name']
        subject = apply_placeholders(general['subject'], merged)
        
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = formataddr((from_name, from_email))
        msg['To'] = recipient
        
        if general.get('reply_to'):
            msg['Reply-To'] = general['reply_to']
        
        msg['Date'] = formatdate(localtime=True)
        msg['Message-ID'] = make_msgid()
        
        if general.get('list_unsubscribe'):
            msg['List-Unsubscribe'] = general['list_unsubscribe']
        
        # Add correlation ID as custom header
        msg['X-Correlation-ID'] = correlation_id
        
        msg.set_content("This message requires HTML support.")
        msg.add_alternative(html, subtype='html')
        
        # Attachment (optional)
        if attachment_path and os.path.exists(attachment_path):
            with open(attachment_path, 'rb') as f:
                data = f.read()
            ctype, _ = mimetypes.guess_type(attachment_path)
            if ctype is None:
                maintype, subtype = 'application', 'octet-stream'
            else:
                maintype, subtype = ctype.split('/', 1)
            msg.add_attachment(
                data,
                maintype=maintype,
                subtype=subtype,
                filename=os.path.basename(attachment_path),
            )
        
        # SMTP delivery
        if general.get('dry_run'):
            logger.info(
                f"[DRY-RUN] Would send to {recipient}: {subject}",
                extra={'email_address': recipient, 'correlation_id': correlation_id}
            )
            log_line(os.path.join(general['log_path'], 'success-emails.txt'), recipient)
            return True
        
        # Send using connection pool or create new connection
        try:
            if connection_pool:
                conn = await connection_pool.get_connection()
                await conn.send_message(msg)
            else:
                async with aiosmtplib.SMTP(
                    hostname=smtp_settings['host'],
                    port=smtp_settings['port'],
                    use_tls=(smtp_settings['port'] == 465)
                ) as smtp:
                    if smtp_settings.get('use_tls', True) and smtp_settings['port'] != 465:
                        await smtp.starttls()
                    
                    if smtp_settings.get('use_auth', True):
                        await smtp.login(
                            smtp_settings['username'],
                            smtp_settings['password']
                        )
                    
                    await smtp.send_message(msg)
            
            # Log success
            log_line(os.path.join(general['log_path'], 'success-emails.txt'), recipient)
            logger.info(
                f"✅ Sent to {recipient}",
                extra={'email_address': recipient, 'correlation_id': correlation_id}
            )
            return True
            
        except Exception as smtp_error:
            # Categorize error
            is_transient, error_type = categorize_smtp_error_async(smtp_error)
            
            # Log failure
            log_line(
                os.path.join(general['log_path'], 'failed-emails.txt'),
                f"{recipient} - {error_type} - {str(smtp_error)}"
            )
            
            logger.error(
                f"❌ Failed to send to {recipient}: {smtp_error}",
                extra={
                    'email_address': recipient,
                    'correlation_id': correlation_id,
                    'error_type': error_type
                }
            )
            
            # Raise appropriate exception
            if is_transient:
                raise SMTPTransientError(f"{error_type}: {smtp_error}")
            else:
                raise SMTPPermanentError(f"{error_type}: {smtp_error}")
    
    except (SMTPTransientError, SMTPPermanentError):
        # Re-raise categorized errors
        raise
    
    except Exception as e:
        # Log unexpected errors
        log_line(
            os.path.join(general['log_path'], 'failed-emails.txt'),
            f"{recipient} - unexpected - {str(e)}"
        )
        
        logger.error(
            f"❌ Unexpected error sending to {recipient}: {e}",
            extra={
                'email_address': recipient,
                'correlation_id': correlation_id or 'unknown',
                'error_type': 'unexpected'
            },
            exc_info=True
        )
        
        # Treat unexpected errors as transient
        raise SMTPTransientError(f"Unexpected error: {e}")


async def send_bulk_emails_async(
    recipients: list[str],
    smtp_settings: SMTPSettings,
    general: GeneralSettings,
    logger: Logger,
    template_path: str,
    attachment_path: Optional[str],
    placeholders: PlaceholderDict,
    concurrency: int = 10
) -> tuple[int, int]:
    """
    Send bulk emails asynchronously with controlled concurrency.
    
    Args:
        recipients: List of email addresses
        smtp_settings: SMTP configuration
        general: General settings
        logger: Logger instance
        template_path: Path to email template
        attachment_path: Path to attachment (optional)
        placeholders: Template placeholder values
        concurrency: Maximum concurrent sends
        
    Returns:
        Tuple of (success_count, failure_count)
    """
    semaphore = asyncio.Semaphore(concurrency)
    connection_pool = AsyncConnectionPool(smtp_settings, pool_size=min(concurrency, 5))
    
    success_count = 0
    failure_count = 0
    
    async def send_with_semaphore(recipient: str) -> bool:
        """Send email with semaphore control."""
        nonlocal success_count, failure_count
        
        async with semaphore:
            try:
                result = await send_email_async(
                    recipient=recipient,
                    smtp_settings=smtp_settings,
                    general=general,
                    logger=logger,
                    template_path=template_path,
                    attachment_path=attachment_path,
                    placeholders=placeholders,
                    connection_pool=connection_pool
                )
                if result:
                    success_count += 1
                else:
                    failure_count += 1
                return result
            except Exception:
                failure_count += 1
                return False
    
    # Send all emails concurrently
    tasks = [send_with_semaphore(recipient) for recipient in recipients]
    await asyncio.gather(*tasks, return_exceptions=True)
    
    # Close connection pool
    await connection_pool.close_all()
    
    return success_count, failure_count

