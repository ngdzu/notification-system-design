---
name: ask
description: Ask a clarifying question about the current or a specific lesson in the notification-system study plan. Answers it in beginner-friendly style and permanently records the question and answer so it can resurface later as a test question. Use whenever something in a lesson is unclear, e.g. "/ask 6 why does consumer group rebalancing happen" or just "/ask why does that happen" mid-session.
---

# ask

The point of this skill is that **no clarifying question is ever thrown
away** — every one becomes a future test question via `/quiz` and `/review`.

## Steps

1. Figure out which lesson this question is about:
   - If the argument starts with a lesson number, use that.
   - Otherwise infer it from what's currently being discussed in the
     conversation (the most recently loaded/quizzed lesson).
   - If it's genuinely ambiguous, ask the user which lesson before answering.
2. Answer the question directly, in the same beginner-friendly style as the
   lessons: define any term you use that hasn't already been introduced,
   use a concrete example or analogy where it helps, and keep the answer
   self-contained (don't say "see above" — someone rereading only this Q&A
   entry later, out of context, should fully understand it).
3. Append the exchange to `lessons/NN-slug/qa.md` (create the file if it
   doesn't exist yet), in this format:

   ```
   ## Q: <question as asked> (<YYYY-MM-DD>)
   <full answer>
   ```

4. If answering reveals the lesson file itself has a gap or error, say so
   out loud to the user, but don't edit `lessons/NN-slug/lesson.md` unless
   they ask you to.
5. Do not quiz the user back in this skill — just answer. Testing happens in
   `/quiz` and `/review`, using this log as material.
