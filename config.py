import configparser
import os


class Config:
    def __init__(self, config_path='email_config.ini'):
        self.parser = configparser.ConfigParser()
        self.parser.read(config_path)
        self.mode = self.parser.get('general', 'mode', fallback='relay')

    def get_general_settings(self):
        general = {
            'mode': self.mode,
            'concurrency': int(os.getenv('CONCURRENCY', self.parser.getint('general', 'concurrency', fallback=10))),
            'retry_limit': int(os.getenv('RETRY_LIMIT', self.parser.getint('general', 'retry_limit', fallback=1))),
            'log_path': os.getenv('LOG_PATH', self.parser.get('general', 'log_path', fallback='logs/')),
            'dry_run': self._get_bool_env('DRY_RUN', self.parser.getboolean('general', 'dry_run', fallback=False)),
            'subject': os.getenv('SUBJECT', self.parser.get('general', 'subject', fallback='Important message')),
            'rate_per_minute': int(os.getenv('RATE_PER_MINUTE', self.parser.getint('general', 'rate_per_minute', fallback=0))),
            'template_path': os.getenv('TEMPLATE_PATH', self.parser.get('general', 'template_path', fallback='templates/message.html')),
            'attachment_path': os.getenv('ATTACHMENT_PATH', self.parser.get('general', 'attachment_path', fallback='templates/attachment.html')),
            'leads_path': os.getenv('LEADS_PATH', self.parser.get('general', 'leads_path', fallback='data/leads.txt')),
            'suppression_path': os.getenv('SUPPRESSION_PATH', self.parser.get('general', 'suppression_path', fallback='data/suppressions.txt')),
            'reply_to': os.getenv('REPLY_TO', self.parser.get('general', 'reply_to', fallback='')),
            'list_unsubscribe': os.getenv('LIST_UNSUBSCRIBE', self.parser.get('general', 'list_unsubscribe', fallback='')),
        }
        # Optional from address override
        from_email = os.getenv('FROM_EMAIL', self.parser.get('general', 'from_email', fallback=''))
        if from_email:
            general['from_email'] = from_email
        return general

    def get_smtp_settings(self):
        return {
            'host': os.getenv('SMTP_HOST', self.parser.get('smtp', 'host', fallback='')),
            'port': int(os.getenv('SMTP_PORT', self.parser.getint('smtp', 'port', fallback=587))),
            'username': os.getenv('SMTP_USERNAME', self.parser.get('smtp', 'username', fallback='')),
            'password': os.getenv('SMTP_PASSWORD', self.parser.get('smtp', 'password', fallback='')),
            'use_tls': self._get_bool_env('SMTP_USE_TLS', self.parser.getboolean('smtp', 'use_tls', fallback=True)),
            'use_auth': self._get_bool_env('SMTP_USE_AUTH', self.parser.getboolean('smtp', 'use_auth', fallback=True)),
        }

    def get_proxy_settings(self):
        if not self.parser.getboolean('proxy', 'enabled', fallback=False):
            return None
        return {
            'type': self.parser.get('proxy', 'type', fallback='socks5'),
            'host': self.parser.get('proxy', 'host'),
            'port': self.parser.getint('proxy', 'port'),
            'username': self.parser.get('proxy', 'username', fallback=''),
            'password': self.parser.get('proxy', 'password', fallback='')
        }

    @staticmethod
    def _get_bool_env(env_key: str, default: bool) -> bool:
        val = os.getenv(env_key)
        if val is None:
            return default
        return val.strip().lower() in {"1", "true", "yes", "on"}