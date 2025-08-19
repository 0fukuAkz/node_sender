# 🚀 Email Dispatcher

A powerful, feature-rich bulk email dispatcher with interactive setup wizard and command-line interface.

## ✨ Features

- **Interactive Setup Wizard** - Guided configuration for beginners
- **Command Line Interface** - Full CLI with argument parsing
- **Smart Email Validation** - Automatic validation and deduplication
- **Template System** - HTML templates with placeholder substitution
- **Rate Limiting** - Configurable sending rate to avoid limits
- **Retry Logic** - Exponential backoff for transient failures
- **Proxy Support** - SOCKS4/5 and HTTP proxy support
- **Comprehensive Logging** - Rotating logs with success/failure tracking
- **Suppression Lists** - Block specific email addresses
- **Dry Run Mode** - Test without sending real emails

## 📋 Requirements

- Python 3.8+
- SMTP server access (Gmail, Outlook, custom, etc.)
- Email credentials (username/password or app password)

## 🚀 Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd node_sender
```

### 2. Install Dependencies

```bash
# Install required packages
pip install -r requirements.txt

# Or install manually
pip install Faker==24.8.0 PySocks==1.7.1
```

### 3. Verify Installation

```bash
# Check if dependencies are available
python3 -c "import faker, socks; print('✅ Dependencies installed successfully')"
```

## ⚙️ Configuration

### Quick Start (Interactive)

```bash
# Run the interactive setup wizard
python3 run_interactive.py

# Follow the prompts to configure:
# - SMTP settings (host, port, credentials)
# - General settings (concurrency, retry limits)
# - Proxy settings (optional)
```

### Manual Configuration

Create `email_config.ini`:

```ini
[general]
mode = relay
concurrency = 10
retry_limit = 2
log_path = logs
from_email = your@email.com
subject = Important message from {company}
rate_per_minute = 0
template_path = templates/message.html
attachment_path = templates/attachment.html
leads_path = data/leads.txt
suppression_path = data/suppressions.txt
reply_to = 
list_unsubscribe = 

[smtp]
host = smtp.gmail.com
port = 587
username = your@email.com
password = your_password
use_tls = true
use_auth = true

[proxy]
enabled = false
type = socks5
host = 127.0.0.1
port = 9050
username = 
password = 
```

### Environment Variables

Override any setting via environment variables:

```bash
# SMTP Settings
export SMTP_HOST=smtp.gmail.com
export SMTP_PORT=587
export SMTP_USERNAME=your@email.com
export SMTP_PASSWORD=your_password
export SMTP_USE_TLS=true
export SMTP_USE_AUTH=true

# General Settings
export CONCURRENCY=10
export RETRY_LIMIT=3
export DRY_RUN=true
export RATE_PER_MINUTE=60
export SUBJECT="Custom subject with {company}"
export FROM_EMAIL=your@email.com

# Paths
export TEMPLATE_PATH=templates/custom.html
export ATTACHMENT_PATH=templates/attachment.html
export LEADS_PATH=data/my_leads.txt
export SUPPRESSION_PATH=data/suppressions.txt
```

## 📧 Template System

### HTML Template

Create `templates/message.html`:

```html
<!DOCTYPE html>
<html>
<head>
    <title>Email from {company}</title>
</head>
<body>
    <h1>Hello {recipient}!</h1>
    <p>Welcome to {company}. We have a special offer: {offer} on {product}!</p>
    <p>Best regards,<br>{full_name}</p>
</body>
</html>
```

### Placeholders

Define variables in `data/placeholders.txt`:

```txt
company=Acme Corporation
product=Widget Pro
offer=50% off
```

### Dynamic Content

Automatically added placeholders:
- `{recipient}` - Email address
- `{full_name}` - Random sender name
- `{company}` - Random company name
- `{email}` - Random sender email
- `{uuid}` - Unique identifier

## 📊 Usage Guide

### Interactive Mode

#### 1. Setup Wizard

```bash
python3 run_interactive.py
# Choose option 1: Setup Wizard
```

**What it configures:**
- SMTP server details (host, port, credentials)
- General settings (concurrency, retry limits, rate limiting)
- Proxy configuration (optional)
- Template and file paths

#### 2. Configuration Editor

```bash
python3 run_interactive.py
# Choose option 2: Edit Configuration
```

**Edit options:**
- SMTP settings (host, port, username, password)
- General settings (subject, concurrency, retry limits)

#### 3. Configuration Validation

```bash
python3 run_interactive.py
# Choose option 3: Validate Current Config
```

**Checks:**
- SMTP connectivity
- File paths
- Configuration syntax

#### 4. Dry Run Testing

```bash
python3 run_interactive.py
# Choose option 4: Run Dry Run Test
```

**What it does:**
- Processes all recipients
- Generates emails (without sending)
- Logs what would be sent
- Validates templates and placeholders

#### 5. Live Dispatch

```bash
python3 run_interactive.py
# Choose option 5: Run Live Dispatch
```

**Safety features:**
- Requires explicit "yes" confirmation
- Shows warning about real emails
- Logs all operations

### Command Line Mode

#### Basic Commands

```bash
# Show help
python3 main.py --help

