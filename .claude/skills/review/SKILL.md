---
name: review
description: Cumulative, interleaved spaced-repetition review across all completed lessons — mixes questions from multiple lessons' QA logs and quiz histories, weighted toward previously-missed items. Use periodically (weekly, or before the capstone lesson) to check retention, e.g. "/review" or "/review 1-10".
---

# review

Single-lesson quizzing (`/quiz`) checks you just learned something.
`review` checks you still remember something from days or weeks ago, and
does it by interleaving lessons rather than blocking by topic — both are
well-established as more effective for long-term retention than re-reading
or re-quizzing one lesson in isolation.

## 1. Scope

If given a range (e.g. `/review 1-10`), restrict to those lesson numbers.
Otherwise use every lesson folder that has a `quiz.md` or `qa.md` in it.

## 2. Build an interleaved question set

For each in-scope lesson, pull from `lessons/NN-slug/quiz.md` and
`lessons/NN-slug/qa.md`:
- Weight questions previously marked `incorrect` or `partial` highest.
- Weight questions never asked in a quiz round yet next.
- Give lowest weight to questions answered correctly 2+ times in a row —
  include a few anyway (don't let mastered material fully drop out), but
  don't let them dominate the set.

Pick roughly 10-15 questions total across the lessons in scope, and order
them so consecutive questions are never from the same lesson (true
interleaving — e.g. L3, L9, L1, L6, L2, L9, L4...).

## 3. Run the loop

Same mechanics as `/quiz`: one question at a time, wait for the answer before
grading, give direct feedback, and log each result back into that specific
lesson's `lessons/NN-slug/quiz.md` file (so its history keeps
compounding across both `/quiz` and `/review` sessions). Requeue missed
questions later in the same session, separated by other questions.

## 4. End of session

Give a retention report grouped by lesson:
- Lessons that held up well (all correct)
- Lessons with slippage (missed something they'd previously gotten right —
  flag these explicitly, that's the signal spaced repetition exists to catch)
- Concrete recommendation: which lesson(s) to run `/quiz N` on again before
  moving forward.
