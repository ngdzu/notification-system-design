---
name: lesson
description: Load or write a specific lesson from the notification-system study plan (.plan/plan.md) and present it for reading. Use at the start of studying a new lesson, e.g. "/lesson 6". Also accepts "/lesson next" to auto-advance to the first unwritten lesson.
---

# lesson

Loads (or writes, if it doesn't exist yet) a single lesson so the user can
read it, then hands off into the ask/quiz loop.

## Steps

1. Resolve the argument to a lesson number using the canonical folder table
   in `AGENTS.md`.
   - If the argument is `next`, pick the first lesson in `.plan/plan.md`'s
     Progress Tracker that is unchecked and has no folder yet in `lessons/`.
   - If no argument is given, ask which lesson number.
2. Read that lesson's entry in `.plan/plan.md` for its scope and "New terms".
3. If `lessons/NN-slug/lesson.md` does not exist: write it following the
   "Writing a lesson" conventions in `AGENTS.md` (5-10 min read, define every
   term on first use, hook → explanation with analogy → how it fits the
   architecture → recap → 1-2 check-yourself questions), then also write
   `lessons/NN-slug/infographic.html` per the same section: a dense
   one-screen poster (grid of small panels, small type, no scrolling) where
   every panel is an SVG diagram/animation of one of this lesson's actual
   mechanisms — not a styled article, and not a reskin of another lesson's
   poster. Follow the "Writing a lesson" recipe in `AGENTS.md` exactly;
   `lessons/01-push-vs-pull-vs-poll/infographic.html` is the reference.
4. If `lesson.md` already exists: just read and present it. Do not silently
   regenerate or rewrite an existing lesson or its infographic — if the user
   wants either revised, confirm what should change first. If `lesson.md`
   exists but `infographic.html` is missing (e.g. an older lesson written
   before infographics existed), offer to generate it now.
5. After presenting the lesson, mention the infographic is available at
   `lessons/NN-slug/infographic.html` (and any `infographic-<topic>.html`
   files), and check whether `lessons/NN-slug/qa.md` or
   `lessons/NN-slug/quiz.md` already exist for this lesson, mentioning their
   state briefly (e.g. "you've asked 3 questions about this before" or "not
   quizzed yet").
6. End with a one-line nudge: "Ask anything with `/ask`, or run `/quiz N`
   when you're ready to test yourself."

Do not start quizzing automatically — wait for the user to ask questions or
invoke `/quiz` themselves. This skill's job is only to get the material in
front of them.
