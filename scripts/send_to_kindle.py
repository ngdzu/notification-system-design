#!/usr/bin/env python3
"""
send_to_kindle.py

Automated script to convert course lessons (Markdown) to EPUB and email them to a Kindle device.
Can run locally or automatically in GitHub Actions (with laptop turned off).

Features:
1. Tracks progress via .kindle_state.json.
2. Converts lesson Markdown files to EPUB using Pandoc (with optional Mermaid filter for visual diagrams).
3. Emails the EPUB attachment to Kindle via SMTP (Gmail).
5. Updates .kindle_state.json (which GitHub Actions commits back to GitHub).
"""

import os
import sys
import glob
import json
import shutil
import argparse
import subprocess
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ["MERMAID_FILTER_PUPPETEER_CONFIG"] = os.path.join(REPO_ROOT, "puppeteer-config.json")
STATE_FILE = os.path.join(REPO_ROOT, ".kindle_state.json")
LESSONS_DIR = os.path.join(REPO_ROOT, "lessons")

LESSON_SLUGS = {
    1: "01-push-vs-pull-vs-poll",
    2: "02-high-level-architecture",
    3: "03-channels-and-priority-tiers",
    4: "04-fanout-write-vs-read",
    5: "05-celebrity-problem-hot-keys",
    6: "06-message-brokers-and-queues",
    7: "07-sharding-and-partitioning",
    8: "08-push-delivery-mechanics",
    9: "09-connection-routing",
    10: "10-pull-fallback",
    11: "11-replay-buffers",
    12: "12-idempotency-and-deduplication",
    13: "13-backpressure-and-rate-limiting",
    14: "14-delivery-guarantees",
    15: "15-monitoring-and-observability",
    16: "16-failure-recovery-and-dlqs",
    17: "17-capstone-walkthrough",
}


def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"last_sent_lesson": 0, "sent_history": []}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)




def convert_to_epub(md_file, title, output_epub_path):
    """Converts Markdown to EPUB using pandoc, with mermaid-filter if installed."""
    cmd = [
        "pandoc",
        md_file,
        "-o", output_epub_path,
        f"--metadata=title:{title}",
        "--metadata=author:System Design Notification Course",
        "--toc"
    ]

    if shutil.which("mermaid-filter"):
        filter_cmd = list(cmd) + ["--filter", "mermaid-filter"]
        print("Enabling mermaid-filter for rendering visual diagrams...")
        try:
            subprocess.run(filter_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return
        except subprocess.CalledProcessError as e:
            print(f"[WARNING] mermaid-filter failed: {e.stderr.decode('utf-8').strip()}\nFalling back to standard pandoc conversion without mermaid diagrams...")

    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except FileNotFoundError:
        sys.exit("Error: 'pandoc' is not installed on the system.")
    except subprocess.CalledProcessError as e:
        sys.exit(f"Error converting {md_file} to EPUB via pandoc:\n{e.stderr.decode('utf-8')}")


def send_email_with_epub(epub_path, title, recipient, smtp_user, smtp_pass, smtp_server, smtp_port):
    """Sends the EPUB attachment to recipient via SMTP TLS."""
    msg = MIMEMultipart()
    msg['From'] = smtp_user
    msg['To'] = recipient
    msg['Subject'] = title

    msg.attach(MIMEText(f"Attached is your daily lesson: {title}\n\nHappy reading!", 'plain'))

    filename = os.path.basename(epub_path)
    with open(epub_path, "rb") as f:
        part = MIMEBase("application", "epub+zip")
        part.set_payload(f.read())
    encoders.encode_base64(part)
    part.add_header('Content-Disposition', f'attachment; filename="{filename}"')
    msg.attach(part)

    print(f"Connecting to SMTP server {smtp_server}:{smtp_port}...")
    server = smtplib.SMTP(smtp_server, int(smtp_port))
    server.starttls()
    server.login(smtp_user, smtp_pass)
    server.sendmail(smtp_user, recipient, msg.as_string())
    server.quit()
    print(f"Successfully delivered {filename} to {recipient}")


def main():
    parser = argparse.ArgumentParser(description="Convert lesson to EPUB and send to Kindle.")
    parser.add_argument("--lesson", type=int, help="Lesson number to send (e.g., 1)")
    parser.add_argument("--dry-run", action="store_true", help="Convert to EPUB only, do not send email")
    args = parser.parse_args()

    state = load_state()

    if args.lesson:
        target_num = args.lesson
    else:
        last_sent = state.get("last_sent_lesson", 0)
        target_num = last_sent + 1

    if target_num not in LESSON_SLUGS and target_num > max(LESSON_SLUGS.keys()):
        print("Congratulations! All course lessons have been delivered to your Kindle.")
        return

    slug = LESSON_SLUGS.get(target_num, f"{target_num:02d}-lesson")
    md_file = os.path.join(LESSONS_DIR, slug, "lesson.md")

    if not os.path.exists(md_file):
        sys.exit(f"Lesson {target_num} ({md_file}) does not exist yet. All lessons must be pre-generated and committed to the repository.")

    lesson_title = f"Lesson {target_num:02d}: {slug.replace('-', ' ').title()}"
    output_epub = os.path.join("/tmp", f"{slug}.epub")

    print(f"Converting '{md_file}' to EPUB...")
    convert_to_epub(md_file, lesson_title, output_epub)
    print(f"Created EPUB: {output_epub}")

    if args.dry_run:
        print("Dry-run mode active. Skipping email dispatch.")
        return

    smtp_user = os.environ.get("SMTP_USER")
    smtp_pass = os.environ.get("SMTP_PASS")
    smtp_server = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = os.environ.get("SMTP_PORT", "587")
    kindle_email = os.environ.get("KINDLE_EMAIL")

    if not smtp_user or not smtp_pass or not kindle_email:
        print("\n[WARNING] Missing SMTP_USER, SMTP_PASS, or KINDLE_EMAIL environment variables.")
        sys.exit(1)

    send_email_with_epub(output_epub, lesson_title, kindle_email, smtp_user, smtp_pass, smtp_server, smtp_port)

    # Save state
    state["last_sent_lesson"] = target_num
    if "sent_history" not in state:
        state["sent_history"] = []
    state["sent_history"].append({"num": target_num, "slug": slug})
    save_state(state)


if __name__ == "__main__":
    main()
