import os
import smtplib
import ssl
import time
import mimetypes
from email.message import EmailMessage
from email.utils import formataddr, formatdate, make_msgid

from identity import generate_identity
from template import load_template, apply_placeholders
from encryptor import encode_attachment
from file_io import log_line

def send_email(recipient, smtp, general, logger, template_path, attachment_path, placeholders):
    try:
        # Identity generation and placeholder merging
        identity = generate_identity()
        merged = {**placeholders, 'recipient': recipient, **identity}
        html = apply_placeholders(load_template(template_path), merged)

        # Email construction
        from_email = general.get('from_email', smtp['username'])
        from_name = identity['full_name']
        subject = apply_placeholders(general['subject'], merged)

        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = formataddr((from_name, from_email))
        msg['To'] = recipient
        if general.get('reply_to'):
            msg['Reply-To'] = general['reply_to']
        msg['Date'] = formatdate(localtime=True)
        msg['Message-ID'] = make_msgid()
        if general.get('list_unsubscribe'):
            msg['List-Unsubscribe'] = general['list_unsubscribe']
        msg.set_content("This message requires HTML support.")
        msg.add_alternative(html, subtype='html')

        # Attachment (optional) - attach raw bytes; let email library set headers
        if attachment_path:
            with open(attachment_path, 'rb') as f:
                data = f.read()
            ctype, _ = mimetypes.guess_type(attachment_path)
            if ctype is None:
                maintype, subtype = 'application', 'octet-stream'
            else:
                maintype, subtype = ctype.split('/', 1)
            msg.add_attachment(
                data,
                maintype=maintype,
                subtype=subtype,
                filename=os.path.basename(attachment_path),
            )

        # SMTP delivery
        if general.get('dry_run'):
            logger.info(f"[DRY-RUN] Would send to {recipient}: {subject}")
        else:
            context = ssl.create_default_context()
            attempts = max(1, int(general.get('retry_limit', 1)) + 1)
            last_exc = None
            for attempt in range(attempts):
                try:
                    if smtp['port'] == 465:
                        with smtplib.SMTP_SSL(smtp['host'], smtp['port'], context=context) as server:
                            if smtp['use_auth']:
                                server.login(smtp['username'], smtp['password'])
                            server.send_message(msg)
                    else:
                        with smtplib.SMTP(smtp['host'], smtp['port']) as server:
                            if smtp['use_tls']:
                                server.starttls(context=context)
                            if smtp['use_auth']:
                                server.login(smtp['username'], smtp['password'])
                            server.send_message(msg)
                    last_exc = None
                    break
                except (smtplib.SMTPServerDisconnected, smtplib.SMTPResponseException, smtplib.SMTPConnectError, smtplib.SMTPHeloError) as e:
                    last_exc = e
                    if attempt < attempts - 1:
                        backoff = 2 ** attempt
                        logger.warning(f"Transient SMTP error on attempt {attempt + 1}/{attempts}: {e}. Retrying in {backoff}s...")
                        time.sleep(backoff)
                except Exception as e:
                    last_exc = e
                    break
            if last_exc:
                raise last_exc

        # Logging
        log_line(os.path.join(general['log_path'], 'success-emails.txt'), recipient)
        logger.info(f"{'[DRY-RUN]' if general.get('dry_run') else '✅'} Sent to {recipient}")

    except Exception as e:
        log_line(os.path.join(general['log_path'], 'failed-emails.txt'), f"{recipient} - {str(e)}")
        logger.error(f"❌ Failed to send to {recipient}: {e}")