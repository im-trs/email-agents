import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import important_email2
import imaplib
import pytest

class FailSelectIMAP:
    def __init__(self, server, port):
        pass
    def login(self, user, password):
        pass
    def select(self, mbox):
        return ('NO', [b'Error'])
    def search(self, charset, query):
        raise imaplib.IMAP4.error("command SEARCH illegal in state AUTH")
    def fetch(self, num, data):
        return ('OK', [])
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb):
        pass

def fail_select_imap(server, port):
    return FailSelectIMAP(server, port)

def test_fetch_recent_sent_emails_handles_select_failure(monkeypatch):
    monkeypatch.setattr(important_email2.imaplib, 'IMAP4_SSL', fail_select_imap)
    monkeypatch.setenv('EMAIL_USER', 'user')
    monkeypatch.setenv('EMAIL_PASSWORD', 'pass')
    result = important_email2.fetch_recent_sent_emails(days=1)
    assert result == []
