"""
Production-grade bulk email dispatcher with advanced features
"""

import argparse
import os
import re
import time
import uuid
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from src.email_dispatcher import Config, init_logger
from src.email_dispatcher.proxy import apply_proxy
from src.email_dispatcher.file_io import read_lines, read_lines_chunked, clear_file
from src.email_dispatcher.dispatcher import send_email_with_pool
from src.email_dispatcher.connection_pool import SMTPConnectionPool
from src.email_dispatcher.rate_limiter import RateLimiter
from src.email_dispatcher.state_manager import StateManager, EmailState
from src.email_dispatcher.retry_queue import RetryQueue, RetryItem
from src.email_dispatcher.metrics import MetricsCollector, ProgressBar
from src.email_dispatcher.exceptions import (
    SMTPTransientError, SMTPPermanentError, PathSecurityError,
    ConfigurationError
)


def parse_args():
    parser = argparse.ArgumentParser(description="Production bulk email dispatcher")
    parser.add_argument('--config', default='email_config.ini', help='Path to INI config')
    parser.add_argument('--dry-run', action='store_true', help='Enable dry run')
    parser.add_argument('--concurrency', type=int, help='Override concurrency')
    parser.add_argument('--rate-per-minute', type=int, help='Throttle rate per minute (0 = unlimited)')
    parser.add_argument('--rate-per-hour', type=int, help='Throttle rate per hour (0 = unlimited)')
    parser.add_argument('--template', help='Path to HTML template')
    parser.add_argument('--attachment', help='Path to attachment (optional)')
    parser.add_argument('--leads', help='Path to leads file')
    parser.add_argument('--suppression', help='Path to suppression list file')
    parser.add_argument('--subject', help='Override subject')
    parser.add_argument('--resume', action='store_true', help='Resume previous campaign')
    parser.add_argument('--campaign-id', help='Campaign ID to resume')
    parser.add_argument('--no-progress-bar', action='store_true', help='Disable progress bar')
    return parser.parse_args()


def validate_email(email: str) -> bool:
    """
    Validate email address format.
    
    Args:
        email: Email address to validate
        
    Returns:
        True if valid, False otherwise
    """
    email_regex = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
    return email_regex.match(email) is not None


def process_leads(
    leads_path: str,
    suppression_path: Optional[str],
    logger
) -> tuple[List[str], set]:
    """
    Process leads file with validation and deduplication.
    
    Args:
        leads_path: Path to leads file
        suppression_path: Path to suppression list
        logger: Logger instance
        
    Returns:
        Tuple of (valid_leads, suppressed_set)
    """
    # Load raw leads
    raw_leads = read_lines(leads_path)
    logger.info(f"Loaded {len(raw_leads)} leads from {leads_path}")
    
    # Validate and deduplicate
    seen = set()
    leads = []
    invalid_count = 0
    
    for addr in raw_leads:
        if addr in seen:
            continue
        
        if validate_email(addr):
            leads.append(addr)
            seen.add(addr)
        else:
            logger.warning(f"Skipping invalid email address: {addr}")
            invalid_count += 1
    
    logger.info(f"Valid emails: {len(leads)}, Invalid: {invalid_count}, Duplicates removed: {len(raw_leads) - len(leads) - invalid_count}")
    
    # Load suppression list
    suppressed = set()
    if suppression_path and os.path.exists(suppression_path):
        suppressed.update(read_lines(suppression_path))
        logger.info(f"Loaded {len(suppressed)} suppressed addresses")
    
    return leads, suppressed


