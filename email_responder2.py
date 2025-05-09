import os
import json
import re
from openai import OpenAI
from dotenv import load_dotenv
from send_mail2 import send_email  # Importing the placeholder send_email function

# Load environment variables
load_dotenv(override=True)

# File paths
NEEDS_RESPONSE_REPORT = "needs_response_report.txt"
RESPONSE_HISTORY_FILE = "response_history.json"

def extract_emails_from_report(report_path=NEEDS_RESPONSE_REPORT):
    """Extract emails from the needs_response_report.txt file"""
    try:
        with open(report_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Split the report by the separator
        email_sections = content.split("-" * 50)
        
        # Extract information from each section
        emails = []
        for section in email_sections:
            if not section.strip():
                continue
            
            # Extract key details using regex
            subject_match = re.search(r"Subject: (.+?)$", section, re.MULTILINE)
            from_match = re.search(r"From: (.+?)$", section, re.MULTILINE)
            email_address_match = re.search(r"<(.+?)>", section)
            preview_match = re.search(r"Preview: (.+?)$", section, re.MULTILINE | re.DOTALL)
            already_responded = "ALREADY RESPONDED" in section
            
            if subject_match and from_match:
                email_data = {
                    "subject": subject_match.group(1).strip(),
                    "from": from_match.group(1).strip(),
                    "email_address": email_address_match.group(1).strip() if email_address_match else None,
                    "preview": preview_match.group(1).strip() if preview_match else "No preview available",
                    "already_responded": already_responded
                }
                emails.append(email_data)
        
        return emails
    
    except FileNotFoundError:
        print(f"Error: File {report_path} not found.")
        return []
    except Exception as e:
        print(f"Error extracting emails from report: {e}")
        return []

def save_response_history(new_response):
    """Save a record of an email we've responded to"""
    try:
        # Load existing history
        try:
            with open(RESPONSE_HISTORY_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            history = {"responded_emails": []}
        
        # Add the new response
        history["responded_emails"].append({
            "subject": new_response["subject"],
            "from": new_response["from"],
            "responded_at": new_response["responded_at"]
        })
        
        # Save back to file
        with open(RESPONSE_HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)
            
        return True
    except Exception as e:
        print(f"Error saving response history: {e}")
        return False

def generate_response(client, email_data, edit_instructions=None):
    """Generate a response email using OpenAI"""
    if edit_instructions:
        prompt = f"""
        Rewrite the email response based on these instructions:
        
        Original Email:
        Subject: {email_data['subject']}
        From: {email_data['from']}
        Preview: {email_data['preview'][:500]}
        
        Instructions for rewriting: {edit_instructions}
        
        Your response should maintain this format:
        Subject: Re: [Original Subject]
        
        [Email body]
        
        Best regards,
        Kris
        """
    else:
        prompt = f"""
        Create a concise and helpful email response for the following inquiry:
        
        Subject: {email_data['subject']}
        From: {email_data['from']}
        Preview: {email_data['preview'][:1000]}
        
        Requirements:
        1. Keep the response friendly but brief and to the point
        2. Address any specific questions or requests in the email
        3. Be professional and helpful
        4. Always end with "Best regards,\nKris"
        5. Include appropriate subject line with "Re: " prefix
        6. Don't be overly verbose - keep it under 150 words
        7. Don't apologize for delay unless clearly necessary
        
        Your response should be formatted as:
        Subject: Re: [Original Subject]
        
        [Email body]
        
        Best regards,
        Kris
        """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4",  # Use appropriate OpenAI model
            messages=[
                {
                    "role": "system", 
                    "content": "You are a professional, concise email responder who crafts helpful, direct responses to business inquiries."
                },
                {"role": "user", "content": prompt}
            ]
        )
        
        return response.choices[0].message.content
    
    except Exception as e:
        print(f"Error generating response: {e}")
        return None

def process_responses():
    """Process and send responses to important emails"""
    # Initialize OpenAI client
    client = OpenAI()
    
    # Extract emails from report
    emails = extract_emails_from_report()
    
    if not emails:
        print("No emails requiring response found in the report.")
        return
    
    # Count new emails (not already responded to)
    new_emails = [email for email in emails if not email['already_responded']]
    
    print(f"Found {len(emails)} emails requiring response ({len(new_emails)} new, {len(emails) - len(new_emails)} already responded to).\n")
    
    # Process each email
    for i, email_data in enumerate(emails, 1):
        print("=" * 50)
        print(f"Email {i}/{len(emails)}")
        print(f"Subject: {email_data['subject']}")
        print(f"From: {email_data['from']}")
        
        if email_data['already_responded']:
            print(f"STATUS: ✅ ALREADY RESPONDED")
            choice = input("\nThis email has already been responded to. Process anyway? (y/n): ").lower()
            if choice != 'y':
                print("Skipping to next email...")
                print()
                continue
        
        print("-" * 50)
        
        # Generate a response
        draft_response = generate_response(client, email_data)
        
        if not draft_response:
            print("Failed to generate a response. Skipping to next email.")
            continue
        
        while True:
            # Extract subject and body from the generated response
            response_lines = draft_response.strip().split('\n')
            subject_line = response_lines[0].replace('Subject:', '').strip()
            body = '\n'.join(response_lines[1:]).strip()
            
            # Display the draft response
            print("\nDRAFT RESPONSE:")
            print("-" * 50)
            print(f"To: {email_data['email_address']}")
            print(f"Subject: {subject_line}")
            print("-" * 50)
            print(body)
            print("-" * 50)
            
            # Ask for confirmation
            choice = input("\nSend this response? (y/n/edit/skip): ").lower()
            
            if choice == 'y':
                if email_data['email_address']:
                    print(f"Sending email to {email_data['email_address']}...")
                    result = send_email(subject_line, body, email_data['email_address'])
                    if result:
                        print("Email sent successfully!")
                        # Record this response in history
                        save_response_history({
                            "subject": email_data['subject'],
                            "from": email_data['from'],
                            "responded_at": datetime.now().isoformat() if 'datetime' in globals() else "2023-01-01T00:00:00"
                        })
                    else:
                        print("Failed to send email.")
                else:
                    print("Error: No email address found for recipient.")
                break
            elif choice == 'n':
                print("Skipping this email.")
                break
            elif choice == 'skip':
                print("Marked as skipped.")
                break
            elif choice == 'edit':
                # Prompt for edit instructions
                print("\nDescribe how you want the email rewritten:")
                edit_instructions = input("> ")
                
                # Generate a new response based on the edit instructions
                print("\nGenerating new response based on your instructions...")
                new_draft = generate_response(client, email_data, edit_instructions)
                
                if new_draft:
                    draft_response = new_draft
                else:
                    print("Failed to generate edited response. Keeping previous draft.")
                
                # Continue loop to display the new draft and prompt y/n/edit again
            else:
                print("Invalid choice. Please enter 'y', 'n', 'edit', or 'skip'.")
        
        print()  # Add a blank line between emails
    
    print("\nAll emails processed.")

if __name__ == "__main__":
    # Import datetime here to avoid circular imports 
    from datetime import datetime
    process_responses() 