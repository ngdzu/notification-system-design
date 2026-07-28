# Study Plan: Notification Systems at Scale (Hundreds of Millions of Users)

## Why this is hard

Sending one notification is trivial. Sending the *right* notification to hundreds
of millions of users — instantly, without losing messages, and without your
servers falling over when a celebrity posts — is one of the classic "hard mode"
system design interview problems (think Facebook, Instagram, X/Twitter). This
plan builds your mental model piece by piece, in the order you'd actually need
it to reason through the problem in an interview.

## How to use this plan

- This file (`.plan/plan.md`) is the **curriculum** — what to learn, in what
  order, and which new vocabulary each lesson introduces.
- Actual lesson write-ups live in `lessons/NN-slug.md`, one file per lesson,
  written on request following the conventions in `AGENTS.md`.
- Each lesson is a **5–10 minute read**, beginner-friendly, and defines every
  new term the first time it's used — no unexplained jargon.
- Work through the modules in order. Later lessons assume the vocabulary from
  earlier ones (e.g., you need "message broker" from Lesson 6 before "replay
  buffer" makes sense in Lesson 11).
- Check off lessons in the **Progress Tracker** at the bottom as you complete them.

---

## Module 1: Foundations & Vocabulary

### Lesson 1 — Why Notification Systems Are Hard at Scale (Push vs. Pull vs. Poll)
**New terms:** push, pull, polling, fan-out, throughput, latency
What a "notification" actually is (a small, timely message telling a user
something happened), and the three basic ways to get it to them: **push**
(server proactively sends data to the client the moment it's ready), **pull**
(client asks "anything new?" on its own schedule — also called **polling**),
and hybrids of the two. Explains why push is preferred for user experience but
pull is the fallback that keeps the system honest. Sets up the core tension of
the whole course: speed (**latency** — how long delivery takes) vs. system
load (**throughput** — how many messages you can process per second).

### Lesson 2 — High-Level Architecture: The Map of the System
**New terms:** producer, ingestion service, fan-out service, delivery worker, channel
A 30,000-foot diagram-in-words of the full pipeline: something happens (a
**producer** emits an event, e.g. "user A liked your post") → an **ingestion
service** receives and validates it → a **fan-out service** figures out who
needs to be notified → the message goes through a queue → **delivery workers**
push it out over the right **channel** (push notification, in-app, email,
SMS). Every later lesson zooms into one box in this diagram.

### Lesson 3 — Notification Channels & Priority Tiers
**New terms:** channel, transactional notification, bulk/marketing notification, priority queue
Not all notifications are equal. A "your password was changed" alert
(**transactional**, must arrive) is different from "someone you follow posted"
(**bulk/marketing**, best-effort). Covers the main delivery **channels** (push,
in-app/in-feed, email, SMS) and why systems split traffic into **priority
tiers** so urgent messages don't sit behind a flood of low-priority ones.

---

## Module 2: Getting the Message to the Crowd (Fan-Out & Brokers)

### Lesson 4 — The Fan-Out Problem: Write Path vs. Read Path
**New terms:** fan-out-on-write, fan-out-on-read, fan-out ratio
The core distribution problem: one event, many recipients. **Fan-out-on-write**
pre-computes and delivers to every follower's inbox the moment the event
happens (fast reads, expensive writes). **Fan-out-on-read** waits until each
user checks their notifications and assembles the result on demand (cheap
writes, slower reads). The **fan-out ratio** (followers per event) is what
decides which strategy — or mix — makes sense.

### Lesson 5 — The Celebrity Problem: Hot Keys & Hybrid Fan-Out
**New terms:** hot key, hybrid fan-out, thundering herd
What happens when one account has 100 million followers and posts once? Why
pure fan-out-on-write would create a **hot key** (a single piece of data
getting hammered with disproportionate traffic) and a **thundering herd** (a
sudden burst of near-simultaneous requests overwhelming a resource). Explains
**hybrid fan-out**: push proactively to normal accounts, but fall back to
pull/read-time computation for mega-accounts.

### Lesson 6 — Message Brokers & Queues 101 (The Post Office of System Design)
**New terms:** message broker, queue, topic, producer/consumer, consumer group, offset
A **message broker** (e.g. Kafka, RabbitMQ, SQS) sits between producers and
consumers so they don't have to talk to each other directly or run at the same
speed — like a post office holding mail until the recipient is ready. Defines
**queue** vs. **topic**, the **producer/consumer** relationship, **consumer
groups** (multiple workers sharing the load of one topic), and **offset**
(a bookmark tracking how far a consumer has read).

### Lesson 7 — Sharding & Partitioning for Notification Data
**New terms:** shard, partition, partition key, consistent hashing
Why one database or one queue can't hold traffic for hundreds of millions of
users, and how you split data into **shards/partitions** — smaller, independent
slices, usually chosen by a **partition key** (e.g. user ID) so a given user's
data always lands in the same place. Introduces **consistent hashing** as the
common technique for spreading keys evenly and resizing without reshuffling
everything.

---

## Module 3: Getting Bits to a Phone (Delivery Mechanics)

### Lesson 8 — Push Delivery Mechanics: APNs, FCM, and Device Tokens
**New terms:** push notification service, device token, payload, silent/background push
You don't push directly to a phone — you go through the OS vendor's **push
notification service** (Apple's APNs, Google's FCM). Explains the **device
token** (a unique address for a specific app install on a specific device),
the **payload** (the small JSON body of the notification, with strict size
limits), and **silent/background push** (a wake-up signal with no visible
alert, used to trigger a data sync).

### Lesson 9 — Connection Routing: Who's Connected to Which Server?
**New terms:** WebSocket, long polling, Server-Sent Events (SSE), gateway server, presence service, sticky session
For in-app real-time delivery, covers the three common persistent-connection
techniques (**WebSocket**, **long polling**, **Server-Sent Events**) and the
routing problem they create: with millions of open connections spread across
thousands of **gateway servers**, how does the system know *which* server a
given user is connected to right now? Introduces the **presence service**
(a lookup registry of user → server) and **sticky sessions** (keeping a user
pinned to one server for the life of a connection).

### Lesson 10 — Pull Fallback: The Backup Plan When Push Fails
**New terms:** sync-on-reconnect, badge count, cursor-based pagination
Push is never 100% reliable — devices go offline, tokens expire, connections
drop. Covers the **pull fallback**: when a client reconnects or opens the app,
it calls an API to catch up (**sync-on-reconnect**), computes the unread
**badge count**, and pages through history using a **cursor** (an opaque
pointer into a sorted list, safer than page numbers when data keeps changing —
**cursor-based pagination**).

---

## Module 4: Making It Correct & Resilient

### Lesson 11 — Replay Buffers & Missed-Message Recovery
**New terms:** replay buffer, retention window, gap detection
A **replay buffer** is a short-term store of recently sent messages (with a
**retention window**, e.g. last 24 hours) that a reconnecting client can
replay from its last known position, instead of the server re-deriving
everything from scratch. Covers **gap detection** — how a client realizes it
missed messages at all (e.g. noticing a jump in sequence numbers).

### Lesson 12 — Idempotency & Deduplication: Avoiding Double Notifications
**New terms:** idempotency, idempotency key, deduplication store, retry storm
Networks and workers retry failed operations — which means the same
notification can easily get sent twice. **Idempotency** means doing an
operation multiple times has the same effect as doing it once. Covers
**idempotency keys** (a unique ID attached to each logical event so retries
can be recognized and skipped), a **deduplication store** (a fast lookup of
"have I seen this key before?"), and the **retry storm** failure mode this
protects against.

### Lesson 13 — Backpressure & Rate Limiting: Protecting the System from Itself
**New terms:** backpressure, rate limiting, token bucket, leaky bucket, load shedding, circuit breaker
What happens when producers create work faster than consumers can process it.
**Backpressure** is the mechanism of signaling "slow down" upstream instead of
silently piling up an unbounded queue. **Rate limiting** caps how fast a
client or service can send (with the classic **token bucket** and **leaky
bucket** algorithms explained plainly). **Load shedding** is deliberately
dropping low-priority work under extreme load, and a **circuit breaker** stops
calling a failing downstream service for a cooldown period instead of
hammering it.

### Lesson 14 — Delivery Guarantees & Trade-offs
**New terms:** at-most-once, at-least-once, exactly-once, acknowledgment (ack)
Defines the three delivery contracts a queue/broker can offer: **at-most-once**
(might lose messages, never duplicates), **at-least-once** (never loses
messages, might duplicate — the common real-world default), and
**exactly-once** (the ideal, usually achieved in practice by combining
at-least-once delivery with the idempotency techniques from Lesson 12, not by
magic). Covers **acknowledgment (ack)** — how a consumer tells the broker
"I successfully processed this" so it isn't redelivered.

---

## Module 5: Running It in Production

### Lesson 15 — Monitoring, Metrics & Observability
**New terms:** observability, SLI/SLO, golden signals, p50/p95/p99 latency, distributed tracing
**Observability** is being able to answer "what is my system doing right now
and why" from the outside. Covers **SLIs/SLOs** (measurable indicators and the
target you promise for them, e.g. "99.9% of pushes delivered within 5s"), the
**golden signals** (latency, traffic, errors, saturation), **percentile
latency** (p50/p95/p99 — why averages hide the worst user experiences), and
**distributed tracing** (following one request across many services).

### Lesson 16 — Failure Recovery & Dead Letter Queues (DLQs)
**New terms:** retry with backoff, poison message, dead letter queue (DLQ)
What to do when a message keeps failing to process. **Retry with backoff**
(waiting progressively longer between attempts instead of hammering
immediately) handles transient failures. A **poison message** is one that will
never succeed no matter how many retries (e.g. malformed data), and a **dead
letter queue (DLQ)** is where these get parked for inspection instead of
blocking the whole pipeline or being silently dropped.

### Lesson 17 — Capstone: Full Reference Architecture Walkthrough
**New terms:** (none — synthesis lesson)
Ties every previous lesson into one end-to-end walkthrough: an event is
created → ingested → fanned out (hybrid, hot-key aware) → queued in a
partitioned broker → delivered via push with connection routing, or picked up
via pull fallback → protected by idempotency, backpressure, and replay buffers
→ observed via monitoring → recovered via DLQ on failure. Ends with a mock
interview prompt so you can practice explaining the whole system out loud in
under 15 minutes.

---

## Appendices

Optional deep-dives that support the main curriculum but aren't part of the
lesson sequence. Read them when the referenced lessons make you curious about
what's underneath.

### Appendix A — Anatomy of a Connection
**New terms:** packet-switched, socket, 4-tuple, file descriptor, thread-per-connection, C10K, event loop (epoll), FIN, RST, half-open connection, keepalive/heartbeat, NAT timeout, TLS session, QUIC
Zooms into the phrase "the server holds a connection open to every client"
(Lesson 1). A connection is **matching state in RAM at both ends** — a socket
with buffers and sequence numbers — not a reserved wire; one idle connection
costs ~10–50 KB, so a million ≈ tens of GB. Covers why thread-per-connection
collapses (**C10K**) and event loops (**epoll**) win, how protocols stack
connections on connections (UDP → TCP → TLS → HTTP/WebSocket/SSH, QUIC), and
the three ways a connection dies: **FIN** (polite — sent even on Ctrl+C),
**RST** (slam), and **silence** (the **half-open** ghost detected only by
heartbeats). Supports Lessons 1, 8, 9, and 10.

---

## Progress Tracker

- [x] Lesson 1 — Push vs. Pull vs. Poll
- [x] Lesson 2 — High-Level Architecture
- [ ] Lesson 3 — Channels & Priority Tiers
- [ ] Lesson 4 — Fan-Out: Write Path vs. Read Path
- [ ] Lesson 5 — The Celebrity Problem
- [ ] Lesson 6 — Message Brokers & Queues 101
- [ ] Lesson 7 — Sharding & Partitioning
- [ ] Lesson 8 — Push Delivery Mechanics
- [ ] Lesson 9 — Connection Routing
- [ ] Lesson 10 — Pull Fallback
- [ ] Lesson 11 — Replay Buffers
- [ ] Lesson 12 — Idempotency & Deduplication
- [ ] Lesson 13 — Backpressure & Rate Limiting
- [ ] Lesson 14 — Delivery Guarantees & Trade-offs
- [ ] Lesson 15 — Monitoring & Observability
- [ ] Lesson 16 — Failure Recovery & DLQs
- [ ] Lesson 17 — Capstone Walkthrough
- [x] Appendix A — Anatomy of a Connection
