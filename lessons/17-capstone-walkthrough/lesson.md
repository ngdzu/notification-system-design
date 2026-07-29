# Lesson 17 — Capstone: Full Reference Architecture Walkthrough

## One Notification, Start to Finish

You have spent sixteen lessons building a mental model of every piece in a notification system. Now it is time to see those pieces working together. We will follow a single notification — "Alice liked your photo" — from the moment Alice taps the heart button to the instant Bob's phone buzzes, and trace every system it passes through along the way.

This is the lesson you rehearse before your interview.

---

## The Cast of Components

Before the walkthrough, here is a quick map of every component in the order a notification touches them. Each one links back to the lesson where it was introduced.

1. **Producer** — the service that detects "something happened" (Lesson 2)
2. **Ingestion service** — validates, deduplicates, and classifies the event (Lessons 2, 3, 12)
3. **Fan-out service** — decides who needs to be notified and how (Lessons 4, 5)
4. **Message broker** — buffers and distributes work to delivery workers (Lessons 6, 7)
5. **Delivery workers** — push notifications out over the right channel (Lessons 8, 9)
6. **Pull fallback & replay buffer** — catch-up path for offline users (Lessons 1, 10, 11)
7. **Safety systems** — idempotency, backpressure, rate limiting (Lessons 12, 13, 14)
8. **Monitoring & observability** — metrics, logs, traces watching every step (Lesson 15)
9. **Dead letter queue (DLQ)** — last resort for messages that cannot be delivered (Lesson 16)

---

## The Walkthrough

### Step 1: The Event Is Born (Producer → Ingestion)

Alice opens Instagram, sees Bob's photo, and taps the heart. The Likes service — a **producer** (Lesson 2) — emits an event:

```
{
  "event_id": "evt-9f3a...",
  "type": "like",
  "actor": "alice",
  "target_owner": "bob",
  "target": "photo-7721",
  "timestamp": 1690000000
}
```

This event arrives at the **ingestion service** (Lesson 2). The ingestion service does three things:

1. **Validates** the payload — is the schema correct? Does Bob's account exist?
2. **Deduplicates** — has `evt-9f3a...` been seen before? It checks an **idempotency key** store (Lesson 12). If Alice double-tapped and the app sent the event twice, the duplicate is dropped here.
3. **Classifies priority** — a like is a low-to-medium priority **bulk notification** (Lesson 3), not a transactional alert like a password change. It gets tagged accordingly so it enters the right **priority queue** later.

### Step 2: Fan-Out — Who Needs to Know? (Fan-Out Service)

The ingestion service forwards the validated event to the **fan-out service** (Lesson 4). For a like, the recipient list is simple: just Bob. But if Alice had *posted* a new photo and had 50,000 followers, the fan-out service would need to generate 50,000 individual delivery tasks.

The fan-out service checks: is the actor a **hot key** — an account with a disproportionately large follower count (Lesson 5)? If Alice were a celebrity with 100 million followers, pure **fan-out-on-write** would create a thundering herd of writes. The system uses **hybrid fan-out** (Lesson 5): push immediately to active, normal-follower users, but let celebrity content be assembled at read time (**fan-out-on-read**, Lesson 4) for the rest.

For our "Alice liked Bob's photo" event, the fan-out ratio is 1:1. One delivery task is created and published to the message broker.

### Step 3: Into the Broker (Message Broker & Partitioning)

The delivery task lands in a **message broker** — think Kafka or RabbitMQ (Lesson 6). The broker acts like a post office: it receives the message, files it in the right **topic** (e.g., `push-notifications`), and holds it until a worker is ready.

The topic is split into **partitions** (Lesson 7). Bob's user ID is hashed to determine which partition the message goes to. Partitioning ensures ordering per user (Bob's notifications arrive in sequence) and spreads load across many machines. A **consumer group** (Lesson 6) of delivery workers reads from these partitions, with each partition assigned to exactly one worker at a time.

The broker also records an **offset** (Lesson 6) — the position of this message in the partition log. This offset is critical later if the message needs to be replayed (Lesson 11).

### Step 4: Delivery — Push Path (Delivery Worker → Connection Routing → Device)

A **delivery worker** (Lesson 2) picks up Bob's notification from the broker. It now needs to push it to Bob's device. But Bob might have three devices — a phone, a tablet, and a laptop — each holding a persistent WebSocket or SSE connection to a different **gateway server** in a cluster of hundreds (Lesson 8).

The worker queries the **connection routing** layer (Lesson 9) — a distributed lookup (often backed by Redis or a consistent hash ring) that maps Bob's user ID to the gateway server(s) holding his active connections. The lookup returns: "Bob's phone is connected to gateway-42, his laptop is connected to gateway-117."

The worker sends the rendered notification payload to gateway-42 and gateway-117. Each gateway pushes the message down Bob's open connection. Bob's phone buzzes. His laptop shows a red badge.

For **mobile push** specifically (Lesson 8), the gateway may also relay through APNs (Apple) or FCM (Google) — external push services that can wake a sleeping app.

### Step 5: What If Bob Is Offline? (Pull Fallback & Replay Buffer)

Suppose Bob's phone has no signal. There is no active connection in the routing table. The delivery worker cannot push.

Two mechanisms cover this:

