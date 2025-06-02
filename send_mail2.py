import os
from dotenv import load_dotenv
import json
from datetime import datetime, timedelta
from openai import OpenAI
from pydantic import BaseModel
from typing import Optional, Literal
import imaplib
import email
import smtplib
from email.message import EmailMessage

# Load environment variables
load_dotenv(override=True)

class EmailAnalysis(BaseModel):
    category: Literal["sponsorship", "business_inquiry", "other"]
    confidence: float
    reason: str
    company_name: Optional[str] = None
    topic: Optional[str] = None

# File paths
OUTPUT_DIR = "output"
EMAILS_FILE = os.path.join(OUTPUT_DIR, "emails.json")
CATEGORIZED_EMAILS_JSON = os.path.join(OUTPUT_DIR, "categorized_emails.json")
OPPORTUNITY_REPORT = os.path.join(OUTPUT_DIR, "opportunity_report.json")
LOG_FILE = os.path.join(OUTPUT_DIR, "send_mail2.log")


def log(message):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now().isoformat()} - {message}\n")
    print(message)

# Function that actually sends an email via SMTP
def send_email_via_smtp(subject: str, body: str, recipient_email: str) -> bool:
    username = os.getenv("EMAIL_USER")
    password = os.getenv("EMAIL_PASSWORD")
    server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    port = int(os.getenv("SMTP_PORT", "465"))

    if not username or not password:
        raise ValueError("EMAIL_USER and EMAIL_PASSWORD must be set")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = username
    msg["To"] = recipient_email
    msg.set_content(body)

    with smtplib.SMTP_SSL(server, port) as smtp:
        smtp.login(username, password)
        smtp.send_message(msg)

    return True

# Backwards compatibility
def send_email(subject: str, body: str, recipient_email: str) -> bool:
    return send_email_via_smtp(subject, body, recipient_email)

# Function that should be implemented by the user
def fetch_recent_inbox_emails(hours: int = 72):
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

    with open(EMAILS_FILE, "w", encoding="utf-8") as f:
        json.dump(emails, f, indent=2)
    log("Saved fetched emails")

    return emails

# Backwards compatibility
def get_emails(hours: int = 72):
    return fetch_recent_inbox_emails(hours)

