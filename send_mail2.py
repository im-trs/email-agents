import os
from dotenv import load_dotenv
import json
from datetime import datetime, timedelta
from openai import OpenAI
from pydantic import BaseModel
from typing import Optional, Literal

# Load environment variables
load_dotenv(override=True)

class EmailAnalysis(BaseModel):
    category: Literal["sponsorship", "business_inquiry", "other"]
    confidence: float
    reason: str
    company_name: Optional[str] = None
    topic: Optional[str] = None

# File paths
EMAILS_FILE = "emails.txt"
CATEGORIZED_EMAILS_JSON = "categorized_emails.json"
OPPORTUNITY_REPORT = "opportunity_report.txt"

# Function that should be implemented by the user
def send_email(subject, body, recipient_email):
    """
    PLACEHOLDER: User should implement this function to send emails
    
    This function should:
    1. Connect to the user's email provider
    2. Send an email to the specified recipient
    
    Args:
        subject: Email subject
        body: Email body content
        recipient_email: Recipient's email address
        
    Returns:
        bool: True if the email was sent successfully, False otherwise
    """
    print(f"PLACEHOLDER: This function should send an email with subject '{subject}' to {recipient_email}")
    print("Implement this function to connect to your email provider")
    
    # For testing purposes, just print the email
    print("\n----- EMAIL CONTENT -----")
    print(f"To: {recipient_email}")
    print(f"Subject: {subject}")
    print(f"Body:\n{body}")
    print("-" * 30)
    
    # Return True to simulate successful sending
    return True

# Function that should be implemented by the user
def get_emails(hours=72):
    """
    PLACEHOLDER: User should implement this function to fetch emails from their provider
    
    This function should:
    1. Connect to the user's email provider
    2. Fetch emails from the last {hours} hours
    3. Save basic email data to EMAILS_FILE in the format:
       Subject: <subject>
       From: <sender name> <sender_email>
       Received: <datetime>
       Body: <email body>
       ------------------------------------------------
    
    Args:
        hours: Number of hours to look back for emails
        
    Returns:
        List of email dictionary objects with keys:
        - subject: Email subject
        - from: Sender information
        - receivedDateTime: When the email was received
        - body: Email body content
    """
    print(f"PLACEHOLDER: This function should fetch emails from the last {hours} hours")
    print("Implement this function to connect to your email provider")
    
    # Return empty list as placeholder
    # When implementing, return actual email data from your provider
    return []

def read_emails():
    """Read emails from emails.txt and return as a list of dictionaries"""
    try:
        with open(EMAILS_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"No {EMAILS_FILE} file found. Creating empty file.")
        with open(EMAILS_FILE, "w", encoding="utf-8") as f:
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
            print(f"\nAnalyzing: {email['subject']}")
            print(f"Analysis result: {json.dumps(analysis, indent=2)}")
            return EmailAnalysis(**analysis)
        else:
            print(f"Empty response for email: {email['subject']}")
            return None
            
    except Exception as e:
        print(f"Error analyzing email: {e}")
        print(f"Failed email subject: {email['subject']}")
        return None

def sort_emails():
    """Main function to sort emails"""
    # First fetch new emails
    print("Fetching new emails...")
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
    
    # Print summary
    print(f"\nProcessed {len(emails)} emails")
    print(f"Sponsorship requests: {len(sponsorship_emails)}")
    print(f"Business inquiries: {len(business_emails)}")
    print(f"Other emails: {len(other_emails)}")
    print(f"\nDetailed results saved to: {CATEGORIZED_EMAILS_JSON}")
    
    # Print high-confidence business and sponsorship emails
    print("\nHigh Confidence Business/Sponsorship Emails (>0.8):")
    for email in sponsorship_emails + business_emails:
        if email["analysis"]["confidence"] > 0.8:
            print(f"\nCategory: {email['analysis']['category']}")
            print(f"From: {email['from']}")
            print(f"Subject: {email['subject']}")
            if email["analysis"]["company_name"]:
                print(f"Company: {email['analysis']['company_name']}")
            if email["analysis"]["topic"]:
                print(f"Topic: {email['analysis']['topic']}")
            print(f"Reason: {email['analysis']['reason']}")
            print("-" * 50)

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
            print("No business or sponsorship emails found to analyze.")
            return
            
        # Initialize OpenAI client
        client = OpenAI()
        
        # Analyze emails to identify quality opportunities
        print("\nAnalyzing business and sponsorship emails for quality opportunities...")
        
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
        
        # Print the report
        print("\n" + "="*50)
        print("BUSINESS AND SPONSORSHIP OPPORTUNITY REPORT")
        print("="*50 + "\n")
        print(report)
        
        # Save the report to a file
        with open(OPPORTUNITY_REPORT, "w", encoding="utf-8") as f:
            f.write("BUSINESS AND SPONSORSHIP OPPORTUNITY REPORT\n")
            f.write("="*50 + "\n\n")
            f.write(report)
            
        print(f"\nReport saved to {OPPORTUNITY_REPORT}")
            
    except FileNotFoundError:
        print(f"Error: File {categorized_emails_path} not found. Please run sort_emails() first.")
    except Exception as e:
        print(f"Error generating opportunity report: {e}")

if __name__ == "__main__":
    # First sort the emails
    sort_emails()
    
    # Then generate the opportunity report
    generate_opportunity_report() 
