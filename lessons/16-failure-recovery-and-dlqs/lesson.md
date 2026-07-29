# Lesson 16 — Failure Recovery & Dead Letter Queues (DLQs)

## Why this matters

In a notification system serving 100M+ users, failures aren't edge cases —
they're a constant. Third-party push services go down, databases hit
timeouts, network blips happen dozens of times per hour. If every failure
crashes a worker or blocks a queue, millions of notifications stall. This
lesson covers the machinery that keeps your pipeline moving when individual
messages fail: retry with backoff, recognizing poison messages, and parking
unfixable failures in a dead letter queue instead of losing them.

## What goes wrong, and how often

When a consumer pulls a message from a queue and tries to process it — say,
calling APNs to deliver an iOS push — three things can happen:

1. **Success.** The message is acknowledged and removed from the queue.
2. **Transient failure.** The downstream service returned a 503 or the
   connection timed out. If you tried again in a few seconds, it would
   probably work.
3. **Permanent failure.** The message itself is broken — maybe the payload is
   malformed, a required field is missing, or the target user was deleted.
   Retrying a thousand times won't fix it.

The entire challenge is distinguishing case 2 from case 3, handling each
correctly, and never letting either one block the flow of healthy messages.

## Retry with backoff

**Retry with backoff** means re-attempting a failed operation after
progressively longer wait periods instead of retrying immediately in a tight
loop. A common pattern is exponential backoff: wait 1 second, then 2, then
4, then 8, and so on up to some maximum (a "cap").

Why not just retry immediately? Two reasons:

- **Thundering herd.** If a downstream service hiccups and 50,000 workers
  all retry at the exact same instant, you've turned a brief hiccup into a
  sustained outage. Spreading retries over time gives the service room to
  recover.
- **Wasted resources.** Tight retry loops burn CPU and network on attempts
  that are almost certainly going to fail for the same reason the first one
  did.

Most implementations add **jitter** — a small random offset — to each wait
period. Without jitter, workers that all started at the same time will also
all retry at the same time, recreating the thundering-herd problem one delay
cycle later. With jitter, retries scatter across a window instead of
clustering.

A typical configuration for a notification worker might look like:

- Max retries: 5
- Base delay: 1 second
- Multiplier: 2× (exponential)
- Jitter: ±0–500 ms random
- Max delay cap: 30 seconds

So the retry sequence would be roughly 1 s → 2 s → 4 s → 8 s → 16 s (each
± jitter), after which the message is declared unprocessable by this worker.

## Poison messages

A **poison message** is a message that will never succeed no matter how many
times you retry it. Examples:

- A notification whose JSON payload is truncated and can't be deserialized.
- A message referencing a user ID that doesn't exist in any database.
- A template ID that was deleted but a stale producer still emitted it.

Poison messages are dangerous because of what happens when you don't handle
them. In a simple queue consumer, the flow is: pull message → try to process
→ fail → message goes back to the front of the queue → pull the same message
again → fail again → forever. The poison message blocks every other message
behind it, and the consumer is stuck in an infinite failure loop. This is
sometimes called "queue poisoning" or "head-of-line blocking."

Even with retries and backoff, if the only end state for a failed message is
"put it back and try again," you've just slowed the infinite loop down — you
haven't solved it.

## Dead letter queues (DLQs)

A **dead letter queue (DLQ)** is a separate queue where messages go after
they've exhausted all retries. Instead of being silently dropped or blocking
the pipeline forever, they get parked in a place where engineers can inspect
them later.

The flow works like this:

1. Consumer pulls a message from the main queue.
2. Processing fails.
3. The message is retried (with backoff) up to the configured maximum.
4. After the final retry fails, the message is published to the DLQ instead
   of going back to the main queue.
5. The consumer acknowledges the original message (removing it from the main
   queue) and moves on to the next one.

The DLQ is just another queue, but it's not actively consumed by normal
workers. Instead, it serves three purposes:

- **Inspection.** Engineers can look at what's in the DLQ to diagnose why
  messages failed — is it a code bug? A schema change that broke
  deserialization? A downstream outage that lasted longer than the retry
  window?
- **Replay.** Once the root cause is fixed, messages in the DLQ can be
  re-published to the main queue for another attempt. This is how you
  recover notifications that would otherwise be lost during an outage.
- **Alerting.** A DLQ that's growing fast is a strong signal that something
  is wrong. Monitoring DLQ depth is one of the most useful operational
  metrics you can have (Lesson 15 covered monitoring broadly; DLQ depth is
  a specific metric worth watching).

## How this fits in the architecture

Think back to the notification pipeline from earlier lessons: a producer
emits an event, a message broker (Lesson 6) queues it, and consumer workers
pull and deliver it. Retry with backoff and DLQs sit entirely on the
consumer side of the broker.

Most message brokers — Kafka, RabbitMQ, SQS — have built-in support for
DLQs or the primitives to build them. In Kafka, a consumer can produce
failed messages to a separate "DLQ topic." In SQS, you configure a redrive
policy that automatically moves messages to a designated DLQ after N failed
receives. RabbitMQ supports dead-letter exchanges natively.

The retry-and-DLQ pattern also interacts with guarantees from Lesson 14.
In an at-least-once delivery system, a message that lands in the DLQ hasn't
been delivered — but it hasn't been lost either. It's in a known state,
waiting for human or automated intervention. That's a much better outcome
than silent data loss, which is what happens in systems that simply drop
messages after a few failures.

## Analogy: the post office

Imagine a postal carrier trying to deliver a package. Nobody's home, so they
leave a notice and try again the next day (retry). They try a second day
(backoff — they're not coming back every 10 minutes). After three failed
attempts, they don't throw the package away — they bring it back to the post
office and put it on a "return to sender" shelf (the DLQ). It sits there
until someone deals with it: the sender picks it up, provides a corrected
address, or it's eventually discarded after a defined holding period. At no
point does the carrier stop delivering other packages on the route because
of one problem delivery.

## Recap

- **Retry with backoff** re-attempts failed operations with progressively
  longer waits (plus jitter) to handle transient failures without
  overwhelming downstream services.
- A **poison message** is one that will never succeed — it must be detected
  and removed from the normal flow.
- A **dead letter queue (DLQ)** parks messages that exhausted all retries,
  preserving them for inspection, replay, and alerting instead of dropping
  or blocking.
- DLQs turn "message failed permanently" from a silent loss into a visible,
  recoverable state.
- Most brokers (Kafka, SQS, RabbitMQ) have native DLQ support.

## Check yourself

1. Why is adding jitter to exponential backoff important, even though plain
   exponential backoff already spaces out retries?
2. A notification system drops messages after 5 failed retries instead of
   routing them to a DLQ. What operational problems does this create compared
   to using a DLQ?