def read_emails():
    """Read emails from emails.json and return as a list of dictionaries"""
    try:
        with open(EMAILS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        log(f"No {EMAILS_FILE} file found. Creating empty file.")
        with open(EMAILS_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)
        return []

def analyze_email(client, email):
    """Analyze a single email using OpenAI API with Structured Outputs"""
    # Clean up the body text while preserving meaningful whitespace
    body = email['body'].strip()
    
    prompt = f"""
    You are an email categorizer for a professional. Your task is to categorize incoming emails
    and identify important information.

    Email to analyze:
    Subject: {email['subject']}
    From: {email['from']}
    Body:
    {body[:4000]}  # Limiting to 4000 chars to stay within token limits

    Categorize this email into one of the following:
    1. "sponsorship" - Companies wanting to sponsor content or services
    2. "business_inquiry" - Business-related emails, partnership offers, marketing opportunities
    3. "other" - Everything else

    If it's a sponsorship or business inquiry, extract the company name and the main topic/product.

    Respond with a JSON object that MUST include:
    {{
        "category": "sponsorship" | "business_inquiry" | "other",
        "confidence": <number between 0 and 1>,
        "reason": <explanation string>,
        "company_name": <extracted company name or null>,
        "topic": <main topic/product or null>
    }}
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4.1",  # Use appropriate OpenAI model
            messages=[
                {
                    "role": "system", 
                    "content": "You are a precise email categorizer. Your goal is to accurately categorize emails and extract relevant business information."
                },
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        if content:
            analysis = json.loads(content)
            # Print for debugging
            log(f"Analyzing: {email['subject']}")
            log(f"Analysis result: {json.dumps(analysis, indent=2)}")
            return EmailAnalysis(**analysis)
        else:
            log(f"Empty response for email: {email['subject']}")
            return None
            
    except Exception as e:
        log(f"Error analyzing email: {e}")
        log(f"Failed email subject: {email['subject']}")
        return None

def sort_emails():
    """Main function to sort emails"""
    # First fetch new emails
    log("Fetching new emails...")
    get_emails(hours=72)
    
    # Initialize OpenAI client
    client = OpenAI()
    
    # Read emails
    emails = read_emails()
    
    # Categorize emails
    sponsorship_emails = []
    business_emails = []
    other_emails = []
    
    # Analyze each email
    for email in emails:
        analysis = analyze_email(client, email)
        if analysis:
            email_data = {
                "subject": email["subject"],
                "from": email["from"],
                "received": email.get("received", datetime.now().isoformat()),
                "body": email["body"],
                "analysis": analysis.model_dump()
            }
            
            if analysis.category == "sponsorship":
                sponsorship_emails.append(email_data)
            elif analysis.category == "business_inquiry":
                business_emails.append(email_data)
            else:
                other_emails.append(email_data)
    
    # Save results to JSON files
    output_data = {
        "last_updated": datetime.now().isoformat(),
        "sponsorship_emails": sponsorship_emails,
        "business_emails": business_emails,
        "other_emails": other_emails
    }
    
    with open(CATEGORIZED_EMAILS_JSON, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2)
    log("Saved categorized_emails.json")
    
    # Print summary
    log(f"Processed {len(emails)} emails")
    log(f"Sponsorship requests: {len(sponsorship_emails)}")
    log(f"Business inquiries: {len(business_emails)}")
    log(f"Other emails: {len(other_emails)}")
    log(f"Detailed results saved to: {CATEGORIZED_EMAILS_JSON}")
    
    # Print high-confidence business and sponsorship emails
    log("High Confidence Business/Sponsorship Emails (>0.8):")
    for email in sponsorship_emails + business_emails:
        if email["analysis"]["confidence"] > 0.8:
            log(f"Category: {email['analysis']['category']}")
            log(f"From: {email['from']}")
            log(f"Subject: {email['subject']}")
            if email["analysis"]["company_name"]:
                log(f"Company: {email['analysis']['company_name']}")
            if email["analysis"]["topic"]:
                log(f"Topic: {email['analysis']['topic']}")
            log(f"Reason: {email['analysis']['reason']}")
            log("-" * 50)

def generate_opportunity_report(categorized_emails_path=CATEGORIZED_EMAILS_JSON):
    """Generate a structured report highlighting valuable business opportunities"""
    try:
        # Load categorized emails
        with open(categorized_emails_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Extract business and sponsorship emails
        business_emails = data.get("business_emails", [])
        sponsorship_emails = data.get("sponsorship_emails", [])
        
        all_relevant_emails = business_emails + sponsorship_emails
        
        if not all_relevant_emails:
            log("No business or sponsorship emails found to analyze.")
            return
            
        # Initialize OpenAI client
        client = OpenAI()
        
        # Analyze emails to identify quality opportunities
        log("Analyzing business and sponsorship emails for quality opportunities...")
        
        # Create a report with AI analysis
        prompt = f"""
        You are an executive assistant tasked with filtering through business and sponsorship emails to identify the highest quality opportunities.
        
        Please analyze these {len(all_relevant_emails)} business and sponsorship emails and create a structured report that:
        
        1. Categorizes them as "High Value" or "Mass Marketing/Generic"
        2. Ranks the high-value opportunities in order of priority
        3. Provides brief reasoning for your assessments
        
        Here are the emails to analyze:
        
        {json.dumps([{
            "category": email["analysis"]["category"],
            "from": email["from"],
            "subject": email["subject"],
            "company": email["analysis"]["company_name"],
            "topic": email["analysis"]["topic"],
            "confidence": email["analysis"]["confidence"],
            "snippet": email["body"][:500] + "..." if len(email["body"]) > 500 else email["body"]
        } for email in all_relevant_emails], indent=2)}
        
        Consider the following criteria to evaluate opportunities:
        1. Personalization (specifically addressed to the user, mentions specific work)
        2. Authenticity (not mass-marketing, personal tone, unique request)
        3. Relevance (aligns with user's work, interesting topic, reasonable offer)
        4. Reputation (known company, established person, verifiable identity)
        5. Specificity (clear request/opportunity with details, not vague)
        
        Format your report with clear sections and prioritize opportunities that seem unique, personalized, and valuable.
        """
        
        response = client.chat.completions.create(
            model="gpt-4",  # Use appropriate OpenAI model
            messages=[
                {
                    "role": "system", 
                    "content": "You are an executive assistant who helps identify high-quality opportunities from business emails. You excel at distinguishing personalized offers from mass marketing campaigns."
                },
                {"role": "user", "content": prompt}
            ]
        )
        
        report = response.choices[0].message.content
        
        log("BUSINESS AND SPONSORSHIP OPPORTUNITY REPORT")
        log(report)

        with open(OPPORTUNITY_REPORT, "w", encoding="utf-8") as f:
            json.dump({
                "generated_on": datetime.now().isoformat(),
                "report": report
            }, f, indent=2)
        log(f"Report saved to {OPPORTUNITY_REPORT}")
            
    except FileNotFoundError:
        log(f"Error: File {categorized_emails_path} not found. Please run sort_emails() first.")
    except Exception as e:
        log(f"Error generating opportunity report: {e}")

if __name__ == "__main__":
    # First sort the emails
    sort_emails()
    
    # Then generate the opportunity report
    generate_opportunity_report() 
