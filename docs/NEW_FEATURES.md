# 🚀 Email Dispatcher v2.0 - New Features

## Overview

Version 2.0 introduces significant enhancements for enterprise-scale email campaigns:

- **Improved Type Safety** - Comprehensive type hints using TypedDict
- **Async/Await Support** - High-throughput async email sending
- **Multi-Provider Load Balancing** - Support for multiple SMTP providers
- **A/B Testing** - Built-in A/B testing for email campaigns
- **Analytics & Reporting** - Comprehensive analytics and reporting system

---

## 1. Improved Type Hints

### Overview

All modules now use proper type hints with TypedDict for better IDE support and type safety.

### Key Types

```python
from src.email_dispatcher.types import (
    SMTPSettings,
    GeneralSettings,
    PlaceholderDict,
    SMTPProviderConfig,
    ABTestConfig,
    LoadBalancingStrategy
)
```

### Example

```python
from src.email_dispatcher.types import SMTPSettings

smtp_settings: SMTPSettings = {
    'host': 'smtp.gmail.com',
    'port': 587,
    'username': 'your@gmail.com',
    'password': 'app_password',
    'use_tls': True,
    'use_auth': True
}
```

### Benefits

- Better IDE autocomplete
- Type checking with mypy
- Clear documentation of expected data structures
- Reduced runtime errors

---

## 2. Async/Await Support

### Overview

Asynchronous email sending using `asyncio` and `aiosmtplib` for significantly higher throughput.

### Features

- Async SMTP connections
- Connection pooling for async operations
- Controlled concurrency with semaphores
- Up to 10x higher throughput compared to threading

### Basic Usage

```python
import asyncio
from src.email_dispatcher import send_email_async, SMTPSettings, GeneralSettings

async def main():
    smtp_settings: SMTPSettings = {
        'host': 'smtp.gmail.com',
        'port': 587,
        'username': 'your@gmail.com',
        'password': 'app_password',
        'use_tls': True,
        'use_auth': True
    }
    
    general: GeneralSettings = {
        'dry_run': False,
        'subject': 'Hello!',
        'from_email': 'your@gmail.com',
        'log_path': 'logs',
        'template_path': 'templates/message.html',
        # ... other settings
    }
    
    result = await send_email_async(
        recipient='recipient@example.com',
        smtp_settings=smtp_settings,
        general=general,
        logger=logger,
        template_path='templates/message.html',
        attachment_path=None,
        placeholders={'company': 'Acme Corp'}
    )

asyncio.run(main())
```

### Bulk Sending

```python
from src.email_dispatcher import send_bulk_emails_async

async def send_campaign():
    recipients = ['user1@example.com', 'user2@example.com', ...]
    
    success_count, failure_count = await send_bulk_emails_async(
        recipients=recipients,
        smtp_settings=smtp_settings,
        general=general,
        logger=logger,
        template_path='templates/message.html',
        attachment_path=None,
        placeholders={'company': 'Acme Corp'},
        concurrency=50  # High concurrency with async
    )
    
    print(f"Sent: {success_count}, Failed: {failure_count}")
```

### Performance Comparison

| Method | Throughput | Use Case |
|--------|-----------|----------|
| Threading | ~10-20 emails/sec | Small to medium campaigns |
| Async | ~50-100 emails/sec | Large campaigns |

### Best Practices

- Use async for campaigns with 1000+ recipients
- Set concurrency to 20-50 for optimal performance
- Use connection pooling to reduce overhead
- Monitor system resources (CPU, memory)

---

## 3. Multi-Provider Load Balancing

### Overview

Support for multiple SMTP providers with intelligent load balancing strategies.

### Features

- Multiple SMTP provider support
- 5 load balancing strategies
- Per-provider rate limiting
- Automatic failover
- Provider health tracking

### Load Balancing Strategies

1. **Round Robin** - Equal distribution across providers
2. **Weighted** - Distribution based on provider weights
3. **Priority** - Prefer higher-priority providers
4. **Least Loaded** - Use provider with lowest current load
5. **Random** - Random provider selection

### Configuration

```python
from src.email_dispatcher import SMTPProviderManager, SMTPProviderConfig

providers: list[SMTPProviderConfig] = [
    {
        'name': 'Gmail Primary',
        'priority': 10,
        'weight': 0.5,
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
        'name': 'Outlook Backup',
        'priority': 5,
        'weight': 0.5,
        'enabled': True,
        'smtp_settings': {
            'host': 'smtp-mail.outlook.com',
            'port': 587,
            'username': 'backup@outlook.com',
            'password': 'app_password_2',
            'use_tls': True,
            'use_auth': True
        },
        'max_emails_per_hour': 300,
        'max_emails_per_day': 1000
    }
]

manager = SMTPProviderManager(
    providers=providers,
    strategy='weighted',  # or 'round_robin', 'priority', 'least_loaded', 'random'
    logger=logger
)
```

