# 📧 Inbox Zero AI Agent System

An AI-powered email management system that helps you achieve inbox zero by intelligently filtering, categorizing, and responding to emails. This system uses OpenAI's GPT models to identify important emails, categorize business opportunities, and draft appropriate responses.

![Inbox Zero](https://img.shields.io/badge/Inbox-Zero-green)
![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![OpenAI](https://img.shields.io/badge/AI-OpenAI%20GPT--4-purple)

## 🌟 Features

- **Smart Email Filtering**: Identifies which emails actually require your attention
- **Business Opportunity Detection**: Categorizes emails into sponsorships, business inquiries, and others
- **Automated Response Generation**: Drafts personalized responses to important emails
- **Provider Agnostic**: Works with any email provider (Gmail, Outlook, etc.) through simple adapter functions
- **Spam & Marketing Detection**: Intelligently filters out mass marketing emails from genuine opportunities

## 📋 Components

The system consists of three main components:

1. **Important Email Detector** (`important_email2.py`): Analyzes your inbox and identifies emails that truly need your attention
2. **Email Categorizer** (`send_mail2.py`): Categorizes business-related emails and generates opportunity reports
3. **Email Response Generator** (`email_responder2.py`): Creates draft responses that you can review, edit, and send

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- OpenAI API key

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/AllAboutAI-YT/email-agents.git
   cd email-agents
   ```

2. Install the required dependencies:
   ```bash
   pip install python-dotenv openai
   ```

3. Create a `.env` file with your OpenAI API key:
   ```
   OPENAI_API_KEY=your_openai_api_key_here
   ```

### Connecting to Your Email Provider

To use the system with your email provider, you need to implement several provider-specific functions:

#### In `important_email2.py`:

```python
def get_emails(hours=24):
    """Implement this function to fetch emails from your provider"""
    # Your implementation here
    
def get_sent_emails(days=7):
    """Implement this function to fetch sent emails from your provider"""
    # Your implementation here
```

#### In `send_mail2.py`:

```python
def get_emails(hours=72):
    """Implement this function to fetch emails from your provider"""
    # Your implementation here
    
def send_email(subject, body, recipient_email):
    """Implement this function to send emails through your provider"""
    # Your implementation here
```

## 🔍 Usage

### Step 1: Find Important Emails

```bash
python important_email2.py
```

This will:
- Scan your inbox for emails from the last 24 hours
- Analyze each email for importance
- Generate a report of emails requiring your attention

### Step 2: Categorize Business Opportunities

```bash
python send_mail2.py
```

This will:
- Analyze emails from the last 72 hours
- Categorize them as sponsorships, business inquiries, or other
- Generate a report of high-value opportunities

### Step 3: Generate and Send Responses

```bash
python email_responder2.py
```

This will:
- Read important emails identified in Step 1
- Draft customized responses for each email
- Let you review, edit, and send the responses with a simple Y/N interface

## ⚙️ Configuration

You can adjust the system's behavior by modifying constants at the top of each file:

- Change the time period for email scanning (24 hours, 72 hours, etc.)
- Modify file paths for generated reports
- Adjust AI parameters for more detailed analysis

## 📁 Output Files

The system generates several output files:

- `needs_response_report.txt`: Human-readable report of emails needing responses
- `opportunity_report.txt`: Report of business opportunities
- `response_history.json`: Tracking which emails have been responded to

## 🛡️ Security

- All API keys are stored in the `.env` file (not in Git)
- The `.gitignore` file prevents sensitive data from being committed

## 🤝 Contributing

Contributions are welcome! Feel free to submit issues or pull requests if you have ideas for improvements.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgements

- [OpenAI](https://openai.com/) for providing the GPT models that power the email analysis
- All contributors and users of this project 