1. **Replay buffer** (Lesson 11): The notification is written to Bob's per-user replay buffer — a short-term ordered log (e.g., a Redis Stream with a 24-hour retention window). When Bob's phone reconnects, the client says "last offset I saw was 3,201." The server streams everything from 3,202 onward. No re-computation needed.

2. **Pull fallback** (Lesson 10): If Bob has been offline longer than the replay buffer's retention window, or if he opens the app and explicitly checks his notifications tab, the system falls back to a read-time query. Bob's client pulls from the notification store — a database where all notifications are persisted — filtered by timestamp.

This push-first, pull-fallback design (Lesson 1) gives the best of both worlds: low latency when the user is online, reliable catch-up when they are not.

### Step 6: Safety Nets Along the Way

Throughout this pipeline, three protective systems are active:

- **Idempotency** (Lesson 12): Every message carries a unique `event_id`. If a broker retry causes the same message to be delivered to a worker twice, the worker checks the idempotency store and skips the duplicate. Bob never sees "Alice liked your photo" twice.

- **Backpressure and rate limiting** (Lesson 13): If a sudden spike — say, a celebrity posts and triggers millions of fan-out tasks — floods the broker, backpressure mechanisms slow down producers rather than letting queues grow until the system crashes. Rate limiting caps how many notifications a single user receives per minute so Bob is not buried under 200 likes in 10 seconds.

- **Delivery guarantees** (Lesson 14): The system is designed for **at-least-once** delivery. The broker does not remove a message from the partition until the worker acknowledges (commits the offset) that delivery succeeded. If a worker crashes mid-delivery, another worker in the consumer group picks up the message. Combined with idempotency, the result is **effectively-once** delivery.

### Step 7: When Things Go Wrong (DLQ & Recovery)

What if gateway-42 is unreachable and retries are exhausted? The delivery worker has tried three times with **exponential backoff** (Lesson 16) — waiting 1 second, then 4 seconds, then 16 seconds. Still failing.

Rather than retrying forever or losing the message, the worker routes it to a **dead letter queue (DLQ)** (Lesson 16). The DLQ is a separate topic in the broker that collects failed messages for later inspection. An operations team (or automated recovery job) can examine DLQ entries, fix the underlying issue (maybe gateway-42 had a bad deploy), and replay the messages back into the main pipeline.

If the message itself is malformed — a **poison message** (Lesson 16) — the DLQ prevents it from blocking the entire partition. It is moved aside so healthy messages behind it can proceed.

### Step 8: Watching It All (Monitoring & Observability)

Every step above emits signals (Lesson 15):

- **Metrics**: ingestion rate, fan-out latency, broker consumer lag, delivery success rate, DLQ depth.
- **Logs**: structured events for each stage — "event evt-9f3a ingested," "delivered to gateway-42," "moved to DLQ after 3 retries."
- **Traces**: a distributed trace following `evt-9f3a` from ingestion through fan-out, broker, delivery, all the way to the gateway push — one trace ID stitching together every hop.

An alert fires if consumer lag exceeds 30 seconds (messages are piling up faster than workers can process them) or if the DLQ depth crosses a threshold (something is systematically failing). Dashboards show the health of the system in real time.

---

## The Full Pipeline, Summarized

```
Alice taps "like"
    │
    ▼
[ Producer ] ──event──▶ [ Ingestion Service ]
                             │  validate, deduplicate, classify priority
                             ▼
                        [ Fan-Out Service ]
                             │  check hot-key status, expand recipients
                             ▼
                        [ Message Broker ]
                             │  partition by user ID, buffer in topic
                             ▼
                        [ Delivery Worker ]
                             │  query connection routing
                             ├──▶ [ Gateway ] ──push──▶ Bob's phone ✓
                             │
                             ├── (offline?) ──▶ [ Replay Buffer ] ──▶ catch-up on reconnect
                             │
                             └── (failed?) ──▶ [ DLQ ] ──▶ inspect & replay later
```

Safety systems (idempotency, backpressure, rate limiting) protect every arrow. Monitoring watches every box.

---

## Recap

- A notification flows through a linear pipeline: produce → ingest → fan out → broker → deliver → fallback.
- Hot-key detection and hybrid fan-out prevent celebrity events from crushing the system.
- Partitioned brokers give ordering and parallelism. Consumer groups give fault tolerance.
- Push is the fast path; pull and replay buffers are the reliable fallback.
- Idempotency turns at-least-once delivery into effectively-once delivery.
- Backpressure and rate limiting prevent cascading overload.
- DLQs catch what retries cannot fix. Monitoring watches everything.
- Every component exists because of a specific failure mode. There are no optional pieces at scale.

---

## Check Yourself

1. Trace a password-reset notification (transactional, high priority) through the same pipeline. How does its path differ from the "Alice liked your photo" example? Which components behave differently because of its priority classification?

2. A celebrity with 80 million followers posts a new photo. Walk through what happens at the fan-out service. Why would pure fan-out-on-write be dangerous here, and how does hybrid fan-out change the flow through the broker and delivery workers?

---

## Mock Interview Prompt

> *"Design a notification system that can serve 100 million daily active users. Walk me through what happens when a user triggers an event — say, liking a post — all the way through to the recipient seeing the notification on their phone. Cover fan-out, delivery, failure handling, and how you would monitor the system."*

Set a timer for 15 minutes and explain the full system out loud. Use the pipeline diagram above as your outline. Hit every numbered step. If you can explain each stage, name the trade-offs, and describe what happens when something fails, you are ready.