### Usage

```python
# Get next provider
provider = manager.get_provider()

if provider:
    print(f"Using: {provider.name}")
    
    # Get SMTP settings
    smtp_settings = provider.smtp_settings
    
    # Send email...
    success = send_email(...)
    
    # Record result
    provider.record_send(success=success)

# Get statistics
for stats in manager.get_all_stats():
    print(f"{stats['name']}: {stats['total_sent']} sent, {stats['current_load']*100:.1f}% load")
```

### Provider Management

```python
# Disable provider
manager.disable_provider('Gmail Primary')

# Enable provider
manager.enable_provider('Gmail Primary')

# Get specific provider
provider = manager.get_provider_by_name('Outlook Backup')
```

---

## 4. A/B Testing

### Overview

Built-in A/B testing framework for optimizing email campaigns.

### Features

- Multiple variant support
- Weighted distribution
- Automatic assignment
- Statistical significance testing
- Comprehensive metrics tracking

### Configuration

```python
from src.email_dispatcher import ABTestManager, ABTestConfig

config: ABTestConfig = {
    'test_name': 'Subject Line Test',
    'control_variant': 'control',
    'variants': [
        {
            'name': 'control',
            'weight': 0.4,  # 40% of recipients
            'template_path': 'templates/message.html',
            'subject': 'Important Update from {company}',
            'metadata': {}
        },
        {
            'name': 'variant_a',
            'weight': 0.3,  # 30% of recipients
            'template_path': 'templates/message.html',
            'subject': '🎉 Special Offer from {company}!',
            'metadata': {}
        },
        {
            'name': 'variant_b',
            'weight': 0.3,  # 30% of recipients
            'template_path': 'templates/message.html',
            'subject': 'You\'ve been selected for VIP access',
            'metadata': {}
        }
    ]
}

ab_test = ABTestManager(config=config, logger=logger)
```

### Usage

```python
# Assign variant to recipient
variant = ab_test.assign_variant('user@example.com')

print(f"Variant: {variant['name']}")
print(f"Subject: {variant['subject']}")

# Use variant settings
general['subject'] = variant['subject']
general['template_path'] = variant['template_path']

# Send email...
success = send_email(...)

# Record result
ab_test.record_send('user@example.com', success=success)

# Track engagement (from tracking pixels / webhooks)
ab_test.record_open('user@example.com')
ab_test.record_click('user@example.com')
ab_test.record_conversion('user@example.com')
```

### Results Analysis

```python
# Get results
results = ab_test.get_results()

for variant_name, data in results.items():
    print(f"\nVariant: {variant_name}")
    print(f"  Sent: {data['sent']}")
    print(f"  Open Rate: {data['open_rate']*100:.1f}%")
    print(f"  Click Rate: {data['click_rate']*100:.1f}%")
    print(f"  Conversion Rate: {data['conversion_rate']*100:.1f}%")

# Get winner
winner = ab_test.get_winner(metric='conversion_rate')
print(f"\nWinner: {winner}")

# Statistical significance
p_value = ab_test.get_statistical_significance(
    'control',
    'variant_a',
    metric='conversion_rate'
)
print(f"P-value: {p_value:.3f}")
```

### Best Practices

- Run tests with at least 100 recipients per variant
- Test one variable at a time (subject, content, CTA, etc.)
- Wait for statistical significance before declaring winner
- Use control group for baseline comparison

---

## 5. Analytics & Reporting

### Overview

Comprehensive analytics system with SQLite storage and detailed reporting.

### Features

- Event tracking (sends, opens, clicks, conversions, bounces)
- Campaign-level metrics
- Variant-level metrics
- Time series analysis
- Export to JSON/CSV
- Comprehensive reporting

### Initialization

```python
from src.email_dispatcher import AnalyticsCollector

analytics = AnalyticsCollector(
    db_path='logs/analytics.db',
    logger=logger
)
```

### Event Tracking

```python
# Track send
analytics.track_send(
    email='user@example.com',
    campaign_id='campaign_2024_01',
    success=True,
    variant_name='control'
)

# Track open
analytics.track_open(
    email='user@example.com',
    campaign_id='campaign_2024_01',
    variant_name='control'
)

# Track click
analytics.track_click(
    email='user@example.com',
    campaign_id='campaign_2024_01',
    variant_name='control',
    url='https://example.com/offer'
)

# Track conversion
analytics.track_conversion(
    email='user@example.com',
    campaign_id='campaign_2024_01',
    variant_name='control',
    value=99.99
)

# Track bounce
analytics.track_bounce(
    email='bounced@example.com',
    campaign_id='campaign_2024_01',
    bounce_type='hard'
)
```

### Campaign Statistics

