#!/usr/bin/env python3
"""
test_email.py

Sends a test email with a sample EPUB attachment directly to a target email address
to verify SMTP credentials and email delivery.

Usage:
  python3 scripts/test_email.py --to user@example.com
"""

import os
import sys
import shutil
import argparse
import subprocess
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def create_sample_epub(output_path):
    """Creates a small sample EPUB using pandoc (with Mermaid diagram support) for testing."""
    sample_md = os.path.join("/tmp", "sample_test.md")
    content = """# Kindle Delivery Test

This is a test document sent from your GitHub Actions workflow to verify email delivery and diagram rendering!

## Sample System Architecture Diagram

```mermaid
graph TD
    Producer[Event Producer] -->|Publish Event| Ingestion[Ingestion Service]
    Ingestion -->|Push to Queue| Queue[Message Broker Queue]
    Queue -->|Deliver| Worker[Delivery Workers]
    Worker -->|Send Push| Kindle[Kindle Device]
```

Happy reading!
"""
    with open(sample_md, "w") as f:
        f.write(content)
    
    cmd = [
        "pandoc",
        sample_md,
        "-o", output_path,
        "--metadata=title:Test Delivery",
        "--metadata=author:Notification System Course"
    ]

    if shutil.which("mermaid-filter"):
        cmd.extend(["--filter", "mermaid-filter"])
        print("Enabling mermaid-filter for rendering test diagram...")

    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"Created sample test EPUB at {output_path}")
    except FileNotFoundError:
        sys.exit("Error: 'pandoc' is not installed.")
    except subprocess.CalledProcessError as e:
        sys.exit(f"Error creating EPUB via pandoc: {e.stderr.decode('utf-8')}")


def send_test_email(recipient, smtp_user, smtp_pass, smtp_server, smtp_port):
    epub_path = "/tmp/test_sample.epub"
    create_sample_epub(epub_path)

    msg = MIMEMultipart()
    msg['From'] = smtp_user
    msg['To'] = recipient
    msg['Subject'] = "Kindle Workflow Test Email"

    msg.attach(MIMEText("Hello!\n\nThis is a test email sent from your Kindle workflow to verify SMTP setup. Attached is a sample EPUB file with diagram rendering.\n", 'plain'))

    with open(epub_path, "rb") as f:
        part = MIMEBase("application", "epub+zip")
        part.set_payload(f.read())
    encoders.encode_base64(part)
    part.add_header('Content-Disposition', f'attachment; filename="test_sample.epub"')
    msg.attach(part)

    print(f"Connecting to SMTP server {smtp_server}:{smtp_port}...")
    server = smtplib.SMTP(smtp_server, int(smtp_port))
    server.starttls()
    server.login(smtp_user, smtp_pass)
    server.sendmail(smtp_user, recipient, msg.as_string())
    server.quit()
    print(f"✅ SUCCESS: Test email successfully sent to {recipient}!")


def main():
    parser = argparse.ArgumentParser(description="Test SMTP email delivery.")
    parser.add_argument("--to", help="Recipient email address")
    args = parser.parse_args()

    smtp_user = os.environ.get("SMTP_USER")
    smtp_pass = os.environ.get("SMTP_PASS")
    smtp_server = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = os.environ.get("SMTP_PORT", "587")
    recipient = args.to or smtp_user

    if not smtp_user or not smtp_pass:
        sys.exit("Error: Missing SMTP_USER or SMTP_PASS environment variables.")

    send_test_email(recipient, smtp_user, smtp_pass, smtp_server, smtp_port)


if __name__ == "__main__":
    main()
