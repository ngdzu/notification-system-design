# Lesson 6 — Message Brokers & Queues 101 (The Post Office of System Design)

## Why this matters

In Lesson 2 you saw that a queue sits between fan-out and delivery, absorbing
bursts of work so a traffic spike doesn't crush the delivery workers. But we
hand-waved what that queue actually *is*. How does it hold millions of
messages? How do workers divide the load? How does the system remember what
has already been processed? This lesson answers all three questions by
introducing the **message broker** — the infrastructure that makes queues
work at scale.

## The post office analogy

Imagine a city where every business needs to send letters to every other
business. Without a post office, each sender has to know exactly where each
recipient is, wait for them to answer the door, and retry if nobody's home.
Now add a post office: senders drop letters there, recipients pick them up
when they're ready, and nobody needs to know each other's address or
schedule. A message broker is that post office for your backend services.

## Core concepts

### Message broker

A **message broker** is a piece of infrastructure that sits between the
services that produce messages and the services that consume them. Instead of
Service A calling Service B directly (and waiting for a response, failing if
B is down, or overwhelming B with traffic), A sends its message to the
broker and walks away. B reads from the broker at its own pace. The broker's
job is to accept, store, and deliver messages reliably.

Popular brokers you'll hear about in interviews: **Apache Kafka** (high
throughput, log-based), **RabbitMQ** (flexible routing, traditional queue),
and **Amazon SQS** (fully managed, no servers to run). They differ in
details, but all three solve the same core problem: decoupling producers from
consumers.

### Producer and consumer

A **producer** is any service that sends a message to the broker. A
**consumer** is any service that reads messages from the broker. In a
notification system, the fan-out service is a producer — it generates
"notify user X" instructions. The delivery workers are consumers — they
read those instructions and actually send the push notification, email, or
SMS.

The key insight: producers and consumers don't need to know about each other.
The producer doesn't know how many consumers there are or how fast they're
running. The consumer doesn't know which service produced the message. The
broker is the only thing they both talk to.

### Queue vs. topic

Brokers offer two main ways to organize messages, and the distinction matters:

A **queue** is a simple line. Messages go in one end, one consumer reads each
message from the other end, and once read the message is gone. If you have
three consumers reading from one queue, each message goes to exactly one of
them — the work is divided. Think of a single deli counter: you take a
number, and whichever clerk is free calls your number. Nobody gets called
twice.

A **topic** (sometimes called a channel or subject) works differently: every
message published to a topic is delivered to *all* subscribers. If three
services subscribe to the "user-activity" topic, all three get every message.
Think of a radio broadcast: everyone tuned in hears the same song.

In practice, most notification systems use topics (Kafka calls them topics,
RabbitMQ can model them with exchanges and bindings). Why? Because the same
event — "Alice liked Bob's photo" — might need to reach the notification
service *and* the analytics pipeline *and* the activity feed service. A topic
lets all three receive the event independently.

### Consumer group

Here's where it gets clever. You often want *both* behaviors: broadcast the
message to multiple services, but within each service have multiple workers
sharing the load. This is exactly what a **consumer group** does.

A consumer group is a set of consumers that act as one logical subscriber to a
topic. The broker delivers each message in the topic to *one* member of
each consumer group — not all of them. If you have 10 delivery workers in
the "push-notification" consumer group, each message gets handled by exactly
one of the 10. But if there's also a separate "analytics" consumer group,
those workers *also* get every message independently.

Back to the post office: a consumer group is like a company that has a shared
mailbox. The post office delivers one copy of each letter to the company's
box, and whichever employee checks the box first picks up that letter.
Meanwhile another company with its own mailbox also gets its own copy.

This is how real notification systems scale delivery: run 5, 50, or 500
workers in the same consumer group, and the broker automatically spreads
messages across them. Add workers when traffic spikes, remove them when it
calms down — no code changes needed.

### Offset

When a consumer reads messages from a topic, the broker needs to know where
that consumer left off — especially if the consumer crashes and restarts.
An **offset** is a bookmark: a number that says "I've read up to message
#4,207 in this partition of this topic."

In Kafka, offsets are stored per consumer group per partition. When a
consumer commits its offset, it's telling the broker "I've successfully
processed everything up to this point — if I crash, resume from here." If
a consumer restarts without having committed, it will re-read some messages
(which is why Lesson 12 on idempotency matters — your system must handle
the occasional duplicate gracefully).

In SQS and RabbitMQ, the equivalent concept exists but works slightly
differently: SQS uses a "visibility timeout" (the message becomes invisible
to other consumers while one is processing it, and gets deleted when the
consumer confirms success), and RabbitMQ uses "acknowledgments." The idea
is the same across all three: the consumer must tell the broker "I'm done
with this one" before the broker considers it processed.

## How this fits in the notification architecture

Remember the five-stage pipeline from Lesson 2:

**Producer → Ingestion → Fan-out → Queue → Delivery Worker → Channel**

The message broker *is* the queue stage. More precisely, the broker is the
infrastructure running that stage, and topics/queues are how messages are
organized within it. The fan-out service is a producer writing to the
broker; the delivery workers are consumers in a consumer group reading
from it. When someone says "we use Kafka between fan-out and delivery,"
they mean a Kafka broker holds the "notifications" topic, and delivery
workers form a consumer group that reads from it.

This is also why the queue absorbs traffic spikes (Lesson 2's "shock
absorber"): the broker stores messages on disk, so producers can write at
whatever rate events arrive, and consumers process at whatever rate they
can manage. The gap between the two is just a growing backlog — the broker
holds it patiently, like the post office holding your mail while you're on
vacation.

## Recap

- A **message broker** (Kafka, RabbitMQ, SQS) sits between producers and
  consumers so they don't need to know about each other or run at the same
  speed.
- A **queue** delivers each message to one consumer (work division). A
  **topic** delivers each message to all subscribers (broadcast).
- A **consumer group** gives you both: broadcast across groups, work
  division within each group.
- An **offset** is a bookmark tracking how far a consumer has read, so it
  can resume after a crash without missing messages (though it may re-read
  some — handled by idempotency, Lesson 12).
- In the notification pipeline, the broker is the queue stage between
  fan-out and delivery.

## Check yourself

1. You have three independent services — push delivery, email delivery, and
   analytics — that all need to process every notification event. Would you
   use three separate queues, or one topic with three consumer groups? Why?
2. A delivery worker crashes after reading a message but before committing
   its offset. What happens when the worker restarts — does the message get
   lost, delivered twice, or something else?
