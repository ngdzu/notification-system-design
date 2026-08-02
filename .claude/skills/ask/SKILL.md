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
2. **Split the input into distinct questions first.** If the user asked more
   than one question in a single `/ask` call (e.g. "where is X located? and
   is Y talking about A or B in general?"), treat each as a separate
   question — do not blend them into one merged answer. This applies even
   when the questions are related or share context.
3. Answer each question directly and separately, in the same
   beginner-friendly style as the lessons: define any term you use that
   hasn't already been introduced, use a concrete example or analogy where
   it helps, and keep each answer self-contained (don't say "see above" —
   someone rereading only that one Q&A entry later, out of context, should
   fully understand it). An answer to question 2 may reference the answer to
   question 1 by restating the relevant fact, not by pointing back to it.
4. Append each question as its own entry to `lessons/NN-slug/qa.md` (create
   the file if it doesn't exist yet), in this format — one `## Q<N>:` block
   per question, even if they arrived in the same `/ask` call:

   ```
   ## Q<N>: <question 1 as asked> (<YYYY-MM-DD>)
   <full answer to question 1>

   ## Q<N+1>: <question 2 as asked> (<YYYY-MM-DD>)
   <full answer to question 2>
   ```

   `<N>` is a running number, sequential within that lesson's `qa.md`,
   never reused or reset. Before writing, scan the file for the highest
   existing `## Q<N>:` and continue from there (start at `Q1` for a new
   file). If the user's question references an earlier one by number (e.g.
   "follow up to Q3" or just "Q3"), treat it as a follow-up to that exact
   entry: read it for context and make the new answer build on it rather
   than re-deriving everything from scratch.
5. If answering reveals the lesson file itself has a gap or error, say so
   out loud to the user, but don't edit `lessons/NN-slug/lesson.md` unless
   they ask you to.
6. Do not quiz the user back in this skill — just answer. Testing happens in
   `/quiz` and `/review`, using this log as material.
