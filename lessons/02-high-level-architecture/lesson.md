# Lesson 2 — High-Level Architecture: The Map of the System

## Why this matters

Lesson 1 gave you the vocabulary for *how* a message can travel (push, pull,
poll) and the tension (latency vs. throughput) that shapes every choice.
Before we zoom into any one piece of the system, you need the whole map: what
are the actual boxes a notification passes through between "something
happened" and "a user sees it"? Every remaining lesson in this course zooms
into exactly one box on this map — so if you can hold this picture in your
head, you'll always know where a new concept slots in.

## The pipeline, end to end

Picture a chain of five stages. A notification is born at one end and a user
sees it at the other:

**Producer → Ingestion Service → Fan-Out Service → Queue → Delivery Worker → Channel**

Let's walk it one stage at a time, using a concrete example: Alice likes
Bob's photo.

### 1. Producer

A **producer** is whatever creates the event that might need to become a
notification. In our example, it's the "likes" service — the part of the app
that recorded that Alice liked Bob's photo. A producer doesn't know or care
who needs to be told about this; it just knows "this thing happened" and
announces it. Producers can be almost anything: a user action (a like, a
comment, a follow), a backend job (a payment finished processing), or a
scheduled event (a reminder is due).

### 2. Ingestion service

The **ingestion service** is the front door: it receives the raw event from
the producer, checks that it's well-formed (does it have a valid user ID? a
real event type?), and records it durably so it isn't lost even if everything
downstream is temporarily broken. Think of it like a hospital's intake desk —
before anyone treats you, someone has to check you in, verify your ID, and
put you in the system. The ingestion service's job is narrow on purpose: it
doesn't decide who gets notified or how, it just accepts the event safely and
hands it off.

### 3. Fan-out service

The **fan-out service** answers the question the ingestion service didn't:
*who needs to know about this?* For "Bob's photo got a like," that might be
just Bob. For "a celebrity you follow just posted," that could be tens of
millions of people. This is the step that expands one event into a list of
"deliver this to user X" instructions — one input, potentially many outputs.
(The word "fan-out" comes from electronics, where one output signal is split
to drive many downstream inputs — same idea here, just with notifications
instead of electrical signal.) This is enough of a problem on its own that
Lessons 4 and 5 are entirely devoted to it — for now, just know it's the
stage that turns "one event" into "N people to notify."

### 4. Queue

Once the fan-out service knows who needs a notification, those individual
"notify user X" instructions don't get delivered directly — they get dropped
into a **queue**, a waiting line that temporarily holds work until something
is ready to process it. Why not deliver directly? Because fan-out can
generate millions of instructions in a burst (remember the celebrity
example), and delivery — actually reaching a phone or browser — is slower and
less reliable than generating the instruction. The queue absorbs that burst
so a traffic spike doesn't take down the delivery machinery; it's the shock
absorber between "how fast work is created" and "how fast work is
processed." Lesson 6 is entirely about how these queues work under the hood
(message brokers like Kafka, RabbitMQ, or SQS).

### 5. Delivery worker

A **delivery worker** is a process that pulls instructions off the queue, one
at a time (or in small batches), and actually does the work of getting the
notification to the user. This is where "notify Bob" turns into "send a push
payload to Bob's phone" or "insert a row into Bob's in-app notification
list." Delivery workers are typically many identical processes running in
parallel, each grabbing whatever work is next in the queue — that's how the
system handles the volume: not one worker doing everything fast, but many
workers each doing a little.

### 6. Channel

Finally, a **channel** is the actual medium the notification travels over to
reach the user: a mobile push notification, an in-app/in-feed alert, an
email, or an SMS text. The delivery worker picks (or is told) which channel
to use for a given notification — an urgent security alert might go out over
push *and* SMS, while "someone liked your photo" might only go to the in-app
feed. Lesson 3 covers how systems decide which channel(s) to use and why;
Lesson 8 covers the delivery mechanics for push specifically.

## Why split it into stages at all?

It might seem simpler to have one program that does everything: receive the
event, figure out recipients, and send the notification, all in one
function call. The reason real systems don't do this is **independent
scaling and failure isolation**. If ingestion, fan-out, and delivery are
separate stages connected by a queue, then:

- Each stage can be scaled independently. If delivery is the slow part (it
  usually is — network calls to phones are slow), you can run 10x more
  delivery workers without touching ingestion at all.
- A slowdown or crash in one stage doesn't immediately break the others. If
  APNs (Apple's push service) has an outage, delivery workers can stall or
  retry while ingestion keeps calmly accepting new events into the queue —
  nothing is lost, it just waits its turn.
- You can reason about and monitor each stage separately, which matters a
  lot once the system is big enough that no one person understands all of it
  at once.

This pattern — small, single-purpose stages connected by queues instead of
one big program — is the backbone of almost every high-scale system, not
just notifications.

## How this maps to the rest of the course

Keep this five-stage picture in mind as a filing cabinet for everything that
follows:

- Lessons 4–5 zoom into **fan-out** (write path vs. read path, the celebrity
  problem).
- Lessons 6–7 zoom into the **queue** (message brokers, sharding).
- Lessons 8–10 zoom into **delivery workers and channels** (push mechanics,
  connection routing, pull fallback).
- Lessons 11–14 cover cross-cutting concerns that touch *every* stage
  (replay, idempotency, backpressure, delivery guarantees).
- Lessons 15–16 cover running the whole pipeline in production (monitoring,
  failure recovery).

Every one of those is a deeper look at one box in the diagram you just
learned. Nothing later contradicts this map — it only adds detail to it.

## Recap

- The pipeline: **Producer** (something happens) → **Ingestion service**
  (accepts and validates the event) → **Fan-out service** (figures out who
  needs to know) → **Queue** (absorbs the burst of work) → **Delivery
  worker** (does the actual sending) → **Channel** (push, in-app, email,
  SMS — the medium it travels over).
- Splitting the pipeline into stages connected by a queue lets each stage
  scale and fail independently — this is why real systems aren't one big
  function.
- Every later lesson zooms into exactly one stage of this map.

## Check yourself

1. Suppose the delivery workers are running slow (say, APNs is having an
   outage). Why doesn't that immediately cause the ingestion service to fall
   over too?
2. "Someone liked your photo" (one recipient) and "a celebrity you follow
   posted" (millions of recipients) both pass through the same five stages.
   Which stage does the *most* different amount of work between these two
   cases, and why?
