"""
Enhanced email dispatcher with connection pooling and error categorization
"""

import os
import smtplib
import mimetypes
from typing import Dict, Optional
from email.message import EmailMessage
from email.utils import formataddr, formatdate, make_msgid

from .identity import generate_identity
from .template import load_template, apply_placeholders
from .file_io import log_line
from .connection_pool import SMTPConnectionPool, ConnectionPoolContextManager
from .exceptions import (
    SMTPTransientError, SMTPPermanentError, SMTPConnectionError,
    SMTPAuthenticationError, TemplateError
)


def categorize_smtp_error(error: Exception) -> tuple[bool, str]:
    """
    Categorize SMTP errors as transient or permanent.
    
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
    if isinstance(error, (smtplib.SMTPServerDisconnected, smtplib.SMTPConnectError)):
        return True, 'connection_error'
    
    if isinstance(error, smtplib.SMTPAuthenticationError):
        return False, 'authentication_error'
    
    if isinstance(error, smtplib.SMTPRecipientsRefused):
        return False, 'recipient_refused'
    
    if isinstance(error, smtplib.SMTPDataError):
        return False, 'data_error'
    
    # Default to transient for unknown errors
    return True, 'unknown'


def send_email_with_pool(
    recipient: str,
    connection_pool: SMTPConnectionPool,
    general: Dict,
    logger,
    template_path: str,
    attachment_path: Optional[str],
    placeholders: Dict,
    correlation_id: Optional[str] = None
) -> bool:
    """
    Send email using connection pool.
    
    Args:
        recipient: Email address to send to
        connection_pool: SMTP connection pool
        general: General settings dictionary
        logger: Logger instance
        template_path: Path to email template
        attachment_path: Path to attachment (optional)
        placeholders: Template placeholder values
        correlation_id: Correlation ID for tracking
        
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
        from_email = general.get('from_email', general.get('smtp_username', identity['email']))
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
        
        # Use connection pool to send
        try:
            with ConnectionPoolContextManager(connection_pool, timeout=10.0) as conn:
                conn.send_message(msg)
            
            # Log success
            log_line(os.path.join(general['log_path'], 'success-emails.txt'), recipient)
            logger.info(
                f"✅ Sent to {recipient}",
                extra={'email_address': recipient, 'correlation_id': correlation_id}
            )
            return True
            
        except Exception as smtp_error:
            # Categorize error
            is_transient, error_type = categorize_smtp_error(smtp_error)
            
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
                'correlation_id': correlation_id,
                'error_type': 'unexpected'
            },
            exc_info=True
        )
        
        # Treat unexpected errors as transient
        raise SMTPTransientError(f"Unexpected error: {e}")


# Maintain backward compatibility with old function signature
def send_email(recipient, smtp, general, logger, template_path, attachment_path, placeholders):
    """
    Legacy send_email function for backward compatibility.
    Creates a temporary connection pool for single email.
    
    Note: For production use, use send_email_with_pool with shared connection pool.
    """
    from connection_pool import SMTPConnectionPool
    
    # Create temporary connection pool
    pool = SMTPConnectionPool(smtp, pool_size=1)
    
    try:
        return send_email_with_pool(
            recipient=recipient,
            connection_pool=pool,
            general=general,
            logger=logger,
            template_path=template_path,
            attachment_path=attachment_path,
            placeholders=placeholders
        )
    except (SMTPTransientError, SMTPPermanentError):
        return False
    except Exception:
        return False
    finally:
        pool.close_all()
