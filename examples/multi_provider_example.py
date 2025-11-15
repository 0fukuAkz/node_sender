#!/usr/bin/env python3
"""
Example: Multiple SMTP providers with load balancing
"""

import logging
from src.email_dispatcher import (
    SMTPProviderManager,
    SMTPProviderConfig,
    send_email_with_pool,
    init_logger
)
from src.email_dispatcher.connection_pool import SMTPConnectionPool


def main():
    """Main function demonstrating multi-provider load balancing."""
    # Initialize logger
    logger = init_logger('logs', structured=False)
    
    # Configure multiple SMTP providers
    providers: list[SMTPProviderConfig] = [
        {
            'name': 'Gmail Primary',
            'priority': 10,
            'weight': 50,
            'enabled': True,
            'smtp_settings': {
                'host': 'smtp.gmail.com',
                'port': 587,
                'username': 'primary@gmail.com',
                'password': 'app_password_1',
                'use_tls': True,
                'use_auth': True
            },
            'max_emails_per_hour': 500,
            'max_emails_per_day': 2000
        },
        {
            'name': 'Gmail Secondary',
            'priority': 5,
            'weight': 30,
            'enabled': True,
            'smtp_settings': {
                'host': 'smtp.gmail.com',
                'port': 587,
                'username': 'secondary@gmail.com',
                'password': 'app_password_2',
                'use_tls': True,
                'use_auth': True
            },
            'max_emails_per_hour': 300,
            'max_emails_per_day': 1000
        },
        {
            'name': 'Outlook Backup',
            'priority': 1,
            'weight': 20,
            'enabled': True,
            'smtp_settings': {
                'host': 'smtp-mail.outlook.com',
                'port': 587,
                'username': 'backup@outlook.com',
                'password': 'app_password_3',
                'use_tls': True,
                'use_auth': True
            },
            'max_emails_per_hour': 200,
            'max_emails_per_day': 500
        }
    ]
    
    # Initialize provider manager with load balancing strategy
    provider_manager = SMTPProviderManager(
        providers=providers,
        strategy='weighted',  # Options: round_robin, weighted, priority, least_loaded, random
        logger=logger
    )
    
    logger.info("=" * 60)
    logger.info("Multi-Provider Load Balancing Example")
    logger.info("=" * 60)
    logger.info(f"Strategy: weighted")
    logger.info(f"Total Providers: {len(providers)}")
    
    # Example: Send emails using different providers
    recipients = [
        'user1@example.com',
        'user2@example.com',
        'user3@example.com',
        'user4@example.com',
        'user5@example.com'
    ]
    
    general = {
        'dry_run': True,
        'subject': 'Test Email',
        'from_email': 'noreply@example.com',
        'log_path': 'logs',
        'template_path': 'templates/message.html',
        'attachment_path': '',
        'reply_to': '',
        'list_unsubscribe': ''
    }
    
    placeholders = {
        'company': 'Test Company',
        'product': 'Test Product'
    }
    
    for recipient in recipients:
        # Get next provider based on strategy
        provider = provider_manager.get_provider()
        
        if not provider:
            logger.warning("No providers available!")
            break
        
        logger.info(f"Using provider: {provider.name} for {recipient}")
        
        # Create connection pool for this provider
        connection_pool = SMTPConnectionPool(
            smtp_settings=provider.smtp_settings,
            pool_size=1
        )
        
        try:
            # Send email
            success = send_email_with_pool(
                recipient=recipient,
                connection_pool=connection_pool,
                general=general,
                logger=logger,
                template_path=general['template_path'],
                attachment_path=general['attachment_path'],
                placeholders=placeholders
            )
            
            # Record send result
            provider.record_send(success=success)
            
        finally:
            connection_pool.close_all()
    
    # Display provider statistics
    logger.info("\n" + "=" * 60)
    logger.info("Provider Statistics")
    logger.info("=" * 60)
    
    for stats in provider_manager.get_all_stats():
        logger.info(f"\nProvider: {stats['name']}")
        logger.info(f"  Status: {'Enabled' if stats['enabled'] else 'Disabled'}")
        logger.info(f"  Total Sent: {stats['total_sent']}")
        logger.info(f"  Total Failed: {stats['total_failed']}")
        logger.info(f"  Emails This Hour: {stats['emails_sent_hour']}")
        logger.info(f"  Emails Today: {stats['emails_sent_day']}")
        logger.info(f"  Current Load: {stats['current_load']*100:.1f}%")


if __name__ == '__main__':
    main()

