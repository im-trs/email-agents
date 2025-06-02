import os
import sys
import json
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import important_email2
import delete_emails
import send_mail2
import email_responder2


def test_group_emails_by_topics():
    emails = [
        {
            "subject": "Subject A",
            "from": "a@example.com",
            "analysis": {
                "topics": ["news", "updates"],
                "importance": "low",
                "needs_response": False
            }
        },
        {
            "subject": "Subject B",
            "from": "b@example.com",
            "analysis": {
                "topics": ["news"],
                "importance": "high",
                "needs_response": True
            }
        }
    ]
    grouped = important_email2.group_emails_by_topics(emails)
    assert "news" in grouped
    assert len(grouped["news"]) == 2
    assert any(e["subject"] == "Subject A" for e in grouped["news"])


def test_update_delete_tasks_creates_file(tmp_path):
    tasks_file = tmp_path / "to_delete.json"
    email = {"subject": "Subj", "from": "test@example.com", "received": "today"}
    analysis = important_email2.EmailImportance(
        importance="low",
        reason="none",
        needs_response=False,
        time_sensitive=False,
        topics=[]
    )
    important_email2.update_delete_tasks(email, analysis, tasks_file=tasks_file)
    assert tasks_file.exists()
    data = json.loads(tasks_file.read_text())
    assert data[0]["status"] == "to review"


def test_process_deletions_marks_deleted(monkeypatch, tmp_path):
    tasks_file = tmp_path / "to_delete.json"
    tasks = [{"subject": "Subj", "from": "t@example.com", "status": "to delete"}]
    tasks_file.write_text(json.dumps(tasks))

    class DummyIMAP:
        def __init__(self, server, port):
            pass
        def login(self, user, password):
            pass
        def select(self, mbox):
            return ('OK', [b''])
        def search(self, charset, query):
            return ('OK', [b'1'])
        def store(self, num, flag, val):
            pass
        def expunge(self):
            pass
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc, tb):
            pass

    def dummy_imap(server, port):
        return DummyIMAP(server, port)

    monkeypatch.setattr(delete_emails.imaplib, 'IMAP4_SSL', dummy_imap)
    monkeypatch.setenv('EMAIL_USER', 'user')
    monkeypatch.setenv('EMAIL_PASSWORD', 'pass')

    delete_emails.process_deletions(tasks_file=tasks_file)
    data = json.loads(tasks_file.read_text())
    assert data[0]["status"] == "deleted"


def test_modules_use_json_output_and_logging():
    # send_mail2 outputs
    assert send_mail2.CATEGORIZED_EMAILS_JSON.startswith("output/")
    assert send_mail2.CATEGORIZED_EMAILS_JSON.endswith(".json")
    assert send_mail2.OPPORTUNITY_REPORT.startswith("output/")
    assert send_mail2.OPPORTUNITY_REPORT.endswith(".json")
    assert hasattr(send_mail2, "LOG_FILE")

    # email_responder2 outputs
    assert email_responder2.NEEDS_RESPONSE_REPORT.startswith("output/")
    assert email_responder2.NEEDS_RESPONSE_REPORT.endswith(".json")
    assert email_responder2.RESPONSE_HISTORY_FILE.startswith("output/")
    assert email_responder2.RESPONSE_HISTORY_FILE.endswith(".json")
    assert hasattr(email_responder2, "LOG_FILE")

    # important_email2 outputs
    assert important_email2.NEEDS_RESPONSE_JSON.startswith("output/")
    assert important_email2.NEEDS_RESPONSE_JSON.endswith(".json")
    assert hasattr(important_email2, "LOG_FILE")
