# AGENTS.md

## What this workspace is

A personal self-study workspace for system design interview prep, focused on
one problem: designing a notification system (push/in-app alerts) for a
social-media-scale product (100M+ users), in the style of Facebook/Instagram/X.
There is no application code here — the deliverable is a set of short,
beginner-friendly written lessons.

## Layout

- `.plan/plan.md` — the curriculum. Source of truth for lesson order, scope,
  and the vocabulary each lesson is responsible for introducing. Don't
  restructure the module/lesson order without checking with the user first —
  it's ordered deliberately (vocabulary → distribution → delivery mechanics →
  correctness/resilience → operations).
- `lessons/NN-slug/` — one folder per lesson, named `NN-slug` matching the
  lesson number and title in the plan (e.g. `06-message-brokers-and-queues/`).
  Created on demand, not all up front. Contains:
  - `lesson.md` — the written lesson itself.
  - `qa.md` — running log of every clarifying question asked about that
    lesson (via `/ask`) and its answer. Raw material for quizzes.
  - `quiz.md` — history of every quiz question asked about that lesson (via
    `/quiz` or `/review`), the user's answer, whether it was correct, and
    the lesson's current mastery status.
  - `infographic.html` — a self-contained, dense one-screen visual poster
    summarizing the lesson (see "Writing a lesson" below for the exact
    recipe). Opens directly in a browser.
  - `infographic-<topic>.html` — optional additional infographics for a
    specific sub-topic within the lesson that deserves its own visual
    (e.g. a mechanism complex enough that the main infographic can't do it
    justice). Not created by default — only when the lesson content calls
    for it.
  - `lesson.html` — (experimental; exists only for L01 so far) an
    interactive HTML rendition of `lesson.md`: same prose, with animated
    diagrams and hands-on demos embedded where the text introduces each
    mechanism. `lesson.md` remains the canonical source the quiz/ask
    pipeline reads.
- `lessons/assets/course.css` — the shared design system for every HTML
  artifact in the course: color tokens (light + dark themes), typography,
  the poster grid (`body.poster-page`) and lesson-document
  (`body.doc-page`) layouts, the SVG diagram vocabulary (`.box`, `.wire`,
  `.lbl`, `.a-fill`/`.c-fill`, …), and the animation keyframes
  (`push-dot`, `poll-req`/`poll-resp`, `ring`, `blink`, `fan-pulse`).
  Every lesson HTML file links it via
  `<link rel="stylesheet" href="../assets/course.css">` and inlines only
  lesson-specific CSS. Restyling the whole course = editing this one file.
  When a new visual pattern is needed by 2+ lessons, add it here, not
  inline.
- `lessons/assets/diagrams.js` — reusable SVG diagram components as custom
  elements, loaded via `<script defer src="../assets/diagrams.js">` and
  rendered into light DOM so `course.css` styles them. Currently:
  `<nc-actors mode="push|poll|hybrid" label="…" label2="…">` (server→client
  actor lane with animated message dots). Use a component instead of
  hand-drawing a repeat of an existing archetype; promote a new archetype
  into a component once 2+ lessons need it (one-off diagrams stay inline
  SVG in the lesson file). Note: SVG sprite reuse via external
  `<use href>` does NOT work here — Chrome blocks it on `file://` pages,
  and `<symbol>`s can't vary their text labels — which is why reuse is
  done with JS components instead.
- `.claude/skills/` — the learning-loop skills (`lesson`, `ask`, `quiz`,
  `review`, `progress`) that drive study sessions. See each `SKILL.md` for
  its exact behavior.

### Canonical lesson folder names

Skills resolve a lesson number to a folder using this table. If a new lesson
is ever added to `.plan/plan.md`, add its slug here too.

