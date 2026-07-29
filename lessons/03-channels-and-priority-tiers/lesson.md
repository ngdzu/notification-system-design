# Lesson 3 — Notification Channels & Priority Tiers

## Why this matters

In Lesson 2 you saw the full pipeline end to end: producer, ingestion, fan-out,
queue, delivery worker, channel. The last box — **channel** — was left
deliberately vague: "push, email, SMS, in-app." But picking the right channel
is not a minor detail. Send a password-reset code only as an in-app badge and
the locked-out user never sees it. Blast every marketing update as an SMS and
you burn money and goodwill. Worse, at scale a surge of low-importance messages
can clog the pipeline and delay the ones that truly matter.

This lesson covers two ideas that solve these problems: **channels** (the
roads a notification can travel) and **priority tiers** (a system for making
sure urgent traffic doesn't get stuck behind a parade of bulk messages).

---

## The four main delivery channels

A **channel** is a specific path through which a notification reaches a user's
eyes. Most large-scale systems support four:

### 1. Push notification

A short message sent by a remote server to a user's phone or browser, even
when the app is closed. Apple (APNs) and Google (FCM) each run a gateway
service that your delivery worker calls to reach the device. Push is fast
(sub-second delivery is common) and highly visible — it lights up the lock
screen — but the user can revoke permission at any time, so you can never
treat it as guaranteed.

### 2. In-app / in-feed

A notification that appears inside the application itself — the bell icon with
a red badge, or a card in an activity feed. In-app notifications are reliable
in the sense that they will be there when the user opens the app, but they are
invisible until then. They cost almost nothing to deliver (it is just a write
to a database the user will read later), so they are the workhorse channel for
high-volume, lower-urgency updates like "Alex liked your post."

### 3. Email

Familiar, universal, and the only channel that works even if the user has
never installed your app. Email is good for longer content (receipts, weekly
digests, account alerts) but slow — delivery can take seconds to minutes, and
open rates for notification-style emails hover around 20%. It also has
deliverability risks: send too much and inbox providers start routing you to
spam.

### 4. SMS (text message)

The nuclear option: it reaches almost any phone, even without a data
connection, and has near-100% open rates. The trade-off is cost — each
message costs real money (fractions of a cent to several cents depending on
the country) — and regulatory complexity (opt-in laws, rate limits, country-
specific rules). Most systems reserve SMS for security-critical messages like
two-factor authentication codes.

### Choosing channels

In practice a single event often fans out to more than one channel. A password
change might go to push *and* email *and* SMS, because the stakes are high
enough that you want every path covered. A "someone you follow posted" update
might go only to push and in-app, because email and SMS would be overkill.
The decision of which channels to use for a given notification type is
usually stored in a configuration table — sometimes called a **channel
routing table** — that maps each notification type to its allowed channels
and respects each user's preferences (e.g., "I turned off push for marketing
messages").

---

## Not all notifications are created equal

Imagine a social platform with 100 million users. At 9:00 AM the marketing
team triggers a campaign: "Check out our new feature!" That is 100 million
messages entering the pipeline. At 9:01 AM a user changes their password. That
single "your password was changed" alert is now standing in line behind 100
million bulk messages. The user waits minutes for a confirmation that should
have arrived in seconds.

This is the problem priority tiers solve.

### Transactional vs. bulk notifications

A **transactional notification** is one that a specific user action directly
triggers and that the user expects immediately. Examples: password-change
confirmations, two-factor codes, order receipts, payment failures. These are
"must arrive" messages — if they are late or lost, the user experience breaks.

A **bulk notification** (sometimes called a **marketing notification**) is one
sent to a large audience on a schedule or campaign basis. Examples: "We
launched a new feature," "Your weekly digest is ready," "People you follow have
been posting." These are "best-effort" — nice to have, but a few-minute delay
or even a small drop rate is acceptable.

The line between the two is not always crisp (a "someone liked your photo"
update sits somewhere in the middle), but the mental model is simple: *would
the user notice and care if this message arrived five minutes late?* If yes,
it is transactional. If no, it is bulk.

### Priority queues: separate lanes for separate urgency

A **priority queue** is a queue where messages with higher priority are
processed before messages with lower priority, regardless of arrival order.
Think of it like a hospital emergency room: a heart attack patient is seen
before someone with a sprained ankle, even if the ankle patient arrived first.

In a notification system this is typically implemented by running **multiple
physical queues** — one per priority tier — rather than a single queue with
fancy sorting. A common setup uses three tiers:

| Tier | Label | Examples | Delivery target |
|------|-------|----------|-----------------|
| P0 | Critical | 2FA codes, security alerts, payment failures | Under 10 seconds |
| P1 | Standard | Likes, comments, follows, direct messages | Under 1 minute |
| P2 | Bulk | Marketing campaigns, digests, recommendations | Best-effort, minutes OK |

Delivery workers pull from the P0 queue first. Only when P0 is empty do they
check P1, and only when P1 is empty do they check P2. Some systems go further
and assign dedicated worker pools to each tier so that bulk traffic can never
starve the critical path even under heavy load.

### Where priority is assigned

Priority is usually stamped onto the message early — at the ingestion service
— based on the notification type. The ingestion service looks up the type
("password_changed" → P0, "new_follower" → P1, "weekly_digest" → P2) and
tags the message before it enters the queue. This means the fan-out and
delivery stages do not need to understand business logic about urgency; they
just respect the priority tag they receive.

---

## How this connects to the architecture

Look back at the Lesson 2 pipeline:

**Producer → Ingestion Service → Fan-Out Service → Queue → Delivery Worker → Channel**

Today's lesson zoomed into two spots:

1. **Channel** (the last box): you now know the four main roads — push,
   in-app, email, SMS — and that a routing table decides which roads each
   notification type takes.
2. **Queue** (the middle): you now know that the single "queue" box is really
   multiple priority queues, and that the ingestion service is where the
   priority tag is assigned.

In Lesson 4 we will zoom into the fan-out service and tackle the core
distribution problem: one event, potentially millions of recipients.

---

## Recap

- **Channels** are the delivery paths: push, in-app, email, SMS. Each has
  trade-offs in speed, cost, reliability, and visibility.
- **Transactional notifications** are user-triggered and time-sensitive.
  **Bulk/marketing notifications** are audience-wide and delay-tolerant.
- **Priority queues** (usually implemented as separate physical queues per
  tier) ensure urgent messages are processed first, even during traffic surges.
- Priority is assigned early, at ingestion, so downstream components stay
  simple.

---

## Check yourself

1. A user requests a password reset. Which channel(s) would you send the reset
   code through, and why? Which channels would be a poor choice?

2. Your system has a single shared queue for all notification types. A
   marketing campaign sends 50 million messages at once. What problem does this
   create for transactional notifications like 2FA codes, and how would you
   fix it?
