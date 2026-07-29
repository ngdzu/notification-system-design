# Lesson 12 — Idempotency & Deduplication: Avoiding Double Notifications

## Why this matters

Your friend texts you "dinner at 7?" You get one text — great. Now imagine
your phone glitches and shows the same text three times. You might show up
with three friends, or just get annoyed. Notification systems hit this
problem constantly: networks drop, workers crash, queues retry — and every
retry is another chance to send the same notification twice. At 100M+ users,
"twice" can mean millions of duplicate pushes flooding phones in seconds.
This lesson covers the tools that prevent that.

## What is idempotency?

**Idempotency** means performing an operation multiple times produces the
same result as performing it once. Pressing an elevator button is idempotent:
the first press calls the elevator, the next ten presses change nothing. A
notification send is idempotent if the system recognizes "I already sent this
one" and skips the duplicate instead of firing it again.

Why does this matter so much? Because in distributed systems, retries are not
a bug — they're a feature. When a worker sends a push notification and
doesn't get an acknowledgment back (maybe the network hiccupped, maybe the
downstream service was slow to respond), the safe thing to do is retry. But
the original send might have actually succeeded — the acknowledgment just got
lost. Without idempotency, every retry is a potential duplicate notification
on someone's phone.

## Idempotency keys

An **idempotency key** is a unique identifier attached to each logical
notification event so retries can be recognized. Think of it like a receipt
number: the first time the system sees receipt #4829, it processes the
notification; every subsequent time it sees #4829, it says "already handled"
and skips it.

What makes a good idempotency key? It needs to be:

- **Deterministic**: the same logical event always produces the same key.
  A common pattern is to combine the event type, the target user, and the
  source entity — e.g., `like:user-42:post-7731`. If Alice likes Bob's post,
  that combination always generates the same key regardless of how many times
  the system retries it.
- **Unique per logical event**: different events must produce different keys.
  If Alice likes post 7731 and Carol also likes post 7731, those are two
  separate notifications for Bob, so they need different keys.

The key is generated early — ideally when the event first enters the system
— and travels with the message through every queue, worker, and retry along
the way. Any component that touches the notification can check: "Have I seen
this key before?"

## The deduplication store

An **idempotency key** is useless without somewhere to look it up. That
somewhere is the **deduplication store** (sometimes called a dedup store): a
fast data store that records which keys have already been processed.

The requirements for a dedup store are simple:

1. **Fast reads**: every notification must check the store before sending, so
   lookups need to be sub-millisecond. Redis and Memcached are common choices
   because they keep data in memory.
2. **Fast writes**: after processing a notification, write the key to the
   store immediately.
3. **Expiry (TTL)**: keys don't need to live forever. A notification retry
   typically happens within seconds or minutes, not days. Setting a
   time-to-live (TTL) of, say, 24 hours keeps the store from growing without
   bound. **TTL** stands for time-to-live — how long a record stays in the
   store before being automatically deleted.

The flow looks like this:

1. A notification event arrives at a worker with idempotency key `K`.
2. The worker checks the dedup store: "Is `K` present?"
3. If yes → skip; this notification was already sent.
4. If no → send the notification, then write `K` to the dedup store with a
   TTL.

There is a subtlety in step 4: what if two workers pick up the same message
at the exact same time and both check the store before either writes?
Both would see "not present" and both would send. This is called a race
condition. The fix is to use an atomic "set if not exists" operation (Redis's
`SETNX`, for example) that combines the check and the write into a single
step. Only the worker that wins the set actually sends the notification.

## Retry storms

A **retry storm** is what happens when idempotency fails — or isn't
implemented at all. Here's the scenario:

1. A downstream push service (e.g., APNs or FCM) slows down or returns
   errors.
2. Workers don't get acknowledgments, so they retry.
3. Those retries also fail (or time out), producing more retries.
4. The queue fills up with duplicate messages — each one generating its own
   retries.
5. Load snowballs: more retries mean more load on the already-struggling
   service, which causes more failures, which causes more retries.

The result: users get flooded with the same notification five, ten, twenty
times, and the downstream service — already under pressure — gets hammered
harder. Retry storms are one of the most common causes of cascading failures
in notification systems.

Idempotency keys and the dedup store are the primary defense. Even if the
retry logic generates ten copies of the same message, only the first one gets
through. But idempotency alone isn't enough — you also need:

- **Exponential backoff**: each retry waits longer than the last (1s, 2s, 4s,
  8s...) instead of retrying immediately. This gives the downstream service
  time to recover.
- **Retry caps**: set a maximum number of retries (e.g., 5) so a permanently
  failed notification doesn't retry forever.
- **Circuit breakers** (covered more in Lesson 14): if too many requests to a
  downstream service are failing, stop sending entirely for a cooldown period
  rather than adding to the pile.

## Where this fits in the architecture

Deduplication plugs in at the worker layer — the same workers from Lesson 6
(message brokers) and Lesson 8 (push delivery). A worker pulls a message off
a queue, checks the dedup store, and either sends or skips. The dedup store
itself sits alongside the worker tier, typically as a shared Redis cluster.

This connects directly to the retry and acknowledgment patterns from earlier
lessons. The message broker guarantees at-least-once delivery (it will re-
deliver a message if the worker doesn't acknowledge it). Idempotency on top
of that gives you effectively-once delivery: the broker ensures nothing is
lost, the dedup store ensures nothing is duplicated.

## Recap

- **Idempotency**: doing an operation multiple times has the same effect as
  doing it once — the key property that prevents duplicate notifications.
- **Idempotency key**: a unique ID per logical event (e.g.,
  `like:user-42:post-7731`) that travels with the message through every
  retry.
- **Deduplication store**: a fast lookup (Redis, Memcached) that tracks which
  keys have already been processed. Uses TTL to avoid unbounded growth.
- **Retry storm**: a cascading failure where retries of failed sends generate
  more retries, flooding users and overwhelming downstream services.
  Prevented by idempotency keys, exponential backoff, retry caps, and circuit
  breakers.
- At-least-once delivery from the broker + idempotency at the worker =
  effectively-once delivery.

## Check yourself

1. A worker sends a push notification and writes the idempotency key to the
   dedup store, but crashes between those two steps (the push was sent, the
   key was not written). What happens on retry, and is this an acceptable
   trade-off compared to the alternative ordering?
2. Why would you set a TTL on entries in the dedup store instead of keeping
   them forever?