| # | Slug |
|---|------|
| 1 | `01-push-vs-pull-vs-poll` |
| 2 | `02-high-level-architecture` |
| 3 | `03-channels-and-priority-tiers` |
| 4 | `04-fanout-write-vs-read` |
| 5 | `05-celebrity-problem-hot-keys` |
| 6 | `06-message-brokers-and-queues` |
| 7 | `07-sharding-and-partitioning` |
| 8 | `08-push-delivery-mechanics` |
| 9 | `09-connection-routing` |
| 10 | `10-pull-fallback` |
| 11 | `11-replay-buffers` |
| 12 | `12-idempotency-and-deduplication` |
| 13 | `13-backpressure-and-rate-limiting` |
| 14 | `14-delivery-guarantees` |
| 15 | `15-monitoring-and-observability` |
| 16 | `16-failure-recovery-and-dlqs` |
| 17 | `17-capstone-walkthrough` |
| A | `appendix-a-connections` |

Appendices (`lessons/appendix-X-slug/`) are optional deep-dives listed in the
"Appendices" section of `.plan/plan.md`. They follow the same folder layout
and writing conventions as numbered lessons (lesson.md + infographic.html,
optionally lesson.html), but sit outside the module sequence; skills address
them by letter (e.g. "appendix A").

## Learning workflow

The intended loop per lesson, designed around active recall and spaced
repetition (testing yourself beats re-reading):

1. `/lesson N` — load or write the lesson, read it.
2. `/ask <question>` — ask anything unclear, as many times as needed. Every
   Q&A is permanently logged, so nothing you were confused about is lost.
3. `/quiz N` — get drilled question-by-question (mixing fresh questions with
   your own past `/ask` questions, since those are proven weak spots) until
   every question in the round is answered correctly. Only then is the
   lesson marked mastered.
4. `/review` (periodically, e.g. weekly or before the capstone) — interleaved
   retrieval practice across all completed lessons, weighted toward items you
   previously got wrong.
5. `/progress` — check the dashboard for what's written, quizzed, mastered,
   and what to do next.

## Writing a lesson

When asked to write, continue, or expand a lesson:

1. Read the lesson's entry in `.plan/plan.md` for its scope and the "New
   terms" it must introduce.
2. Write `lessons/NN-slug/lesson.md`:
   - **Length:** 5-10 minute read (~700-1200 words).
   - **Audience:** beginner — assume no prior system design vocabulary beyond
     what earlier lessons already introduced.
   - **First-use rule:** define every technical term in plain language at the
     exact point it first appears (inline, one clause or sentence) — never
     assume the reader already knows it, never leave it for a glossary.
   - **Structure:** brief hook (why this matters at scale) → core explanation,
     ideally with a real-world analogy → how it connects to the surrounding
     architecture → short recap → 1-2 "check yourself" questions at the end.
   - Reference real systems (Kafka, APNs, FCM, Redis, DynamoDB, etc.) where it
     helps ground the concept, but keep the explanation generic enough to be
     portable to any interview, not tied to one vendor's API.
   - Avoid code/pseudocode unless it's the clearest way to explain a specific
     mechanism (e.g. a token bucket rate limiter). This is conceptual/
     architecture study, not an implementation exercise.