# Basic dry run
python3 main.py --dry-run

# Validate configuration
python3 validate_email_config.py
```

#### Advanced Options

```bash
# Custom concurrency and rate limiting
python3 main.py --dry-run --concurrency 5 --rate-per-minute 60

# Custom template and subject
python3 main.py --dry-run \
  --template templates/promotional.html \
  --subject "Special offer from {company}: {offer}"

# Custom leads and suppression files
python3 main.py --dry-run \
  --leads data/my_leads.txt \
  --suppression data/suppressions.txt

# Override multiple settings
python3 main.py --dry-run \
  --concurrency 3 \
  --rate-per-minute 30 \
  --subject "Hello from {company}"
```

#### Environment Variable Examples

```bash
# Override SMTP settings
SMTP_HOST=smtp.gmail.com SMTP_PORT=587 python3 main.py --dry-run

# Override general settings
CONCURRENCY=5 RATE_PER_MINUTE=60 python3 main.py --dry-run

# Override paths
TEMPLATE_PATH=templates/custom.html python3 main.py --dry-run
```

## 📁 File Structure

```
node_sender/
├── interactive.py          # Interactive setup wizard
├── run_interactive.py      # Interactive mode launcher
├── main.py                 # Main dispatcher (CLI mode)
├── config.py               # Configuration management
├── dispatcher.py           # Email sending logic
├── template.py             # Template processing
├── identity.py             # Random identity generation
├── logger.py               # Logging setup
├── proxy.py                # Proxy configuration
├── file_io.py              # File operations
├── validate_email_config.py # Configuration validator
├── email_config.ini        # Configuration file
├── requirements.txt         # Python dependencies
├── data/
│   ├── leads.txt           # Recipient email addresses
│   ├── placeholders.txt    # Template variables (key=value)
│   └── suppressions.txt    # Blocked email addresses
├── templates/
│   ├── message.html        # Main email template
│   └── attachment.html     # Optional attachment
└── logs/                   # Log files and tracking
```

## 🔧 Configuration Reference

### General Section

| Setting | Default | Description |
|---------|---------|-------------|
| `mode` | `relay` | Operation mode (legacy, kept for compatibility) |
| `concurrency` | `10` | Number of concurrent email threads |
| `retry_limit` | `2` | Maximum retry attempts for failed emails |
| `log_path` | `logs` | Directory for log files |
| `from_email` | `` | Sender email address |
| `subject` | `Important message from {company}` | Email subject line |
| `rate_per_minute` | `0` | Rate limiting (0 = unlimited) |
| `template_path` | `templates/message.html` | HTML template file |
| `attachment_path` | `templates/attachment.html` | Optional attachment file |
| `leads_path` | `data/leads.txt` | Recipient email list |
| `suppression_path` | `data/suppressions.txt` | Blocked email list |
| `reply_to` | `` | Reply-to email address |
| `list_unsubscribe` | `` | List unsubscribe header |

### SMTP Section

| Setting | Default | Description |
|---------|---------|-------------|
| `host` | `` | SMTP server hostname |
| `port` | `587` | SMTP server port |
| `username` | `` | SMTP username/email |
| `password` | `` | SMTP password/app password |
| `use_tls` | `true` | Enable TLS encryption |
| `use_auth` | `true` | Enable SMTP authentication |

### Proxy Section

| Setting | Default | Description |
|---------|---------|-------------|
| `enabled` | `false` | Enable proxy support |
| `type` | `socks5` | Proxy type (socks4/socks5/http) |
| `host` | `127.0.0.1` | Proxy server hostname |
| `port` | `9050` | Proxy server port |
| `username` | `` | Proxy username (if required) |
| `password` | `` | Proxy password (if required) |

## 📊 Monitoring and Logs

### Log Files

```bash
# Main application log
tail -f logs/email_sender.log

