"""Sending of email messages, a replacement for Flask-Mail."""
import smtplib
from email.message import EmailMessage
from threading import Thread

from app.state import state


def send_async_email(config, msg):
    _send_message(config, msg)


def _send_message(config, msg):
    server = smtplib.SMTP(config['MAIL_SERVER'], config['MAIL_PORT'])
    try:
        if config['MAIL_USE_TLS']:
            server.starttls()
        if config['MAIL_USERNAME'] or config['MAIL_PASSWORD']:
            server.login(config['MAIL_USERNAME'], config['MAIL_PASSWORD'])
        server.send_message(msg)
    finally:
        server.quit()


def send_email(subject, sender, recipients, text_body, html_body,
               attachments=None, sync=False):
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = ', '.join(recipients)
    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype='html')
    if attachments:
        for attachment in attachments:
            filename, content_type, data = attachment
            maintype, _, subtype = content_type.partition('/')
            if isinstance(data, str):
                data = data.encode('utf-8')
            msg.add_attachment(data, maintype=maintype, subtype=subtype,
                               filename=filename)
    config = dict(state.config)
    if sync:
        _send_message(config, msg)
    else:
        Thread(target=send_async_email, args=(config, msg)).start()
