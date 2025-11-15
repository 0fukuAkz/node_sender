#!/usr/bin/env python3
"""
Example: Analytics and reporting for email campaigns
"""

import time
import logging
from src.email_dispatcher import (
    AnalyticsCollector,
    init_logger
)


def main():
    """Main function demonstrating analytics and reporting."""
    # Initialize logger
    logger = init_logger('logs', structured=False)
    
    # Initialize analytics collector
    analytics = AnalyticsCollector(
        db_path='logs/analytics.db',
        logger=logger
    )
    
    logger.info("=" * 60)
    logger.info("Analytics and Reporting Example")
    logger.info("=" * 60)
    
    campaign_id = 'campaign_demo_2024'
    
    # Simulate campaign events
    logger.info(f"\nSimulating campaign: {campaign_id}")
    
    recipients = [
        'user1@example.com',
        'user2@example.com',
        'user3@example.com',
        'user4@example.com',
        'user5@example.com'
    ]
    
    variants = ['control', 'variant_a', 'variant_b']
    
    # Simulate sends
    logger.info("\nTracking send events...")
    for i, recipient in enumerate(recipients):
        variant = variants[i % len(variants)]
        success = i % 4 != 0  # Simulate 25% failure rate
        
        analytics.track_send(
            email=recipient,
            campaign_id=campaign_id,
            success=success,
            variant_name=variant,
            metadata={'send_time': time.time()}
        )
        
        logger.info(f"  {recipient} → {variant} ({'✅ sent' if success else '❌ failed'})")
    
    # Simulate engagement events
    logger.info("\nTracking engagement events...")
    
    # Opens
    for recipient in recipients[:4]:
        variant = variants[recipients.index(recipient) % len(variants)]
        analytics.track_open(
            email=recipient,
            campaign_id=campaign_id,
            variant_name=variant,
            metadata={'user_agent': 'Mozilla/5.0'}
        )
        logger.info(f"  📧 Open: {recipient}")
    
    # Clicks
    for recipient in recipients[:3]:
        variant = variants[recipients.index(recipient) % len(variants)]
        analytics.track_click(
            email=recipient,
            campaign_id=campaign_id,
            variant_name=variant,
            url='https://example.com/offer',
            metadata={'click_time': time.time()}
        )
        logger.info(f"  🖱️  Click: {recipient}")
    
    # Conversions
    for recipient in recipients[:2]:
        variant = variants[recipients.index(recipient) % len(variants)]
        analytics.track_conversion(
            email=recipient,
            campaign_id=campaign_id,
            variant_name=variant,
            value=99.99,
            metadata={'product_id': 'WIDGET-PRO'}
        )
        logger.info(f"  💰 Conversion: {recipient}")
    
    # Bounce
    analytics.track_bounce(
        email=recipients[4],
        campaign_id=campaign_id,
        bounce_type='hard',
        metadata={'bounce_reason': 'Mailbox does not exist'}
    )
    logger.info(f"  ⚠️  Bounce: {recipients[4]}")
    
    # Get campaign statistics
    logger.info("\n" + "=" * 60)
    logger.info("Campaign Statistics")
    logger.info("=" * 60)
    
    stats = analytics.get_campaign_stats(campaign_id)
    
    logger.info(f"\nTotal Emails: {stats['total_emails']}")
    logger.info(f"Sent Successfully: {stats['completed_emails']}")
    logger.info(f"Failed: {stats['failed_emails']}")
    logger.info(f"Elapsed Time: {stats['elapsed_seconds']:.2f}s")
    
    # Get variant-specific statistics
    logger.info("\n" + "=" * 60)
    logger.info("Variant Performance")
    logger.info("=" * 60)
    
    for variant in variants:
        variant_stats = analytics.get_variant_stats(campaign_id, variant)
        
        logger.info(f"\nVariant: {variant}")
        logger.info(f"  Sent: {variant_stats['sent']}")
        logger.info(f"  Failed: {variant_stats['failed']}")
        logger.info(f"  Opens: {variant_stats['opens']}")
        logger.info(f"  Clicks: {variant_stats['clicks']}")
        logger.info(f"  Conversions: {variant_stats['conversions']}")
        logger.info(f"  Open Rate: {variant_stats['open_rate']*100:.1f}%")
        logger.info(f"  Click Rate: {variant_stats['click_rate']*100:.1f}%")
        logger.info(f"  Conversion Rate: {variant_stats['conversion_rate']*100:.1f}%")
    
    # Generate comprehensive report
    logger.info("\n" + "=" * 60)
    logger.info("Comprehensive Report")
    logger.info("=" * 60)
    
    report = analytics.generate_report(campaign_id, include_variants=True)
    
    logger.info(f"\nCampaign ID: {report['campaign_id']}")
    logger.info(f"Duration: {report['end_time'] - report['start_time']:.2f}s")
    logger.info(f"Total Sent: {report['total_sent']}")
    logger.info(f"Total Failed: {report['total_failed']}")
    logger.info(f"Success Rate: {report['success_rate']*100:.1f}%")
    
    if report['variants']:
        logger.info("\nVariant Breakdown:")
        for variant in report['variants']:
            logger.info(f"  {variant['name']}:")
            logger.info(f"    Sent: {variant['sent']}")
            logger.info(f"    Opens: {variant['opens']} ({variant['open_rate']*100:.1f}%)")
            logger.info(f"    Clicks: {variant['clicks']} ({variant['click_rate']*100:.1f}%)")
            logger.info(f"    Conversions: {variant['conversions']} ({variant['conversion_rate']*100:.1f}%)")
    
    if report['errors']:
        logger.info("\nError Breakdown:")
        for error in report['errors']:
            logger.info(f"  {error['error_type']}: {error['count']}")
    
    # Export events to JSON
    logger.info("\n" + "=" * 60)
    logger.info("Exporting Data")
    logger.info("=" * 60)
    
    export_path = f'logs/campaign_{campaign_id}_events.json'
    analytics.export_events(campaign_id, export_path, format='json')
    logger.info(f"\n✅ Events exported to: {export_path}")
    
    # Get time series data
    logger.info("\n" + "=" * 60)
    logger.info("Time Series Analysis")
    logger.info("=" * 60)
    
    time_series = analytics.get_time_series(
        campaign_id=campaign_id,
        event_type='send_success',
        interval_seconds=3600  # 1 hour buckets
    )
    
    if time_series:
        logger.info("\nSends over time (hourly):")
        for data_point in time_series:
            logger.info(f"  {data_point['timestamp']}: {data_point['count']} sends")
    
    logger.info("\n✅ Analytics example complete!")


if __name__ == '__main__':
    main()