3. Write `lessons/NN-slug/infographic.html` — a **dense one-screen poster**,
   not a styled article. The reference implementation is
   `lessons/01-push-vs-pull-vs-poll/infographic.html`; match its structure
   and tokens so all 17 read as one series. What "poster, not article" means:

   - **One screen, no scrolling** (on a laptop viewport, ~1200×800). Achieve
     density with a CSS grid of small panels (12-column grid, ~10px gap),
     small type (12px base, 9-10px labels/captions), and tight padding —
     never by cutting concepts. Everything important in the lesson should be
     on screen simultaneously; the whole point is refreshing the lesson in
     one glance.
   - **Diagram-first, every panel.** Each panel's payload is a *drawing* —
     an inline SVG diagram, timeline, or animated mechanism — with text
     demoted to labels and one-line captions. If a panel is mostly prose,
     redesign it as a picture. Standard visual moves to reach for:
     actor diagrams (server/client boxes with animated message dots on
     wires), timelines with event markers and shaded waiting-windows,
     trade-off seesaws/spectrums, fan-out trees, state machines, filling/
     draining buckets, before/after comparisons. Draw with inline SVG
     (viewBox-scaled, colored via the CSS custom properties, animated with
     small CSS keyframes on transforms/opacity); no external images.
   - **Every panel is a mechanism — no glossary, no "check yourself", no
     prose recap.** The poster *is* the recap; screen real estate is the
     scarcest resource, so 100% of it goes to diagrams of the lesson's
     actual mechanisms. The panel set: header strip (lesson badge + title +
     one-line hook) + one diagram panel per core concept. New terms are
     taught where they appear, as labels/captions inside the relevant
     diagram — never in a term-list panel. Check-yourself questions live in
     `lesson.md` (and the quiz pipeline) only.
   - **Semantic color, not decoration:** the accent pair amber (`--amber`) /
     cyan (`--cyan`) is used to encode a real dichotomy in the lesson's
     content (in L01: push vs. pull; in later lessons pick the lesson's own
     opposition — e.g. producer vs. consumer, write path vs. read path,
     success vs. failure). All colors, fonts, and themes come from
     `lessons/assets/course.css` — link it and use its custom properties;
     never hardcode hex values or re-declare the token block inline.
   - **Motion with meaning:** small looping CSS animations that *demonstrate
     the mechanism* (a push dot streaming continuously vs. a poll dot
     departing on a schedule; a bucket refilling; a retry backing off) —
     not decorative transitions. Always guard with
     `@media (prefers-reduced-motion: reduce)` and make sure the static
     frame still reads correctly.
   - **Content, not template:** reuse the shared stylesheet's grid, panel,
     and diagram classes, but design the panels for *this* lesson's actual
     mechanisms — don't clone L01's panel layout with new words.
   - **Reuse before writing new markup or CSS:** start from
     `<link rel="stylesheet" href="../assets/course.css">` +
     `<script defer src="../assets/diagrams.js">` +
     `<body class="poster-page">`; the grid, panels, chips, glossary,
     check-yourself, SVG classes, and animations are already there, and
     recurring diagram archetypes exist as custom elements (e.g.
     `<nc-actors mode="push">`). Inline only CSS/SVG unique to this
     lesson's diagrams; promote anything reused by 2+ lessons into the
     shared assets.
   - **SVG text sizing — don't eyeball it.** `font-size="…"` presentation
     attributes are silently overridden by course.css classes (`.lbl` is
     9px; CSS always beats presentation attributes), so set sizes with a
     class or `style="font-size:…"`. Size each viewBox ≈ 1 unit : 1
     rendered px so font sizes mean what they say (span4 panel ≈ 360 units
     wide, span5 ≈ 460, span7 ≈ 660; doc-page `.demo` ≈ 690), and budget
     monospace text width at ~0.6 × font-size per character when placing
     labels so text never overlaps or escapes its box.
   - **Verify by rendering, never by reading the markup:** before
     delivering any HTML artifact, screenshot it headless
     (`"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
     --headless --screenshot=out.png --window-size=1280,880 file://…`) and
     actually look at the image for overlapping/clipped text.
   - No network requests: the only external references allowed are the
     relative links into `lessons/assets/`; inline everything else. Opens
     directly from the file in a browser. Mobile: panels stack to one
     column under ~860px (scrolling is fine there).
   - If one sub-topic is complex enough to deserve its own focused visual
     (a multi-step protocol, a state machine), add
     `infographic-<topic>.html` alongside rather than overloading the main
     poster past one screen.
4. After writing a lesson, check its box in the Progress Tracker at the bottom
   of `.plan/plan.md`.

## Tone

Plain, direct, beginner-friendly explanations. No filler, no marketing
language, no unexplained acronyms.
