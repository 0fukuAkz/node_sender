import argparse
import os
import re
import time
from config import Config
from proxy import apply_proxy
from logger import init_logger
from file_io import read_lines, clear_file
from dispatcher import send_email
from concurrent.futures import ThreadPoolExecutor, as_completed

def parse_args():
    parser = argparse.ArgumentParser(description="Bulk email dispatcher")
    parser.add_argument('--config', default='email_config.ini', help='Path to INI config')
    parser.add_argument('--dry-run', action='store_true', help='Enable dry run')
    parser.add_argument('--concurrency', type=int, help='Override concurrency')
    parser.add_argument('--rate-per-minute', type=int, help='Throttle rate per minute (0 = unlimited)')
    parser.add_argument('--template', help='Path to HTML template')
    parser.add_argument('--attachment', help='Path to attachment (optional)')
    parser.add_argument('--leads', help='Path to leads file')
    parser.add_argument('--suppression', help='Path to suppression list file')
    parser.add_argument('--subject', help='Override subject')
    return parser.parse_args()


def main():
    args = parse_args()
    cfg = Config(args.config)
    general = cfg.get_general_settings()
    smtp = cfg.get_smtp_settings()
    proxy = cfg.get_proxy_settings()
    logger = init_logger(general['log_path'])

    apply_proxy(proxy)

    # Paths with CLI override
    leads_path = args.leads or general.get('leads_path', 'data/leads.txt')
    suppression_path = args.suppression or general.get('suppression_path', 'data/suppressions.txt')
    template_path = args.template or general.get('template_path', 'templates/message.html')
    attachment_path = args.attachment or general.get('attachment_path', 'templates/attachment.html')

    # Apply CLI overrides to settings
    if args.dry_run:
        general['dry_run'] = True
    if args.concurrency is not None:
        general['concurrency'] = args.concurrency
    if args.rate_per_minute is not None:
        general['rate_per_minute'] = args.rate_per_minute
    if args.subject:
        general['subject'] = args.subject

    raw_leads = read_lines(leads_path)

    # Simple email validation and dedupe
    email_regex = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
    seen = set()
    leads = []
    for addr in raw_leads:
        if addr in seen:
            continue
        if email_regex.match(addr):
            leads.append(addr)
            seen.add(addr)
        else:
            logger.warning(f"Skipping invalid email address: {addr}")
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

    # Load suppression list
    suppressed = set()
    if suppression_path and os.path.exists(suppression_path):
        suppressed.update(read_lines(suppression_path))

    # Rate limiting configuration
    rate = int(general.get('rate_per_minute', 0))
    interval = 60.0 / rate if rate and rate > 0 else 0.0
    last_sent_time = [0.0]  # mutable cell shared by tasks

    def task(recipient):
        if interval > 0:
            # Coarse-grained throttle
            now = time.monotonic()
            elapsed = now - last_sent_time[0]
            sleep_for = max(0.0, interval - elapsed)
            if sleep_for > 0:
                time.sleep(sleep_for)
            last_sent_time[0] = time.monotonic()
        send_email(
            recipient=recipient,
            smtp=smtp,
            general=general,
            logger=logger,
            template_path=template_path,
            attachment_path=attachment_path,
            placeholders=placeholder_dict
        )

    # Filter suppressed addresses
    filtered = [e for e in leads if e not in suppressed]
    skipped = len(leads) - len(filtered)
    if skipped:
        logger.info(f"Skipping {skipped} suppressed recipients")

    logger.info(f"🚀 Starting dispatch to {len(filtered)} recipients...")
    successes = 0
    failures = 0
    with ThreadPoolExecutor(max_workers=general['concurrency']) as pool:
        futures = [pool.submit(task, r) for r in filtered]
        for _ in as_completed(futures):
            pass
    # Summarize from logs (basic): counts from success/failed files
    try:
        success_file = os.path.join(general['log_path'], 'success-emails.txt')
        failure_file = os.path.join(general['log_path'], 'failed-emails.txt')
        successes = len(read_lines(success_file)) if os.path.exists(success_file) else 0
        failures = len(read_lines(failure_file)) if os.path.exists(failure_file) else 0
    except Exception:
        pass
    logger.info(f"✅ Dispatch complete. Successes={successes}, Failures={failures}")

if __name__ == '__main__':
    main()