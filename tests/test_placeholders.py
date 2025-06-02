import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import types
import important_email2
import send_mail2

class DummyIMAP:
    def __init__(self, server, port):
        pass
    def login(self, user, password):
        pass
    def select(self, mbox):
        pass
    def search(self, charset, query):
        return ('OK', [b'1'])
    def fetch(self, num, data):
        from email.message import EmailMessage
        msg = EmailMessage()
        msg['Subject'] = 'Hello'
        msg['From'] = 'sender@example.com'
        msg['Date'] = 'Thu, 1 Jan 1970 00:00:00 +0000'
        msg.set_content('body')
        return ('OK', [(b'1', msg.as_bytes())])
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb):
        pass

def dummy_imap(server, port):
    return DummyIMAP(server, port)

class DummySMTP:
    def __init__(self, server, port):
        pass
    def login(self, user, password):
        pass
    def send_message(self, msg):
        self.msg = msg
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb):
        pass

def dummy_smtp(server, port):
    return DummySMTP(server, port)


def test_placeholder_get_emails(monkeypatch):
    monkeypatch.setattr(important_email2.imaplib, 'IMAP4_SSL', dummy_imap)
    monkeypatch.setenv('EMAIL_USER', 'user')
    monkeypatch.setenv('EMAIL_PASSWORD', 'pass')
    emails = important_email2.get_emails(hours=1)
    assert emails and emails[0]['subject'] == 'Hello'


def test_placeholder_send_email(monkeypatch):
    monkeypatch.setattr(send_mail2.smtplib, 'SMTP_SSL', dummy_smtp)
    monkeypatch.setenv('EMAIL_USER', 'user')
    monkeypatch.setenv('EMAIL_PASSWORD', 'pass')
    result = send_mail2.send_email('Test', 'body', 'test@example.com')
    assert result is True
