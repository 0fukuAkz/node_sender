from src.email_dispatcher import Config
from src.email_dispatcher.template import load_template, apply_placeholders
from src.email_dispatcher.identity import generate_identity
from src.email_dispatcher.exceptions import ConfigurationError, PathSecurityError, SMTPConnectionError, SMTPAuthenticationError
import sys
import smtplib
import ssl
import os


def validate_config(test_smtp: bool = False, test_template: bool = True):
    """
    Comprehensive configuration validation with pre-flight checks.
    
    Args:
        test_smtp: Test actual SMTP connectivity
        test_template: Test template rendering
    """
    errors = []
    warnings = []
    
    try:
        print("🔍 Validating Configuration...")
        print("=" * 50)
        
        # Load configuration
        try:
            cfg = Config()
            general = cfg.get_general_settings()
            smtp = cfg.get_smtp_settings()
            proxy = cfg.get_proxy_settings()
        except Exception as e:
            print(f"❌ Failed to load configuration: {e}")
            sys.exit(1)
        
        # Display settings
        print("\n✅ GENERAL SETTINGS")
        for k, v in general.items():
            if k not in ['structured_logging', 'enable_progress_bar']:
                print(f"  {k}: {v}")
        
        print("\n✅ SMTP SETTINGS")
        for k, v in smtp.items():
            if k == "password" and v:
                print(f"  {k}: {'*' * 8}")
            else:
                print(f"  {k}: {v}")
        
        if proxy:
            print("\n✅ PROXY SETTINGS")
            for k, v in proxy.items():
                if k == "password" and v:
                    print(f"  {k}: {'*' * 8}")
                else:
                    print(f"  {k}: {v}")
        else:
            print("\nℹ️  Proxy disabled or not configured")
        
        # Validate file paths
        print("\n🔍 Validating File Paths...")
        
        # Check leads file
        leads_path = general.get('leads_path')
        if leads_path and os.path.exists(leads_path):
            print(f"  ✅ Leads file found: {leads_path}")
            # Check if readable
            try:
                with open(leads_path, 'r') as f:
                    line_count = sum(1 for _ in f)
                print(f"     Contains {line_count} lines")
            except Exception as e:
                errors.append(f"Cannot read leads file: {e}")
        else:
            warnings.append(f"Leads file not found: {leads_path}")
        
        # Check template file
        template_path = general.get('template_path')
        if template_path:
            try:
                template = load_template(template_path)
                print(f"  ✅ Template file loaded: {template_path}")
                print(f"     Size: {len(template)} characters")
                
                # Test template rendering if requested
                if test_template:
                    print("  🧪 Testing template rendering...")
                    test_identity = generate_identity()
                    test_placeholders = {
                        'recipient': 'test@example.com',
                        **test_identity
                    }
                    rendered = apply_placeholders(template, test_placeholders)
                    print("     ✅ Template renders successfully")
                    
            except PathSecurityError as e:
                errors.append(f"Template path security error: {e}")
            except Exception as e:
                errors.append(f"Cannot load template: {e}")
        
        # Check suppression file
        suppression_path = general.get('suppression_path')
        if suppression_path and os.path.exists(suppression_path):
            try:
                with open(suppression_path, 'r') as f:
                    suppression_count = sum(1 for _ in f)
                print(f"  ✅ Suppression file found: {suppression_path}")
                print(f"     Contains {suppression_count} addresses")
            except Exception as e:
                warnings.append(f"Cannot read suppression file: {e}")
        
        # Check log directory
        log_path = general.get('log_path', 'logs')
        if not os.path.exists(log_path):
            print(f"  ⚠️  Creating log directory: {log_path}")
            try:
                os.makedirs(log_path, exist_ok=True)
                print(f"     ✅ Log directory created")
            except Exception as e:
                errors.append(f"Cannot create log directory: {e}")
        else:
            print(f"  ✅ Log directory exists: {log_path}")
        
        # Validate settings ranges
        print("\n🔍 Validating Settings...")
        
        if general.get('concurrency', 0) < 1:
            errors.append("Concurrency must be at least 1")
        elif general.get('concurrency', 0) > 100:
            warnings.append("High concurrency (>100) may cause performance issues")
        else:
            print(f"  ✅ Concurrency: {general['concurrency']}")
        
        if general.get('retry_limit', 0) < 0:
            errors.append("Retry limit cannot be negative")
        else:
            print(f"  ✅ Retry limit: {general['retry_limit']}")
        
        # Test SMTP connection if requested
        if test_smtp:
            print("\n🔌 Testing SMTP Connection...")
            try:
                context = ssl.create_default_context()
                host = smtp['host']
                port = smtp['port']
                
                if not host:
                    errors.append("SMTP host not configured")
                else:
                    print(f"  Connecting to {host}:{port}...")
                    
                    if port == 465:
                        with smtplib.SMTP_SSL(host, port, context=context, timeout=10) as server:
                            if smtp.get('use_auth'):
                                server.login(smtp['username'], smtp['password'])
                            print("  ✅ SMTP connection successful (SSL)")
                    else:
                        with smtplib.SMTP(host, port, timeout=10) as server:
                            if smtp.get('use_tls'):
                                server.starttls(context=context)
                            if smtp.get('use_auth'):
                                server.login(smtp['username'], smtp['password'])
                            print("  ✅ SMTP connection successful (TLS)")
                            
            except smtplib.SMTPAuthenticationError as e:
                errors.append(f"SMTP authentication failed: {e}")
            except smtplib.SMTPException as e:
                errors.append(f"SMTP error: {e}")
            except Exception as e:
                errors.append(f"Connection error: {e}")
        
        # Print summary
        print("\n" + "=" * 50)
        print("📊 Validation Summary")
        print("=" * 50)
        
        if errors:
            print(f"\n❌ ERRORS ({len(errors)}):")
            for error in errors:
                print(f"  - {error}")
        
        if warnings:
            print(f"\n⚠️  WARNINGS ({len(warnings)}):")
            for warning in warnings:
                print(f"  - {warning}")
        
        if not errors and not warnings:
            print("\n✅ All validations passed!")
        elif not errors:
            print("\n✅ Validation passed with warnings")
        else:
            print("\n❌ Validation failed")
            sys.exit(1)
        
        print("\n🎯 Configuration validation complete.\n")

    except Exception as e:
        print(f"\n❌ Unexpected validation error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Validate email dispatcher configuration")
    parser.add_argument('--test-smtp', action='store_true', help='Test SMTP connectivity')
    parser.add_argument('--no-test-template', action='store_true', help='Skip template rendering test')
    args = parser.parse_args()
    
    validate_config(
        test_smtp=args.test_smtp,
        test_template=not args.no_test_template
    )