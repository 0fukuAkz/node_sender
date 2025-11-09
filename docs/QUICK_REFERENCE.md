# 🚀 Email Dispatcher - Quick Reference

## 🚀 Quick Start

```bash
# 1. Install and setup
./install.sh

# 2. Interactive configuration
python3 run_interactive.py

# 3. Test configuration
python3 main.py --dry-run

# 4. Send emails
python3 main.py
```

## 📋 Essential Commands

### Interactive Mode
```bash
python3 run_interactive.py          # Interactive setup wizard
```

### Command Line Mode
```bash
python3 main.py --help             # Show all options
python3 main.py --dry-run          # Test without sending
python3 validate_email_config.py   # Validate configuration
```

### Configuration
```bash
# Override settings via CLI
python3 main.py --dry-run --concurrency 5 --rate-per-minute 60

# Override via environment variables
SMTP_HOST=smtp.gmail.com python3 main.py --dry-run
```

## ⚙️ Common Configurations

### Gmail
```bash
export SMTP_HOST=smtp.gmail.com
export SMTP_PORT=587
export SMTP_USERNAME=your@gmail.com
export SMTP_PASSWORD=your_app_password
export SMTP_USE_TLS=true
export SMTP_USE_AUTH=true
```

### Outlook
```bash
export SMTP_HOST=smtp-mail.outlook.com
export SMTP_PORT=587
export SMTP_USERNAME=your@outlook.com
export SMTP_PASSWORD=your_app_password
export SMTP_USE_TLS=true
export SMTP_USE_AUTH=true
```

## 📊 Monitoring

```bash
# Watch logs in real-time
tail -f logs/email_sender.log

# Check success/failure counts
wc -l logs/success-emails.txt logs/failed-emails.txt

# Monitor specific operations
tail -f logs/email_sender.log | grep "DRY-RUN\|Sent to\|Failed to"
```

## 🔧 Troubleshooting

```bash
# Check dependencies
python3 -c "import faker, socks; print('OK')"

# Validate configuration
python3 validate_email_config.py

# Test with minimal settings
python3 main.py --dry-run --concurrency 1 --rate-per-minute 30
```

## 📁 Key Files

- `email_config.ini` - Main configuration
- `data/leads.txt` - Recipient emails
- `data/placeholders.txt` - Template variables
- `templates/message.html` - Email template
- `logs/email_sender.log` - Application logs

## 🚨 Safety First

- **Always test first**: `python3 main.py --dry-run`
- **Start small**: Use low concurrency (2-5) initially
- **Rate limit**: Set `--rate-per-minute 60` for new providers
- **Monitor logs**: Watch for errors and warnings

