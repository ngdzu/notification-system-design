# Notification System Study

Self-study notes for one system design interview problem: designing a push
notification system for a social-media-scale product (hundreds of millions of
users), covering fan-out, message brokers, connection routing, replay
buffers, backpressure, delivery guarantees, monitoring, and failure recovery.

- Start here: [`.plan/plan.md`](.plan/plan.md) — the full 17-lesson curriculum.
- Lessons are written one at a time into `lessons/` as you work through them.
- See [`AGENTS.md`](AGENTS.md) for the conventions each lesson follows.

## Automated Daily Kindle Delivery

You can fork this repository to receive daily lessons on your Kindle automatically via GitHub Actions:

1. **Fork this repository**.
2. **Add GitHub Secrets** in **Settings** $\rightarrow$ **Secrets and variables** $\rightarrow$ **Actions**:
   - `SMTP_USER`: Email address to send from (e.g. Gmail).
   - `SMTP_PASS`: Email App Password.
   - `KINDLE_EMAIL`: Destination Kindle email address (`username@kindle.com`).
   - `GEMINI_API_KEY` *(Optional)*: Required if auto-generating missing lessons.
3. **Approve Sender Email in Amazon**: Add your `SMTP_USER` email to your **Approved Personal Document E-mail List** under Amazon account $\rightarrow$ *Manage Your Content and Devices* $\rightarrow$ *Preferences* $\rightarrow$ *Personal Document Settings*.
4. **Enable Workflows**: In the fork's **Actions** tab, enable workflows and grant **Read and write permissions** under **Settings** $\rightarrow$ **Actions** $\rightarrow$ **General** $\rightarrow$ **Workflow permissions**.
