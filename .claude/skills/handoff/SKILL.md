---
name: handoff
description: Record the current session into a handoff doc — what was covered, key decisions, and what to do next — so a future session (or a different context window) can pick up exactly where this one left off. Use at the end of a study session, or any time before context is likely to be lost, e.g. "/handoff" or "/handoff next: start lesson 11 and quiz me on lesson 10 first".
---

# handoff

A write-only session log. Its only job is to make the *next* session (which
starts with zero memory of this one) able to read one file and know exactly
where things stand and what to do first.

## Steps

1. Figure out the "what to do next" instruction:
   - If the user passed argument text, use it close to verbatim as the
     **Next action** section — it's their explicit instruction to
     future-you, don't paraphrase it into something vaguer.
   - If no argument was passed, infer a sensible next action from the
     session (e.g. "continue answering questions about lesson N," "run
     `/quiz N`," "start `/lesson N+1`") and say so, but flag it as inferred
     rather than user-specified.
2. Reconstruct what actually happened this session by looking at what
   changed, not by summarizing from memory:
   - `git status` / `git diff` (if this is a git repo) to see which files
     were created or modified.
   - Which `lessons/NN-slug/` folders were touched (new `lesson.md`,
     `qa.md`, `quiz.md`, `infographic.html` entries).
   - For any `qa.md` that gained new `## Q<N>:` entries this session, note
     the question numbers added (e.g. "Lesson 10: added Q3–Q6") — don't
     copy the full Q&A text in, that's what the file itself is for.
   - Any `.plan/plan.md` Progress Tracker checkbox changes.
   - Any skill files (`.claude/skills/**/SKILL.md`) or `AGENTS.md` created
     or edited — these are process changes that matter as much as content.
   - Any non-obvious decision the user made or corrected mid-session (a
     preference, a correction to your approach, a scope call) — the kind of
     thing that would otherwise have to be re-explained.
3. Write (overwriting) `.claude/handoff/HANDOFF.md` (create the directory if
   needed), in this structure:

   ```markdown
   # Handoff — <YYYY-MM-DD HH:MM>

   ## Where things stand
   <1-3 sentences: what lesson/topic was the focus, what state it's in>

   ## What happened this session
   - <bullet per meaningful change — file created/edited and why, in one line>
   - <...>

   ## Decisions / corrections to remember
   - <anything the user specified about how to work, if any — omit section if none>

   ## Next action
   <the user's instruction verbatim if given, otherwise your inferred
   suggestion, clearly marked "(inferred)">
   ```

   Keep it short — a paragraph plus bullets, not a full transcript. The
   detail already lives in the actual files (`lesson.md`, `qa.md`,
   `quiz.md`); this doc is a pointer and a summary, not a duplicate.
4. If `.claude/handoff/HANDOFF.md` already exists from a previous session,
   don't just discard it: move its content to
   `.claude/handoff/archive/<old-timestamp>.md` (create the directory if
   needed) before writing the new one, so a chain of past handoffs is still
   recoverable if needed.
5. Confirm to the user in one line that `.claude/handoff/HANDOFF.md` was
   written, and where. Don't re-print the whole file in chat unless asked —
   they can read it.

## Reading a handoff back in

This skill only writes. To resume from a handoff at the start of a new
session, the user reads `.claude/handoff/HANDOFF.md` directly (or asks you
to) — just read the file and follow its "Next action" section as the
starting point for the session, cross-checking anything it claims against
the actual current state of the files it references before acting on it (a
handoff is a snapshot, not a live source of truth).
