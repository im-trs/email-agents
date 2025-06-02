import os
from dotenv import load_dotenv
import json
from datetime import datetime, timedelta
from openai import OpenAI
from pydantic import BaseModel
from typing import List, Optional, Literal
import re
import imaplib
import email
import smtplib
from email.message import EmailMessage

# Load environment variables
load_dotenv(override=True)

class EmailImportance(BaseModel):
    importance: Literal["high", "medium", "low"]
    reason: str
    needs_response: bool
    time_sensitive: bool
    topics: List[str]

# File paths
RECENT_EMAILS_FILE = "recent_emails.txt"
RESPONSE_HISTORY_FILE = "response_history.json"
NEEDS_RESPONSE_JSON = "needs_response_emails.json"
NEEDS_RESPONSE_REPORT = "needs_response_report.txt"

def load_response_history():
    """Load history of emails we've already responded to"""
    try:
        with open(RESPONSE_HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"responded_emails": []}

def save_response_history(history, new_response=None):
    """Save history of emails we've already responded to"""
    if new_response:
        history["responded_emails"].append({
            "subject": new_response["subject"],
            "from": new_response["from"],
            "responded_at": datetime.now().isoformat()
        })
    
    with open(RESPONSE_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)

def is_previously_responded(email, sent_emails):
    """Check if we've already responded to this email"""
    # Extract email address from the "From" field
    from_match = re.search(r'<(.+?)>', email.get('from', ''))
    sender_email = from_match.group(1).lower() if from_match else None
    
    if not sender_email:
        return False
    
    # Get the original subject without "Re:" or "Fwd:" prefixes
    subject = email.get('subject', '').lower()
    clean_subject = re.sub(r'^(?:re|fwd):\s*', '', subject, flags=re.IGNORECASE)
    
    for sent_email in sent_emails:
        # Check if we have sent an email to this sender 
        if sender_email in sent_email.get('recipients', []):
            # Check if the subject matches (either exact or with Re:/Fwd: prefixes)
            sent_subject = sent_email.get('subject', '').lower()
            clean_sent_subject = re.sub(r'^(?:re|fwd):\s*', '', sent_subject, flags=re.IGNORECASE)
            
            # If subject lines match (without prefixes), we've likely responded
            if clean_subject == clean_sent_subject or clean_subject in clean_sent_subject or clean_sent_subject in clean_subject:
                return True
    
    return False

def fetch_recent_inbox_emails(hours: int = 24):
    """Fetch emails from the inbox using IMAP."""
    username = os.getenv("EMAIL_USER")
    password = os.getenv("EMAIL_PASSWORD")
    server = os.getenv("IMAP_SERVER", "imap.gmail.com")
    port = int(os.getenv("IMAP_PORT", "993"))

    if not username or not password:
        raise ValueError("EMAIL_USER and EMAIL_PASSWORD must be set")

    cutoff = (datetime.utcnow() - timedelta(hours=hours)).strftime("%d-%b-%Y")

    emails = []
    with imaplib.IMAP4_SSL(server, port) as imap:
        imap.login(username, password)
        imap.select("INBOX")
        status, data = imap.search(None, f'(SINCE "{cutoff}")')
        if status != "OK":
            return []
        for num in data[0].split():
            status, msg_data = imap.fetch(num, "(RFC822)")
            if status != "OK":
                continue
            msg = email.message_from_bytes(msg_data[0][1])
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain" and not part.get("Content-Disposition"):
                        charset = part.get_content_charset() or "utf-8"
                        body = part.get_payload(decode=True).decode(charset, errors="replace")
                        break
            else:
                charset = msg.get_content_charset() or "utf-8"
                body = msg.get_payload(decode=True).decode(charset, errors="replace")

            emails.append({
                "subject": msg.get("Subject", ""),
                "from": msg.get("From", ""),
                "received": msg.get("Date", ""),
                "body": body.strip()
            })

    with open(RECENT_EMAILS_FILE, "w", encoding="utf-8") as f:
        for email_item in emails:
            f.write(f"Subject: {email_item['subject']}\n")
            f.write(f"From: {email_item['from']}\n")
            f.write(f"Received: {email_item['received']}\n")
            f.write(f"Body: {email_item['body']}\n")
            f.write("-" * 50 + "\n")

    return emails

# Backwards compatibility
def get_emails(hours: int = 24):
    return fetch_recent_inbox_emails(hours)

