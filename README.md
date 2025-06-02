# 📧 Inbox Zero AI Agent System

This project helps you reach **inbox zero**. It uses OpenAI models to scan your inbox, find important messages, categorize business opportunities and draft short replies. The email integration now works out-of-the-box with any provider that supports IMAP and SMTP through a few environment variables.

![Inbox Zero](https://img.shields.io/badge/Inbox-Zero-green)
![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![OpenAI](https://img.shields.io/badge/AI-OpenAI%20GPT--4-purple)

## 🌟 Features

- **Smart Email Filtering** – analyzes which messages truly require attention
- **Business Opportunity Detection** – categorizes sponsorship and business emails
- **Automated Response Generation** – drafts quick replies that you can edit
- **Built‑in IMAP/SMTP Support** – works with Gmail, Outlook or one.com just by setting credentials
- **Local LLM Option** – route sensitive emails to a local model instead of the OpenAI API

## 📋 Components

1. **Important Email Detector** – `important_email2.py`
2. **Email Categorizer** – `send_mail2.py`
3. **Response Generator** – `email_responder2.py`

## 🚀 Installation

1. Install Python 3.8+.
2. Clone the repository and install the requirements:
   ```bash
   git clone https://github.com/AllAboutAI-YT/email-agents.git
   cd email-agents
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and fill in your email credentials and OpenAI key. These variables configure the IMAP/SMTP connection and the API key.

## 🔧 Running the tools

1. **Find important emails**
   ```bash
   python important_email2.py
   ```
   Generates `output/needs_response_report.json` with the messages that require your reply.
2. **Categorize business opportunities**
   ```bash
   python send_mail2.py
   ```
   Writes results to `output/categorized_emails.json` and an opportunity report.
3. **Draft and send responses**
   ```bash
   python email_responder2.py
   ```
   Walks through each email so you can review and send a generated reply.

## 🛠 Developer guide

- Run `pytest` to execute the unit tests.
- Modify the scripts or create new modules as needed. The IMAP/SMTP functions already handle fetching and sending email (see `important_email2.py` and `send_mail2.py`). Environment variable names are the same ones used in `.env.example`.
- Keep data files such as those in the `output/` folder out of version control.

## 🙋 How to use (non‑technical overview)

1. Install Python from [python.org](https://www.python.org/downloads/).
2. Download the project (or clone it if you use Git) and open a command prompt inside the folder.
3. Create a file named `.env` by copying `.env.example` and typing your email address, password and the server names shown in the example. Also paste your OpenAI API key.
4. Type `pip install -r requirements.txt` to install everything.
5. Run the programs one by one as shown above. Each step prints instructions on the screen and saves a text report you can open with any editor.

## ⚙️ Configuration

- Adjust the time ranges or output file paths at the top of each Python file.
- Set `OPENAI_API_KEY` in `.env` to use the OpenAI API, or modify the scripts to call a local model if you prefer.

## 📁 Output files

- `output/needs_response_report.json` – list of messages requiring a reply
- `output/categorized_emails.json` – JSON export of analyzed emails
- `output/opportunity_report.json` – summary of good business leads
- `output/response_history.json` – log of emails you have answered

## 🛡️ Security

Your credentials remain in the local `.env` file and are ignored by Git. If the emails are extremely sensitive, switch the code to a local language model so nothing is sent to OpenAI.

## 🤝 Contributing

Pull requests and ideas are welcome!

## 📄 License

MIT

