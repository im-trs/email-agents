import os
import json
import imaplib
from datetime import datetime
from dotenv import load_dotenv

OUTPUT_DIR = "output"
TO_DELETE_FILE = os.path.join(OUTPUT_DIR, "to_delete.json")
LOG_FILE = os.path.join(OUTPUT_DIR, "delete_emails.log")

load_dotenv(override=True)


def load_delete_tasks(tasks_file=TO_DELETE_FILE):
    try:
        with open(tasks_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_delete_tasks(tasks, tasks_file=TO_DELETE_FILE):
    os.makedirs(os.path.dirname(tasks_file), exist_ok=True)
    with open(tasks_file, "w", encoding="utf-8") as f:
        json.dump(tasks, f, indent=2)


def log(message):
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now().isoformat()} - {message}\n")
    print(message)


def delete_email(task):
    username = os.getenv("EMAIL_USER")
    password = os.getenv("EMAIL_PASSWORD")
    server = os.getenv("IMAP_SERVER", "imap.gmail.com")
    port = int(os.getenv("IMAP_PORT", "993"))

    if not username or not password:
        raise ValueError("EMAIL_USER and EMAIL_PASSWORD must be set")

    with imaplib.IMAP4_SSL(server, port) as imap:
        imap.login(username, password)
        imap.select("INBOX")
        status, data = imap.search(None, f'(HEADER Subject "{task["subject"]}")')
        if status != "OK":
            return False
        for num in data[0].split():
            imap.store(num, "+FLAGS", "\\Deleted")
        imap.expunge()
    return True


def process_deletions(tasks_file=TO_DELETE_FILE):
    tasks = load_delete_tasks(tasks_file)
    updated = False
    for task in tasks:
        if task.get("status") != "to delete":
            continue
        log(f"Deleting: {task['subject']}")
        if delete_email(task):
            task["status"] = "deleted"
            task["deleted_at"] = datetime.now().isoformat()
            updated = True
            log(f"Deleted: {task['subject']}")
        else:
            log(f"Failed to delete: {task['subject']}")
    if updated:
        save_delete_tasks(tasks, tasks_file)


if __name__ == "__main__":
    process_deletions()
