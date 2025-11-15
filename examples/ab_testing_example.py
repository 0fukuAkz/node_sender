#!/usr/bin/env python3
"""
Example: A/B testing for email campaigns
"""

import logging
from src.email_dispatcher import (
    ABTestManager,
    ABTestConfig,
    send_email_with_pool,
    init_logger
)
from src.email_dispatcher.connection_pool import SMTPConnectionPool


def main():
    """Main function demonstrating A/B testing."""
    # Initialize logger
    logger = init_logger('logs', structured=False)
    
    # Configure A/B test
    ab_test_config: ABTestConfig = {
        'test_name': 'Subject Line Test',
        'control_variant': 'control',
        'variants': [
            {
                'name': 'control',
                'weight': 0.4,  # 40% of recipients
                'template_path': 'templates/message.html',
                'subject': 'Important Update from {company}',
                'metadata': {'description': 'Original subject line'}
            },
            {
                'name': 'variant_a',
                'weight': 0.3,  # 30% of recipients
                'template_path': 'templates/message.html',
                'subject': '🎉 Special Offer from {company}!',
                'metadata': {'description': 'Emoji + excitement'}
            },
            {
                'name': 'variant_b',
                'weight': 0.3,  # 30% of recipients
                'template_path': 'templates/message.html',
                'subject': 'You\'ve been selected for {company} VIP access',
                'metadata': {'description': 'Exclusivity angle'}
            }
        ]
    }
    
    # Initialize A/B test manager
    ab_test = ABTestManager(config=ab_test_config, logger=logger)
    
    logger.info("=" * 60)
    logger.info("A/B Testing Example")
    logger.info("=" * 60)
    logger.info(f"Test Name: {ab_test_config['test_name']}")
    logger.info(f"Variants: {len(ab_test_config['variants'])}")
    logger.info(f"Control: {ab_test_config['control_variant']}")
    
    # Example recipients
    recipients = [
        'user1@example.com',
        'user2@example.com',
        'user3@example.com',
        'user4@example.com',
        'user5@example.com',
        'user6@example.com',
        'user7@example.com',
        'user8@example.com',
        'user9@example.com',
        'user10@example.com'
    ]
    
    # SMTP configuration
    smtp_settings = {
        'host': 'smtp.gmail.com',
        'port': 587,
        'username': 'your@gmail.com',
        'password': 'your_app_password',
        'use_tls': True,
        'use_auth': True
    }
    
    # General settings (template for all variants)
    general_base = {
        'dry_run': True,
        'from_email': 'noreply@example.com',
        'log_path': 'logs',
        'attachment_path': '',
        'reply_to': '',
        'list_unsubscribe': ''
    }
    
    placeholders = {
        'company': 'Acme Corp',
        'product': 'Widget Pro',
        'offer': '50% discount'
    }
    
    # Create connection pool
    connection_pool = SMTPConnectionPool(
        smtp_settings=smtp_settings,
        pool_size=2
    )
    
    logger.info("\nSending emails with variant assignments...")
    
    try:
        for recipient in recipients:
            # Assign variant to recipient
            variant = ab_test.assign_variant(recipient)
            
            logger.info(f"\n{recipient} → Variant: {variant['name']}")
            logger.info(f"  Subject: {variant['subject']}")
            
            # Prepare settings with variant-specific values
            general = {
                **general_base,
                'subject': variant['subject'],
                'template_path': variant['template_path']
            }
            
            # Send email
            try:
                success = send_email_with_pool(
                    recipient=recipient,
                    connection_pool=connection_pool,
                    general=general,
                    logger=logger,
                    template_path=variant['template_path'],
                    attachment_path=general['attachment_path'],
                    placeholders=placeholders
                )
                
                # Record send result
                ab_test.record_send(recipient, success=success)
                
                # Simulate engagement events (in real scenario, these would come from tracking pixels)
                if success:
                    # Simulate some opens
                    import random
                    if random.random() > 0.3:  # 70% open rate
                        ab_test.record_open(recipient)
                        
                        # Simulate some clicks
                        if random.random() > 0.5:  # 50% click rate of opens
                            ab_test.record_click(recipient)
                            
                            # Simulate some conversions
                            if random.random() > 0.7:  # 30% conversion rate of clicks
                                ab_test.record_conversion(recipient)
                
            except Exception as e:
                logger.error(f"Error sending to {recipient}: {e}")
                ab_test.record_send(recipient, success=False)
    
    finally:
        connection_pool.close_all()
    
    # Display results
    logger.info("\n" + "=" * 60)
    logger.info("A/B Test Results")
    logger.info("=" * 60)
    
    logger.info("\n" + ab_test.format_summary())
    
    # Get detailed results
    results = ab_test.get_results()
    
    # Compare variants
    logger.info("\n" + "=" * 60)
    logger.info("Statistical Comparison")
    logger.info("=" * 60)
    
    control = ab_test_config['control_variant']
    for variant in ab_test_config['variants']:
        if variant['name'] != control:
            p_value = ab_test.get_statistical_significance(
                control,
                variant['name'],
                metric='conversion_rate'
            )
            
            if p_value is not None:
                significance = "Significant" if p_value < 0.05 else "Not significant"
                logger.info(f"\n{control} vs {variant['name']}:")
                logger.info(f"  P-value: {p_value:.3f}")
                logger.info(f"  Result: {significance}")
    
    # Export results
    export_data = ab_test.export_results()
    logger.info(f"\n✅ Test complete! Winner: {export_data['winner']}")


if __name__ == '__main__':
    main()

