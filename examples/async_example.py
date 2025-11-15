#!/usr/bin/env python3
"""
Example: Async email sending with asyncio for higher throughput
"""

import asyncio
import logging
from src.email_dispatcher import (
    send_bulk_emails_async,
    SMTPSettings,
    GeneralSettings,
    PlaceholderDict
)


async def main():
    """Main async function."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    # SMTP configuration
    smtp_settings: SMTPSettings = {
        'host': 'smtp.gmail.com',
        'port': 587,
        'username': 'your@gmail.com',
        'password': 'your_app_password',
        'use_tls': True,
        'use_auth': True
    }
    
    # General settings
    general: GeneralSettings = {
        'dry_run': True,
        'subject': 'Hello from {company}!',
        'from_email': 'your@gmail.com',
        'log_path': 'logs',
        'template_path': 'templates/message.html',
        'attachment_path': '',
        'leads_path': 'data/leads.txt',
        'suppression_path': 'data/suppressions.txt',
        'reply_to': '',
        'list_unsubscribe': '',
        'mode': 'relay',
        'concurrency': 20,
        'retry_limit': 2,
        'rate_per_minute': 0,
        'rate_per_hour': 0
    }
    
    # Placeholder values
    placeholders: PlaceholderDict = {
        'company': 'Acme Corp',
        'product': 'Widget Pro',
        'offer': '50% off'
    }
    
    # Recipients
    recipients = [
        'user1@example.com',
        'user2@example.com',
        'user3@example.com'
    ]
    
    logger.info("Starting async bulk email send...")
    logger.info(f"Recipients: {len(recipients)}")
    logger.info(f"Concurrency: 20")
    
    # Send emails asynchronously
    success_count, failure_count = await send_bulk_emails_async(
        recipients=recipients,
        smtp_settings=smtp_settings,
        general=general,
        logger=logger,
        template_path=general['template_path'],
        attachment_path=general.get('attachment_path'),
        placeholders=placeholders,
        concurrency=20  # High concurrency with async
    )
    
    logger.info(f"✅ Completed! Success: {success_count}, Failed: {failure_count}")


if __name__ == '__main__':
    asyncio.run(main())

