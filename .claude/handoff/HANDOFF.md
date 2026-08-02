# Handoff — 2026-08-01 00:00

## Where things stand

Studying the notification-system curriculum. Lessons 1–2 and Appendix A are marked complete in `.plan/plan.md`; Lesson 10 (Pull Fallback) has a written `lesson.md` and an active Q&A thread but isn't checked off yet. This session was mostly `/ask` activity on Lessons 2 and 10 (pipeline architecture, where the notification store lives, push vs. pull semantics), plus two process changes to the `/ask` workflow itself.

## What happened this session

- `lessons/10-pull-fallback/qa.md` (new) — Q1–Q6: where the notification store lives, push/pull = general delivery vs. APNs-specific, which pipeline stage owns the DB write, whether the DB is shared across delivery workers, how the client reaches the DB on pull, and whether a dedicated pull API server exists.
- `lessons/02-high-level-architecture/qa.md` — added Q2–Q4: whether pipeline stages are "components" or "phases" (both), a diagram of how components interact with the database, and a corrected diagram showing Channel's last hop to the client (through APNs/FCM, WebSocket, or a mail/SMS gateway) instead of dead-ending at Channel. Q4's diagram was further corrected in place (not as a new Q) after the user caught that push-clients and the pull-client were wrongly drawn as separate nodes — now a single `Client` node with edges both ways.
- `.claude/skills/ask/SKILL.md` — two behavior changes: (1) split multi-part questions into separate, independently-answered entries instead of blending them; (2) number every `## Q<N>:` entry sequentially per lesson, so future questions can reference earlier ones by number (e.g. "follow up to Q3").
- `AGENTS.md` — documented the new `handoff` skill and `HANDOFF.md` in the Layout and Learning workflow sections.
- `.claude/skills/handoff/SKILL.md` (new) — this skill.
- Retroactively numbered pre-existing entries in `lessons/appendix-a-connections/qa.md` (now Q1–Q6) for consistency with the new numbering rule.

## Decisions / corrections to remember

- `/ask` answers should be direct — skip hedging or restating context the user already said they know; answer exactly what was asked.
- When a correction targets a *factual error* in a previous Q&A answer (not a differing follow-up question), fix it in place in that same `## Q<N>:` entry (with a short "corrected on \<date\>" note) rather than appending a new numbered entry that leaves the wrong version standing.

## Next action

Send the rest of the lessons to Kindle.