# Function that should be implemented by the user to get sent emails
def fetch_recent_sent_emails(days: int = 7):
    """Fetch sent emails using IMAP."""
    username = os.getenv("EMAIL_USER")
    password = os.getenv("EMAIL_PASSWORD")
    server = os.getenv("IMAP_SERVER", "imap.gmail.com")
    port = int(os.getenv("IMAP_PORT", "993"))
    sent_folder = os.getenv("IMAP_SENT_FOLDER", "[Gmail]/Sent Mail")

    if not username or not password:
        raise ValueError("EMAIL_USER and EMAIL_PASSWORD must be set")

    cutoff = (datetime.utcnow() - timedelta(days=days)).strftime("%d-%b-%Y")
    sent_emails = []
    with imaplib.IMAP4_SSL(server, port) as imap:
        imap.login(username, password)
        imap.select(sent_folder)
        status, data = imap.search(None, f'(SINCE "{cutoff}")')
        if status != "OK":
            return []
        for num in data[0].split():
            status, msg_data = imap.fetch(num, "(RFC822)")
            if status != "OK":
                continue
            msg = email.message_from_bytes(msg_data[0][1])
            recipients = []
            to_field = msg.get_all("To", [])
            cc_field = msg.get_all("Cc", [])
            for addr in email.utils.getaddresses(to_field + cc_field):
                recipients.append(addr[1])
            sent_emails.append({
                "subject": msg.get("Subject", ""),
                "recipients": recipients,
                "sent_time": msg.get("Date", "")
            })

    return sent_emails

# Backwards compatibility
def get_sent_emails(days: int = 7):
    return fetch_recent_sent_emails(days)

def read_emails():
    """Read emails from recent_emails.txt and return as a list of dictionaries"""
    try:
        with open(RECENT_EMAILS_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"No {RECENT_EMAILS_FILE} file found. Creating empty file.")
        with open(RECENT_EMAILS_FILE, "w", encoding="utf-8") as f:
            f.write("")
        return []
    
    emails = []
    current_email = {}
    current_body_lines = []
    
    for line in lines:
        line = line.rstrip()  # Remove trailing whitespace but keep leading whitespace
        
        if line.startswith("Subject: "):
            if current_email:  # Save previous email
                # Join body lines and clean up excessive whitespace
                current_email["body"] = "\n".join(
                    line for line in current_body_lines if line.strip()
                )
                emails.append(current_email)
                current_body_lines = []
            current_email = {"subject": line[9:], "from": "unknown"}  # Default 'from' to 'unknown'
        elif line.startswith("From: "):
            current_email["from"] = line[6:]
        elif line.startswith("Received: "):
            current_email["received"] = line[10:]
        elif line.startswith("Body: "):
            current_body_lines = [line[6:]]
        elif line.startswith("-" * 50):
            continue
        else:
            # Append non-marker lines to body
            if current_body_lines is not None:
                current_body_lines.append(line)
            
    # Don't forget to add the last email
    if current_email:
        current_email["body"] = "\n".join(
            line for line in current_body_lines if line.strip()
        )
        emails.append(current_email)
        
    return emails

