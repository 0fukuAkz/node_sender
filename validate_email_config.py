from config import Config
import sys

def validate_config():
    try:
        cfg = Config()
        general = cfg.get_general_settings()
        smtp = cfg.get_smtp_settings()
        proxy = cfg.get_proxy_settings()

        print("✅ GENERAL SETTINGS")
        for k, v in general.items():
            print(f"{k}: {v}")

        print("\n✅ SMTP SETTINGS")
        for k, v in smtp.items():
            if k == "password" and v:
                print(f"{k}: {'*' * 8}")
            else:
                print(f"{k}: {v}")

        if proxy:
            print("\n✅ PROXY SETTINGS")
            for k, v in proxy.items():
                print(f"{k}: {v}")
        else:
            print("\nℹ️  Proxy disabled or not configured")

        print("\n🎯 Config validation complete.")

    except Exception as e:
        print(f"❌ Configuration error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    validate_config()