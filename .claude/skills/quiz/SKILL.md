---
name: quiz

description: Drill the user on a single lesson with one-at-a-time active-recall questions, drawing on both the lesson content and their own previously logged /ask questions, until every question in the round is answered correctly. Use once a lesson has been read, e.g. "/quiz 6".
---

# quiz

This is the core mastery-check skill. The goal is active recall (the user
produces the answer from memory before seeing any feedback), not a re-read.
A round is not "done" just because you asked N questions — it's done when
every question in it has been answered correctly at least once.

## 1. Build the question bank

Read, for the target lesson:
- `lessons/NN-slug/lesson.md` (the lesson content and its check-yourself
  questions)
- The lesson's "New terms" list in `.plan/plan.md`
- `lessons/NN-slug/qa.md` if it exists — every question logged there is a
  proven weak spot and MUST be represented in the bank, rephrased (not
  copy-pasted verbatim, so the user can't pattern-match the old answer)
- `lessons/NN-slug/quiz.md` if it exists — skip questions already
  answered correctly 2+ times in a row unless the bank would otherwise be too
  small; prioritize anything previously marked incorrect or partial

Build a bank of roughly 6-10 questions mixing these types:
- **Recall**: define a term in your own words
- **Mechanism**: explain how something works or why it's needed
- **Application/scenario**: apply the concept to a new hypothetical
  ("if X happened, what would you expect the system to do and why?")
- **Compare/contrast**: distinguish two related concepts from the lesson
  (or from earlier lessons, if the current one builds on them)

## 2. Run the loop

Ask **one question at a time**. Do not reveal the answer, a hint, or whether
it's right/wrong until the user responds. Wait for their answer.

After each answer:
- Grade it as correct / partially correct / incorrect against the lesson's
  actual content.
- Give direct feedback: confirm what's right, correct what's wrong, and fill
  any gap — briefly, don't re-teach the whole lesson.
- Append the result to `lessons/NN-slug/quiz.md` (create the file if
  needed):

  ```
  ## Q: <question> (<YYYY-MM-DD>)
  User answer: <answer>
  Result: correct | partial | incorrect
  Notes: <brief correction or confirmation>
  ```

- If partial or incorrect, put that question back into the round's queue to
  ask again later (reworded), rather than moving on for good. Don't
  immediately re-ask it next — let 1-2 other questions come between, so it's
  a real recall attempt, not short-term memory.

## 3. End of round

Continue until every question in the bank has been answered correctly at
least once (retries included). Then:
- Give a summary: first-try score (e.g. "7/9 correct on first attempt"),
  and which specific concepts needed a second pass.
- Update the mastery line at the top of `lessons/NN-slug/quiz.md`:
  `Status: mastered (<date>, N questions needed a retry)`.
- Check off that lesson's box in the Progress Tracker in `.plan/plan.md`.
- Suggest next step: `/lesson next` to continue, or `/review` if several
  lessons are now mastered and it's worth checking retention across them.

Never mark a lesson mastered if any question in the round was never answered
correctly.