# Success tracking
cat logs/success-emails.txt

# Failure tracking
cat logs/failed-emails.txt

# Check counts
wc -l logs/success-emails.txt logs/failed-emails.txt
```

### Real-time Monitoring

```bash
# Watch logs in real-time
tail -f logs/email_sender.log | grep -E "(INFO|ERROR|WARNING)"

# Monitor specific operations
tail -f logs/email_sender.log | grep "DRY-RUN\|Sent to\|Failed to"
```

## 🚨 Safety Features

### Dry Run Mode

```bash
# Always test first
python3 main.py --dry-run

# Test with custom settings
python3 main.py --dry-run --concurrency 2 --rate-per-minute 30
```

### Email Validation

- Automatic validation of recipient addresses
- Deduplication of email lists
- Suppression list support
- Invalid email warnings

### Rate Limiting

```bash
# Prevent overwhelming SMTP providers
python3 main.py --rate-per-minute 60

# Conservative settings for new providers
python3 main.py --concurrency 2 --rate-per-minute 30
```

## 🐛 Troubleshooting

### Common Issues

#### 1. Import Errors

```bash
# Install dependencies
pip install Faker PySocks

# Check Python version
python3 --version  # Should be 3.8+
```

#### 2. SMTP Errors

**Authentication Failed:**
- Check username/password
- Use app password for Gmail/Outlook
- Verify 2FA settings

**Connection Refused:**
- Check host and port
- Verify firewall settings
- Try different ports (587, 465, 25)

**Rate Limited:**
- Reduce concurrency
- Enable rate limiting
- Check provider limits

#### 3. Template Errors

**Placeholder Issues:**
- Check `data/placeholders.txt` format
- Verify template syntax
- Use `{placeholder}` format

**File Not Found:**
- Check file paths in config
- Verify file permissions
- Use absolute paths if needed

### Debug Mode

```bash
# Enable verbose logging
export LOG_LEVEL=DEBUG
python3 main.py --dry-run

# Check configuration
python3 validate_email_config.py
```

### Getting Help

1. **Check Logs**: Review `logs/email_sender.log`
2. **Validate Config**: Run `python3 validate_email_config.py`
3. **Test Template**: Use dry-run mode
4. **Check Dependencies**: Verify all packages installed

## 📝 Examples

### Gmail Setup

```bash
# 1. Enable 2FA in Gmail
# 2. Generate app password
# 3. Use interactive setup
python3 run_interactive.py

# Or set environment variables
export SMTP_HOST=smtp.gmail.com
export SMTP_PORT=587
export SMTP_USERNAME=your@gmail.com
export SMTP_PASSWORD=your_app_password
export SMTP_USE_TLS=true
export SMTP_USE_AUTH=true

# 4. Test configuration
python3 main.py --dry-run
```

### Outlook Setup

```bash
# 1. Enable 2FA in Outlook
# 2. Generate app password
# 3. Use interactive setup
python3 run_interactive.py

# Or set environment variables
export SMTP_HOST=smtp-mail.outlook.com
export SMTP_PORT=587
export SMTP_USERNAME=your@outlook.com
export SMTP_PASSWORD=your_app_password
export SMTP_USE_TLS=true
export SMTP_USE_AUTH=true

# 4. Test configuration
python3 main.py --dry-run
```

### Custom SMTP Server

```bash
# 1. Get server details from your provider
# 2. Use interactive setup
python3 run_interactive.py

# Or set environment variables
export SMTP_HOST=mail.yourdomain.com
export SMTP_PORT=587
export SMTP_USERNAME=your@yourdomain.com
export SMTP_PASSWORD=your_password
export SMTP_USE_TLS=true
export SMTP_USE_AUTH=true

# 3. Test configuration
python3 main.py --dry-run
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 📞 Support

For issues and questions:
1. Check the troubleshooting section
2. Review the logs in `logs/email_sender.log`
3. Run `python3 validate_email_config.py` to verify configuration
4. Use dry-run mode to test without sending emails
5. Check the examples section for common setups

