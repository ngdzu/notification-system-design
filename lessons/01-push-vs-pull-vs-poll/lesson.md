# Lesson 1 — Why Notification Systems Are Hard at Scale (Push vs. Pull vs. Poll)

## Why this matters

Sending one notification is trivial — call an API, show a banner, done. The
hard part shows up the moment you have hundreds of millions of users: one
popular post can trigger millions of notifications in seconds, and every one
of those has to arrive fast without knocking the system over. Before we can
design anything, we need a shared vocabulary for what a notification even is
and the handful of basic strategies for getting it to a user.

## What is a notification, really?

A **notification** is a small, timely message telling a user that something
happened — "Alice liked your photo," "Your order shipped," "You have a new
message." It's small (a few lines of text plus maybe an ID or link) and
timely (it loses most of its value if it arrives an hour late instead of
seconds late). That combination — small payload, strict freshness — is why
notification systems are their own design problem instead of just "send some
data somewhere."

## Three ways to deliver: push, pull, poll

There are exactly three basic strategies for getting new information from a
server to a client (a client is whatever is displaying the notification —
usually a phone app or browser tab).

**Push** means the server proactively sends data to the client the instant
it's ready, without the client asking first. Think of it like a phone
ringing: the caller initiates, you just react. Technically this relies on the
server holding open some channel to the client (we'll get into exactly how in
later lessons) so it has somewhere to push the message *to*. Push gives the
best user experience — notifications feel instant — but it means the server
has to do work (and use resources) for every connected client, all the time,
whether or not anything is happening.

**Pull** means the client asks the server "anything new for me?" on its own
initiative. Think of it like checking your mailbox: nobody rings your
doorbell, you just walk out and look. The specific pattern of pulling on a
fixed schedule ("check every 30 seconds") is called **polling**. Pull is
simpler and more robust — if the client's network drops for a while, it just
asks again next time it's back online — but it trades that robustness for
delay: if you poll every 30 seconds, a notification can sit ready-and-waiting
on the server for up to 30 seconds before the client ever notices it.

**Hybrid** approaches use push as the primary path (for speed) and fall back
to pull when push isn't available or reliable — e.g., the client's push
connection dropped, or a lot of time passed and the client wants to make sure
it didn't miss anything. Almost every real notification system at scale is a
hybrid, not a pure push or pure pull system. Later lessons build this hybrid
model in detail (Lesson 8 covers push delivery mechanics, Lesson 10 covers
pull as a deliberate fallback, not just a fallback plan).

## The core tension: latency vs. throughput

Two terms are going to come up constantly for the rest of this course, so
let's define them now:

- **Latency** is how long delivery takes — the time between "something
  happened" and "the user saw the notification." Lower is better; this is
  what push optimizes for.
- **Throughput** is how many messages the system can process per unit time
  (e.g., notifications per second). This is what determines whether your
  system survives a celebrity posting something that a million followers all
  need notified about at once.

Every design decision in this course is really a trade-off between these two.
Pushing to every client the instant something happens minimizes latency but
maximizes the load the system carries at every moment. Batching, queuing, and
polling reduce that load (raising throughput capacity) at the cost of some
delay. You'll see this tension resurface explicitly in fan-out strategy
(Lesson 4), broker design (Lesson 6), and backpressure (Lesson 13) — it's the
single idea that ties the whole system together.

## Recap

- A notification is a small, timely message — freshness is part of its
  value, not a nice-to-have.
- **Push**: server sends proactively, best latency, costs resources per
  connected client.
- **Pull / polling**: client asks on its own schedule, simpler and more
  resilient, worse latency.
- Real systems are **hybrids**: push as the fast path, pull as the fallback.
- **Latency** (speed of delivery) and **throughput** (volume the system can
  handle) are in tension — nearly every later design choice is picking a
  point on that trade-off curve.

## Check yourself

1. Why is polling every 5 seconds not simply "better" than polling every 60
   seconds if it gets notifications to users faster?
2. A client's push connection just dropped for 10 minutes due to a network
   issue. Why might the system need a pull-based fallback even though it's
   fundamentally a "push" system?