def analyze_email_importance(client, email):
    """Analyze a single email's importance using OpenAI API"""
    # Clean up the body text while preserving meaningful whitespace
    body = email['body'].strip()
    
    prompt = f"""
    You are an email importance analyzer for a busy professional.
    Your task is to determine which emails CRITICALLY NEED a response and which can be ignored.
    
    BE EXTREMELY SELECTIVE - only flag emails as needing a response if they are:
    1. From real people (not automated systems)
    2. Personalized (not mass marketing)
    3. Require specific action or input from the recipient
    4. Have clear business value, substantial opportunity, or time-sensitive importance
    
    Automated notifications, newsletters, marketing emails should ALWAYS be marked as not needing response.

    Email to analyze:
    Subject: {email['subject']}
    From: {email['from']}
    Received: {email.get('received', 'unknown')}
    Body:
    {body[:4000]}  # Limiting to 4000 chars to stay within token limits
    
    Classify importance:
    - "high" importance: Personalized communications with clear value, time-sensitive matters that MUST be addressed
    - "medium" importance: Potentially useful but less critical communications
    - "low" importance: Mass marketing, newsletters, automated notifications, spam, etc.
    
    BE STRICT about "needs_response" - only mark TRUE if it absolutely requires personal attention and response.

    Respond with a JSON object that MUST include:
    {{
        "importance": "high" | "medium" | "low",
        "reason": <brief explanation for the importance rating>,
        "needs_response": <boolean - true ONLY if email absolutely requires a response>,
        "time_sensitive": <boolean - true if matter is time-sensitive>,
        "topics": [<list of 1-3 key topics in the email>]
    }}
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4.1",  # Use appropriate OpenAI model
            messages=[
                {
                    "role": "system", 
                    "content": "You are an executive assistant who helps busy professionals prioritize their emails. You are EXTREMELY selective about what emails truly need a response. Your goal is to minimize noise and only surface emails that absolutely must be dealt with."
                },
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        if content:
            analysis = json.loads(content)
            # Print for debugging
            print(f"\nAnalyzing: {email['subject']}")
            print(f"Analysis result: {json.dumps(analysis, indent=2)}")
            return EmailImportance(**analysis)
        else:
            print(f"Empty response for email: {email['subject']}")
            return None
            
    except Exception as e:
        print(f"Error analyzing email: {e}")
        print(f"Failed email subject: {email['subject']}")
        return None

def find_important_emails():
    """Main function to identify important emails"""
    # First fetch new emails from the last 24 hours
    print("Fetching emails from the last 24 hours...")
    get_emails(hours=24)
    
    # Get sent emails from the past week to check for responses
    print("Checking sent folder for previous responses...")
    sent_emails = get_sent_emails(days=7)
    
    # Initialize OpenAI client
    client = OpenAI()
    
    # Read emails
    emails = read_emails()
    
    # Prepare to store only emails that need a response
    needs_response_emails = []
    
    # Analyze each email
    for email in emails:
        # Check if we've already responded to this email by looking at sent items
        already_responded = is_previously_responded(email, sent_emails)
        
        analysis = analyze_email_importance(client, email)
        if analysis and analysis.needs_response:
            email_data = {
                "subject": email["subject"],
                "from": email["from"],
                "received": email.get("received", datetime.now().isoformat()),
                "body": email["body"][:1000] + ("..." if len(email["body"]) > 1000 else ""),  # Truncate for readability
                "analysis": analysis.model_dump(),
                "already_responded": already_responded
            }
            
            needs_response_emails.append(email_data)
    
    # Save results to JSON file
    output_data = {
        "last_updated": datetime.now().isoformat(),
        "needs_response_emails": needs_response_emails
    }
    
    with open(NEEDS_RESPONSE_JSON, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2)
    
    # Print summary
    print(f"\nProcessed {len(emails)} emails from the last 24 hours")
    print(f"Emails requiring response: {len(needs_response_emails)}")
    already_responded_count = sum(1 for email in needs_response_emails if email["already_responded"])
    print(f"Previously responded to: {already_responded_count}")
    print(f"New emails requiring response: {len(needs_response_emails) - already_responded_count}")
    print(f"\nDetailed results saved to: {NEEDS_RESPONSE_JSON}")
    
    # Generate a readable report
    with open(NEEDS_RESPONSE_REPORT, "w", encoding="utf-8") as f:
        f.write("==================================================\n")
        f.write("EMAILS REQUIRING RESPONSE\n")
        f.write(f"Generated on: {datetime.now().isoformat()}\n")
        f.write("==================================================\n\n")
        
        if needs_response_emails:
            # Sort by already_responded (not responded first), then time sensitivity, then importance
            sorted_emails = sorted(
                needs_response_emails, 
                key=lambda x: (
                    x["already_responded"],  # Not responded first
                    not x['analysis']['time_sensitive'],  # Time sensitive first
                    0 if x['analysis']['importance'] == 'high' else 
                    1 if x['analysis']['importance'] == 'medium' else 2  # Order by importance
                )
            )
            
            for email in sorted_emails:
                f.write(f"Subject: {email['subject']}\n")
                f.write(f"From: {email['from']}\n")
                f.write(f"Received: {email['received']}\n")
                f.write(f"Importance: {email['analysis']['importance'].upper()}\n")
                f.write(f"Time Sensitive: {'YES' if email['analysis']['time_sensitive'] else 'No'}\n")
                f.write(f"Topics: {', '.join(email['analysis']['topics'])}\n")
                f.write(f"Reason: {email['analysis']['reason']}\n")
                if email["already_responded"]:
                    f.write(f"STATUS: ✅ ALREADY RESPONDED\n")
                f.write(f"Preview: {email['body'][:300]}...\n\n")
                f.write("-" * 50 + "\n\n")
        else:
            f.write("No emails requiring immediate response were found.\n\n")
    
    # Print emails requiring response to console
    if needs_response_emails:
        print("\nEMAILS REQUIRING RESPONSE:\n" + "="*50)
        # Sort by already_responded (not responded first), then time sensitivity, then importance
        sorted_emails = sorted(
            needs_response_emails, 
            key=lambda x: (
                x["already_responded"],  # Not responded first
                not x['analysis']['time_sensitive'],  # Time sensitive first
                0 if x['analysis']['importance'] == 'high' else 
                1 if x['analysis']['importance'] == 'medium' else 2  # Order by importance
            )
        )
        
        for email in sorted_emails:
            print(f"\nSubject: {email['subject']}")
            print(f"From: {email['from']}")
            print(f"Importance: {email['analysis']['importance'].upper()}")
            print(f"Time Sensitive: {'YES' if email['analysis']['time_sensitive'] else 'No'}")
            print(f"Topics: {', '.join(email['analysis']['topics'])}")
            if email["already_responded"]:
                print(f"STATUS: ✅ ALREADY RESPONDED")
            print(f"Reason: {email['analysis']['reason']}")
            print("-" * 50)
    else:
        print("\nNo emails requiring immediate response were found.")
    
    print(f"\nFull report available in {NEEDS_RESPONSE_REPORT}")

if __name__ == "__main__":
    find_important_emails() 