def main():
    args = parse_args()
    
    # Load configuration
    try:
        cfg = Config(args.config)
    except ConfigurationError as e:
        print(f"❌ Configuration error: {e}")
        return 1
    
    general = cfg.get_general_settings()
    smtp = cfg.get_smtp_settings()
    proxy = cfg.get_proxy_settings()
    
    # Initialize logger
    logger = init_logger(
        general['log_path'],
        structured=general.get('structured_logging', False)
    )
    
    logger.info("=" * 60)
    logger.info("🚀 Email Dispatcher - Production Mode")
    logger.info("=" * 60)
    
    # Apply proxy if configured
    apply_proxy(proxy)
    
    # Apply CLI overrides
    if args.dry_run:
        general['dry_run'] = True
    if args.concurrency is not None:
        general['concurrency'] = args.concurrency
    if args.rate_per_minute is not None:
        general['rate_per_minute'] = args.rate_per_minute
    if args.rate_per_hour is not None:
        general['rate_per_hour'] = args.rate_per_hour
    if args.subject:
        general['subject'] = args.subject
    
    # Paths
    leads_path = args.leads or general.get('leads_path', 'data/leads.txt')
    suppression_path = args.suppression or general.get('suppression_path', 'data/suppressions.txt')
    template_path = args.template or general.get('template_path', 'templates/message.html')
    attachment_path = args.attachment or general.get('attachment_path', '')
    
    # Clear log files at start
    clear_file(os.path.join(general['log_path'], 'success-emails.txt'))
    clear_file(os.path.join(general['log_path'], 'failed-emails.txt'))
    
    # Load placeholder values
    placeholder_dict = {}
    placeholder_file = 'data/placeholders.txt'
    if os.path.exists(placeholder_file):
        for line in read_lines(placeholder_file):
            if '=' in line:
                k, v = line.split('=', 1)
                placeholder_dict[k.strip()] = v.strip()
        logger.info(f"Loaded {len(placeholder_dict)} placeholder values")
    
    # Process leads
    try:
        leads, suppressed = process_leads(leads_path, suppression_path, logger)
    except Exception as e:
        logger.error(f"Failed to process leads: {e}")
        return 1
    
    # Filter suppressed addresses
    filtered_leads = [e for e in leads if e not in suppressed]
    skipped = len(leads) - len(filtered_leads)
    if skipped:
        logger.info(f"Filtered {skipped} suppressed recipients")
    
    if not filtered_leads:
        logger.warning("No leads to process after filtering!")
        return 0
    
    # Initialize state manager
    campaign_id = args.campaign_id or f"campaign_{int(time.time())}_{uuid.uuid4().hex[:8]}"
    state_manager = StateManager(
        db_path=general.get('state_db_path', 'logs/state.db'),
        campaign_id=campaign_id
    )
    
    # Check for resume
    if args.resume:
        if state_manager.can_resume():
            logger.info(f"📦 Resuming campaign: {campaign_id}")
            # Get pending/failed emails
            pending = state_manager.get_emails_by_state(EmailState.PENDING)
            failed = state_manager.get_emails_by_state(EmailState.FAILED)
            to_process = pending + failed
            logger.info(f"Resuming {len(to_process)} emails (pending: {len(pending)}, failed: {len(failed)})")
        else:
            logger.warning("No campaign to resume. Starting new campaign.")
            args.resume = False
    
    if not args.resume:
        # Start new campaign
        state_manager.start_campaign(
            total_emails=len(filtered_leads),
            config={
                'concurrency': general['concurrency'],
                'rate_per_minute': general['rate_per_minute'],
                'template_path': template_path,
            }
        )
        # Add all emails to state
        state_manager.add_emails(filtered_leads, EmailState.PENDING)
        to_process = filtered_leads
        logger.info(f"📧 Starting new campaign with {len(to_process)} emails")
    
    # Initialize components
    logger.info("🔧 Initializing components...")
    
    # Connection pool
    connection_pool = SMTPConnectionPool(
        smtp_settings=smtp,
        pool_size=general.get('connection_pool_size', 5),
        max_age=300.0,
        max_idle=60.0,
        max_uses=100
    )
    logger.info(f"✅ Connection pool initialized (size: {general.get('connection_pool_size', 5)})")
    
    # Rate limiter
    rate_limiter = RateLimiter(
        rate_per_minute=general.get('rate_per_minute', 0),
        rate_per_hour=general.get('rate_per_hour', 0),
        burst_allowance=1.5,
        adaptive=True
    )
    logger.info(f"✅ Rate limiter initialized (min: {general.get('rate_per_minute', 0)}, hour: {general.get('rate_per_hour', 0)})")
    
    # Retry queue
    retry_queue = RetryQueue(
        max_retries=general.get('max_retries_per_email', 3),
        base_delay=60.0,
        max_delay=3600.0,
        jitter=True,
        persistence_path=os.path.join(general['log_path'], 'retry_queue.json')
    )
    logger.info(f"✅ Retry queue initialized (max retries: {general.get('max_retries_per_email', 3)})")
    
    # Metrics collector
    metrics = MetricsCollector(total_emails=len(to_process))
    logger.info("✅ Metrics collector initialized")
    
    # Progress bar
    progress_bar = None
    if general.get('enable_progress_bar', True) and not args.no_progress_bar:
        progress_bar = ProgressBar(
            total=len(to_process),
            prefix="Sending",
            show_eta=True
        )
    
    logger.info(f"🚀 Starting dispatch to {len(to_process)} recipients...")
    logger.info(f"⚙️  Concurrency: {general['concurrency']}")
    if general.get('dry_run'):
        logger.warning("⚠️  DRY RUN MODE - No emails will be sent")
    
    # Task function
    def send_task(recipient: str) -> bool:
        """Send email with rate limiting and error handling."""
        correlation_id = str(uuid.uuid4())
        
        try:
            # Update state to in_progress
            state_manager.update_email_state(recipient, EmailState.IN_PROGRESS)
            
            # Acquire rate limit permission
            try:
                rate_limiter.acquire(block=True, timeout=300)
            except Exception as e:
                logger.warning(f"Rate limit timeout for {recipient}: {e}")
                state_manager.update_email_state(recipient, EmailState.PENDING)
                return False
            
            # Send email
            success = send_email_with_pool(
                recipient=recipient,
                connection_pool=connection_pool,
                general=general,
                logger=logger,
                template_path=template_path,
                attachment_path=attachment_path,
                placeholders=placeholder_dict,
                correlation_id=correlation_id
            )
            
            # Update state and metrics
            if success:
                state_manager.update_email_state(recipient, EmailState.SENT)
                metrics.record_success()
                rate_limiter.report_success()
            
            return success
            
        except SMTPTransientError as e:
            # Add to retry queue
            retry_queue.add(
                email_address=recipient,
                error=str(e),
                original_data={'placeholders': placeholder_dict},
                retry_count=0
            )
            state_manager.update_email_state(
                recipient,
                EmailState.RETRYING,
                error=str(e)
            )
            metrics.record_failure('transient')
            rate_limiter.report_error(is_rate_limit_error='rate limit' in str(e).lower())
            return False
            
        except SMTPPermanentError as e:
            # Don't retry permanent errors
            state_manager.update_email_state(
                recipient,
                EmailState.FAILED,
                error=str(e)
            )
            metrics.record_failure('permanent')
            return False
            
        except Exception as e:
            # Unexpected error - log and mark as failed
            logger.error(f"Unexpected error processing {recipient}: {e}", exc_info=True)
            state_manager.update_email_state(
                recipient,
                EmailState.FAILED,
                error=str(e)
            )
            metrics.record_failure('unexpected')
            return False
        
        finally:
            # Update progress bar
            if progress_bar:
                progress_bar.increment()
    
    # Execute with thread pool
    successes = 0
    failures = 0
    
    try:
        with ThreadPoolExecutor(max_workers=general['concurrency']) as pool:
            futures = [pool.submit(send_task, recipient) for recipient in to_process]
            
            # Create checkpoint every N emails
            checkpoint_interval = general.get('checkpoint_interval', 50)
            processed = 0
            
            for future in as_completed(futures):
                try:
                    result = future.result()
                    if result:
                        successes += 1
                    else:
                        failures += 1
                    
                    processed += 1
                    
                    # Create checkpoint
                    if processed % checkpoint_interval == 0:
                        state_manager.create_checkpoint(processed // checkpoint_interval)
                        logger.info(f"📍 Checkpoint: {processed}/{len(to_process)} processed")
                        
                except Exception as e:
                    logger.error(f"Task execution error: {e}")
                    failures += 1
        
        # Final checkpoint
        state_manager.create_checkpoint(9999)
        
    except KeyboardInterrupt:
        logger.warning("\n⚠️  Interrupted by user. Saving state...")
        state_manager.end_campaign('interrupted')
        connection_pool.close_all()
        return 130
    
    # Finish progress bar
    if progress_bar:
        progress_bar.finish()
    
    # End campaign
    state_manager.end_campaign('completed')
    
    # Close connection pool
    connection_pool.close_all()
    
    # Print final statistics
    logger.info("\n" + "=" * 60)
    logger.info("📊 Campaign Summary")
    logger.info("=" * 60)
    
    stats = state_manager.get_statistics()
    logger.info(f"Total Emails: {stats['total_emails']}")
    logger.info(f"Sent: {stats['completed_emails']}")
    logger.info(f"Failed: {stats['failed_emails']}")
    logger.info(f"Success Rate: {metrics.get_success_rate()*100:.1f}%")
    logger.info(f"Elapsed Time: {stats.get('elapsed_seconds', 0):.1f}s")
    logger.info(f"Throughput: {metrics.get_throughput()*60:.1f} emails/minute")
    
    # Retry queue stats
    retry_stats = retry_queue.get_stats()
    if retry_stats['queue_size'] > 0:
        logger.info(f"\n📥 Retry Queue: {retry_stats['queue_size']} items")
        logger.info(f"Dead Letter Queue: {retry_stats['dead_letter_size']} items")
    
    # Connection pool stats
    pool_stats = connection_pool.get_stats()
    logger.info(f"\n🔌 Connection Pool Stats:")
    logger.info(f"Total Connections Created: {pool_stats['total_created']}")
    logger.info(f"Connection Reuse Rate: {pool_stats.get('pool_hit_rate', 0)*100:.1f}%")
    
    # Print metrics summary
    logger.info("\n" + metrics.format_summary())
    
    logger.info("\n✅ Campaign complete!")
    logger.info(f"📝 Campaign ID: {campaign_id}")
    logger.info("=" * 60)
    
    return 0 if failures == 0 else 1


if __name__ == '__main__':
    exit(main())