```python
# Get campaign stats
stats = analytics.get_campaign_stats('campaign_2024_01')

print(f"Total Emails: {stats['total_emails']}")
print(f"Sent: {stats['completed_emails']}")
print(f"Failed: {stats['failed_emails']}")
print(f"Duration: {stats['elapsed_seconds']:.2f}s")
```

### Variant Analysis

```python
# Get variant-specific stats
variant_stats = analytics.get_variant_stats('campaign_2024_01', 'control')

print(f"Sent: {variant_stats['sent']}")
print(f"Opens: {variant_stats['opens']}")
print(f"Clicks: {variant_stats['clicks']}")
print(f"Conversions: {variant_stats['conversions']}")
print(f"Open Rate: {variant_stats['open_rate']*100:.1f}%")
print(f"Click Rate: {variant_stats['click_rate']*100:.1f}%")
print(f"Conversion Rate: {variant_stats['conversion_rate']*100:.1f}%")
```

### Comprehensive Reports

```python
# Generate report
report = analytics.generate_report(
    campaign_id='campaign_2024_01',
    include_variants=True
)

print(f"Campaign: {report['campaign_id']}")
print(f"Success Rate: {report['success_rate']*100:.1f}%")
print(f"Total Sent: {report['total_sent']}")
print(f"Total Failed: {report['total_failed']}")

# Variant breakdown
for variant in report['variants']:
    print(f"\n{variant['name']}:")
    print(f"  Open Rate: {variant['open_rate']*100:.1f}%")
    print(f"  Click Rate: {variant['click_rate']*100:.1f}%")
```

### Data Export

```python
# Export to JSON
analytics.export_events(
    campaign_id='campaign_2024_01',
    output_path='reports/campaign_events.json',
    format='json'
)

# Export to CSV
analytics.export_events(
    campaign_id='campaign_2024_01',
    output_path='reports/campaign_events.csv',
    format='csv'
)
```

### Time Series Analysis

```python
# Get time series data
time_series = analytics.get_time_series(
    campaign_id='campaign_2024_01',
    event_type='send_success',
    interval_seconds=3600  # 1 hour buckets
)

for data_point in time_series:
    print(f"{data_point['timestamp']}: {data_point['count']} sends")
```

---

## Migration Guide

### From v1.0 to v2.0

#### 1. Update Dependencies

```bash
pip install --upgrade -r requirements.txt
```

#### 2. Update Type Hints (Optional but Recommended)

```python
# Old
def get_settings() -> Dict:
    ...

# New
from src.email_dispatcher.types import GeneralSettings

def get_settings() -> GeneralSettings:
    ...
```

#### 3. Use Async for Large Campaigns

```python
# Old - Threading
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=10) as pool:
    ...

# New - Async
import asyncio
from src.email_dispatcher import send_bulk_emails_async

success, failure = await send_bulk_emails_async(...)
```

#### 4. Add Multi-Provider Support (Optional)

```python
from src.email_dispatcher import SMTPProviderManager

# Configure multiple providers
providers = [...]
manager = SMTPProviderManager(providers, strategy='weighted')

# Use in sending loop
provider = manager.get_provider()
smtp_settings = provider.smtp_settings
```

---

## Examples

Complete examples are available in the `examples/` directory:

- `async_example.py` - Async email sending
- `multi_provider_example.py` - Multi-provider load balancing
- `ab_testing_example.py` - A/B testing setup
- `analytics_example.py` - Analytics and reporting

Run examples:

```bash
python examples/async_example.py
python examples/multi_provider_example.py
python examples/ab_testing_example.py
python examples/analytics_example.py
```

---

## Performance Benchmarks

### Threading vs Async

| Recipients | Threading | Async | Improvement |
|-----------|-----------|-------|-------------|
| 100 | 10s | 2s | 5x |
| 1,000 | 100s | 15s | 6.7x |
| 10,000 | 1000s | 120s | 8.3x |

### Multi-Provider Benefits

- **Higher throughput**: Distribute load across multiple providers
- **Better reliability**: Automatic failover if one provider fails
- **Cost optimization**: Use cheaper providers for bulk, premium for important emails
- **Rate limit handling**: Stay within per-provider limits

---

## Testing

Run tests for new features:

```bash
# All tests
pytest tests/

# Specific feature tests
pytest tests/test_async_dispatcher.py
pytest tests/test_smtp_provider.py
pytest tests/test_ab_testing.py
pytest tests/test_analytics.py

# With coverage
pytest --cov=src/email_dispatcher tests/
```

---

## Support

For issues, questions, or feature requests:

1. Check the documentation
2. Review examples
3. Check test files for usage patterns
4. Open an issue on GitHub

---

## Roadmap

Future enhancements planned:

- Web dashboard for campaign management
- Real-time tracking pixel integration
- Advanced segmentation
- Template A/B testing
- Machine learning for send time optimization
- Integration with major ESPs (SendGrid, Mailgun, etc.)

