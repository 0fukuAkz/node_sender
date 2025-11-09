#!/usr/bin/env python3
"""
Interactive Email Dispatcher Setup and Management
"""

import os
import sys
import getpass
from pathlib import Path
from src.email_dispatcher import Config
from main import main as run_dispatcher
from scripts.validate_email_config import validate_config


class InteractiveSetup:
    def __init__(self):
        self.config_file = 'email_config.ini'
        self.config = None
        
    def run(self):
        """Main interactive loop"""
        while True:
            self.show_main_menu()
            choice = input("\nEnter your choice (1-6): ").strip()
            
            if choice == '1':
                self.setup_wizard()
            elif choice == '2':
                self.edit_config()
            elif choice == '3':
                self.validate_current_config()
            elif choice == '4':
                self.run_dry_run()
            elif choice == '5':
                self.run_live()
            elif choice == '6':
                print("\n👋 Goodbye!")
                break
            else:
                print("\n❌ Invalid choice. Please try again.")
            
            input("\nPress Enter to continue...")
    
    def show_main_menu(self):
        """Display the main interactive menu"""
        os.system('clear' if os.name == 'posix' else 'cls')
        print("🚀 Interactive Email Dispatcher")
        print("=" * 40)
        print("1. 🔧 Setup Wizard (First Time)")
        print("2. ✏️  Edit Configuration")
        print("3. ✅ Validate Current Config")
        print("4. 🧪 Run Dry Run Test")
        print("5. 🚀 Run Live Dispatch")
        print("6. 🚪 Exit")
        print("=" * 40)
    
    def setup_wizard(self):
        """Interactive setup wizard for first-time configuration"""
        print("\n🔧 Email Dispatcher Setup Wizard")
        print("=" * 40)
        
        # Check if config exists
        if os.path.exists(self.config_file):
            overwrite = input(f"\nConfiguration file '{self.config_file}' already exists. Overwrite? (y/N): ").strip().lower()
            if overwrite != 'y':
                print("Setup cancelled.")
                return
        
        print("\n📧 SMTP Configuration")
        print("-" * 20)
        
        smtp_host = input("SMTP Host (e.g., smtp.gmail.com): ").strip()
        if not smtp_host:
            print("❌ SMTP host is required!")
            return
            
        smtp_port = input("SMTP Port (587 for STARTTLS, 465 for SSL): ").strip()
        try:
            smtp_port = int(smtp_port) if smtp_port else 587
        except ValueError:
            print("❌ Invalid port number!")
            return
            
        smtp_username = input("SMTP Username (email): ").strip()
        if not smtp_username:
            print("❌ Username is required!")
            return
            
        smtp_password = getpass.getpass("SMTP Password: ")
        if not smtp_password:
            print("❌ Password is required!")
            return
            
        use_tls = input("Use TLS? (Y/n): ").strip().lower()
        use_tls = use_tls != 'n'
        
        use_auth = input("Use Authentication? (Y/n): ").strip().lower()
        use_auth = use_auth != 'n'
        
        print("\n📋 General Settings")
        print("-" * 20)
        
        from_email = input(f"From Email (default: {smtp_username}): ").strip() or smtp_username
        subject = input("Default Subject (use {company} for placeholder): ").strip() or "Important message from {company}"
        concurrency = input("Concurrency (default: 10): ").strip()
        concurrency = int(concurrency) if concurrency.isdigit() else 10
        
        retry_limit = input("Retry Limit (default: 2): ").strip()
        retry_limit = int(retry_limit) if retry_limit.isdigit() else 2
        
        rate_per_minute = input("Rate Limit per Minute (0 = unlimited, default: 0): ").strip()
        rate_per_minute = int(rate_per_minute) if rate_per_minute.isdigit() else 0
        
        print("\n🔒 Proxy Settings (Optional)")
        print("-" * 20)
        
        use_proxy = input("Use Proxy? (y/N): ").strip().lower()
        proxy_config = {}
        
        if use_proxy == 'y':
            proxy_config['enabled'] = True
            proxy_config['type'] = input("Proxy Type (socks5/socks4/http, default: socks5): ").strip() or 'socks5'
            proxy_config['host'] = input("Proxy Host (default: 127.0.0.1): ").strip() or '127.0.0.1'
            proxy_port = input("Proxy Port (default: 9050): ").strip()
            proxy_config['port'] = int(proxy_port) if proxy_port.isdigit() else 9050
            proxy_config['username'] = input("Proxy Username (optional): ").strip()
            proxy_config['password'] = getpass.getpass("Proxy Password (optional): ")
        else:
            proxy_config['enabled'] = False
        
        # Create config file
        self.create_config_file(
            smtp_host, smtp_port, smtp_username, smtp_password, use_tls, use_auth,
            from_email, subject, concurrency, retry_limit, rate_per_minute,
            proxy_config
        )
        
        print(f"\n✅ Configuration saved to '{self.config_file}'")
        print("💡 Tip: You can now use environment variables to override settings:")
        print("   export SMTP_HOST=smtp.gmail.com")
        print("   export SMTP_PASSWORD=your_password")
    
    def create_config_file(self, smtp_host, smtp_port, smtp_username, smtp_password, 
                          use_tls, use_auth, from_email, subject, concurrency, 
                          retry_limit, rate_per_minute, proxy_config):
        """Create the configuration file with user inputs"""
        config_content = f"""[general]
mode = relay
concurrency = {concurrency}
retry_limit = {retry_limit}
log_path = logs
from_email = {from_email}
subject = {subject}
rate_per_minute = {rate_per_minute}
template_path = templates/message.html
attachment_path = templates/attachment.html
leads_path = data/leads.txt
suppression_path = data/suppressions.txt
reply_to = 
list_unsubscribe = 

[smtp]
host = {smtp_host}
port = {smtp_port}
username = {smtp_username}
password = {smtp_password}
use_tls = {str(use_tls).lower()}
use_auth = {str(use_auth).lower()}

[proxy]
enabled = {str(proxy_config['enabled']).lower()}
type = {proxy_config.get('type', 'socks5')}
host = {proxy_config.get('host', '127.0.0.1')}
port = {proxy_config.get('port', 9050)}
username = {proxy_config.get('username', '')}
password = {proxy_config.get('password', '')}
"""
        
        with open(self.config_file, 'w') as f:
            f.write(config_content)
    
    def edit_config(self):
        """Interactive configuration editor"""
        print("\n✏️  Configuration Editor")
        print("=" * 40)
        
        if not os.path.exists(self.config_file):
            print(f"❌ Configuration file '{self.config_file}' not found!")
            print("Please run the Setup Wizard first.")
            return
        
        try:
            self.config = Config(self.config_file)
            general = self.config.get_general_settings()
            smtp = self.config.get_smtp_settings()
            
            print("Current Settings:")
            print(f"SMTP Host: {smtp['host']}")
            print(f"SMTP Port: {smtp['port']}")
            print(f"Username: {smtp['username']}")
            print(f"From Email: {general.get('from_email', 'Not set')}")
            print(f"Subject: {general['subject']}")
            print(f"Concurrency: {general['concurrency']}")
            print(f"Retry Limit: {general['retry_limit']}")
            print(f"Rate per Minute: {general['rate_per_minute']}")
            
            print("\nWhat would you like to edit?")
            print("1. SMTP Settings")
            print("2. General Settings")
            print("3. Back to Main Menu")
            
            choice = input("\nEnter choice (1-3): ").strip()
            
            if choice == '1':
                self.edit_smtp_settings()
            elif choice == '2':
                self.edit_general_settings()
            elif choice == '3':
                return
            else:
                print("❌ Invalid choice!")
                
        except Exception as e:
            print(f"❌ Error reading configuration: {e}")
    
    def edit_smtp_settings(self):
        """Edit SMTP settings interactively"""
        print("\n📧 Edit SMTP Settings")
        print("-" * 20)
        
        # Read current config
        with open(self.config_file, 'r') as f:
            lines = f.readlines()
        
        # Find and update SMTP section
        for i, line in enumerate(lines):
            if line.startswith('host = '):
                new_host = input(f"SMTP Host (current: {line.split('=')[1].strip()}): ").strip()
                if new_host:
                    lines[i] = f"host = {new_host}\n"
            elif line.startswith('port = '):
                new_port = input(f"SMTP Port (current: {line.split('=')[1].strip()}): ").strip()
                if new_port and new_port.isdigit():
                    lines[i] = f"port = {new_port}\n"
            elif line.startswith('username = '):
                new_username = input(f"Username (current: {line.split('=')[1].strip()}): ").strip()
                if new_username:
                    lines[i] = f"username = {new_username}\n"
            elif line.startswith('password = '):
                change_pwd = input("Change password? (y/N): ").strip().lower()
                if change_pwd == 'y':
                    new_password = getpass.getpass("New SMTP Password: ")
                    if new_password:
                        lines[i] = f"password = {new_password}\n"
        
        # Write updated config
        with open(self.config_file, 'w') as f:
            f.writelines(lines)
        
        print("✅ SMTP settings updated!")
    
    def edit_general_settings(self):
        """Edit general settings interactively"""
        print("\n📋 Edit General Settings")
        print("-" * 20)
        
        # Read current config
        with open(self.config_file, 'r') as f:
            lines = f.readlines()
        
        # Find and update general section
        for i, line in enumerate(lines):
            if line.startswith('subject = '):
                new_subject = input(f"Subject (current: {line.split('=')[1].strip()}): ").strip()
                if new_subject:
                    lines[i] = f"subject = {new_subject}\n"
            elif line.startswith('concurrency = '):
                new_concurrency = input(f"Concurrency (current: {line.split('=')[1].strip()}): ").strip()
                if new_concurrency and new_concurrency.isdigit():
                    lines[i] = f"concurrency = {new_concurrency}\n"
            elif line.startswith('retry_limit = '):
                new_retry = input(f"Retry Limit (current: {line.split('=')[1].strip()}): ").strip()
                if new_retry and new_retry.isdigit():
                    lines[i] = f"retry_limit = {new_retry}\n"
            elif line.startswith('rate_per_minute = '):
                new_rate = input(f"Rate per Minute (current: {line.split('=')[1].strip()}): ").strip()
                if new_rate and new_rate.isdigit():
                    lines[i] = f"rate_per_minute = {new_rate}\n"
        
        # Write updated config
        with open(self.config_file, 'w') as f:
            f.writelines(lines)
        
        print("✅ General settings updated!")
    
    def validate_current_config(self):
        """Validate the current configuration"""
        print("\n✅ Validating Current Configuration")
        print("=" * 40)
        
        try:
            validate_config()
        except Exception as e:
            print(f"❌ Validation failed: {e}")
    
    def run_dry_run(self):
        """Run a dry run test"""
        print("\n🧪 Running Dry Run Test")
        print("=" * 40)
        
        try:
            # Set dry run environment variable
            os.environ['DRY_RUN'] = 'true'
            run_dispatcher()
        except Exception as e:
            print(f"❌ Dry run failed: {e}")
        finally:
            # Clean up environment
            if 'DRY_RUN' in os.environ:
                del os.environ['DRY_RUN']
    
    def run_live(self):
        """Run live dispatch"""
        print("\n🚀 Running Live Dispatch")
        print("=" * 40)
        print("⚠️  WARNING: This will send real emails!")
        
        confirm = input("Are you sure you want to continue? (yes/NO): ").strip().lower()
        if confirm == 'yes':
            try:
                run_dispatcher()
                print("✅ Live dispatch completed!")
            except Exception as e:
                print(f"❌ Live dispatch failed: {e}")
        else:
            print("Live dispatch cancelled.")


def main():
    """Main entry point"""
    try:
        setup = InteractiveSetup()
        setup.run()
    except KeyboardInterrupt:
        print("\n\n👋 Setup interrupted. Goodbye!")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

