---
name: progress
description: Show a status dashboard for the notification-system study plan — which lessons are written, asked about, quizzed, and mastered — plus a recommended next action. Use to decide what to study next, e.g. "/progress".
---

# progress

A read-only dashboard. Makes no edits.

## Steps

1. Read the Progress Tracker in `.plan/plan.md` for the full lesson list.
2. For each lesson number, check:
   - Does `lessons/NN-slug/lesson.md` exist? (Written)
   - Does `lessons/NN-slug/infographic.html` exist? (Infographic)
   - Does `lessons/NN-slug/qa.md` exist, and how many Q&A entries? (Asked)
   - Does `lessons/NN-slug/quiz.md` exist? What does its `Status:` line
     say, and how many questions in its most recent round were marked
     `incorrect`/`partial`? (Quizzed / Mastered)
3. Print a table:

   | # | Lesson | Written | Infographic | Questions Asked | Quiz Status |
   |---|--------|---------|-------------|------------------|-------------|

4. Below the table, recommend exactly one next action based on what's most
   useful right now, e.g.:
   - If a lesson is written but has no infographic (an older lesson from
     before infographics existed): flag it and offer to generate one via
     `/lesson N`.
   - If a lesson is written but never quizzed: "`/quiz N` — you read this
     but haven't tested yourself yet."
   - If a lesson was quizzed with retries needed and hasn't been revisited:
     suggest `/review` to check it stuck.
   - If the current module's lessons are all mastered: suggest `/lesson next`.
   - If 5+ lessons are mastered and no `/review` has been logged recently
     across them: suggest `/review`.

Keep the output short — a table plus one recommendation, not a full report.
