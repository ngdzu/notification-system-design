# Lesson 13: Backpressure & Rate Limiting — Protecting the System from Itself

Your notification pipeline can handle millions of messages per minute — until it suddenly can't. A flash sale starts, a celebrity posts, or a deployment goes wrong, and event volume spikes 10x in seconds. If producers keep flooding in work faster than consumers can process it, queues grow without bound, memory fills up, and the whole pipeline collapses. The system's biggest threat isn't external attackers — it's its own traffic.

This lesson covers four defense mechanisms: backpressure, rate limiting, load shedding, and circuit breakers. Together they keep a spike from becoming an outage.

---

## Backpressure: Telling Producers to Slow Down

**Backpressure** is a signal from a downstream component to an upstream one that says "I'm falling behind — slow down." Instead of silently accepting work into an ever-growing queue, the system pushes resistance back toward the source.

### Analogy

Picture a factory assembly line. If the painting station can only paint 100 widgets per hour but the welding station sends 200, unpainted widgets pile up on the floor. A smarter design: when the painting station's staging area is nearly full, a light turns red, and the welding station pauses until there's room. That red light is backpressure.

### How It Works in Practice

There are several common ways to implement backpressure:

- **Bounded queues.** Set a maximum size on every queue. When the queue is full, the producer's publish call blocks or returns an error. The producer must retry or slow its own intake. Kafka does this with `max.block.ms` — if the broker can't accept a message within that window, the producer gets an exception.
- **Credit-based flow control.** The consumer grants the producer a fixed number of "credits" (permits to send). Each message costs one credit. When credits run out, the producer stops until the consumer issues more. TCP's sliding window works exactly this way.
- **Reactive streams.** Frameworks like Project Reactor or RxJava let the subscriber request N items at a time. The publisher only emits as many items as the subscriber has requested.

The key principle: producers should never be allowed to push unbounded work into the system. Every queue needs a size limit, and hitting that limit must create a visible signal — not silent data loss.

---

## Rate Limiting: Capping How Fast Anyone Can Send

**Rate limiting** caps the number of requests a client or service can make within a time window. While backpressure is an internal signal between pipeline stages, rate limiting is typically enforced at the edge — API gateways, ingestion endpoints, or per-tenant policies.

Two classic algorithms handle rate limiting:

### Token Bucket

Imagine a bucket that holds a fixed number of tokens — say, 100. Every second, 10 new tokens are added (up to the maximum of 100). Each request costs one token. If the bucket is empty, the request is rejected or queued. This allows short bursts (you can spend all 100 tokens at once if the bucket is full) while enforcing a sustained average rate (10 per second).

**Token bucket** is the most widely used algorithm because it naturally handles bursty traffic. AWS API Gateway, Stripe, and most cloud rate limiters use variations of it.

### Leaky Bucket

The **leaky bucket** works differently. Requests enter a fixed-size bucket, and the bucket "leaks" (processes requests) at a constant rate. If the bucket overflows, excess requests are dropped. Unlike token bucket, leaky bucket enforces a strictly smooth output rate — no bursts. It acts like a funnel: no matter how fast you pour water in, it drips out at the same speed.

### Which to Choose

| Algorithm | Burst Handling | Output Rate | Best For |
|---|---|---|---|
| Token bucket | Allows short bursts | Variable (up to burst) | APIs, user-facing rate limits |
| Leaky bucket | No bursts allowed | Constant | Smoothing traffic to fragile downstream services |

In a notification system, you might use token bucket at the API gateway (let clients burst a bit) and leaky bucket internally to smooth delivery to push providers like APNs or FCM, which have their own rate limits.

---

## Load Shedding: Dropping Work on Purpose

When backpressure and rate limiting aren't enough — when the system is truly overwhelmed — **load shedding** deliberately drops low-priority work to protect high-priority work.

This sounds reckless, but it's the opposite. Without load shedding, all traffic degrades equally. A password-reset notification gets the same treatment as a marketing email, and both arrive late. With load shedding, the system uses the priority tiers from Lesson 3:

- **Critical** (security alerts, auth codes): never shed.
- **High** (direct messages, payment confirmations): shed only under extreme load.
- **Medium** (social interactions): shed early.
- **Low** (marketing, recommendations): shed first.

Implementation is straightforward. Each queue or worker checks overall system health (CPU, queue depth, error rate). When health crosses a threshold, it stops accepting anything below a certain priority tier. As load drops, lower-priority traffic is re-admitted.

Think of it like a hospital triage: when the emergency room is overflowing, you postpone routine checkups to focus on critical patients.

---

## Circuit Breaker: Stop Hammering a Dead Service

A **circuit breaker** monitors calls to a downstream service and stops making calls when that service is failing, giving it time to recover.

It has three states:

1. **Closed** (normal). Requests flow through. The breaker tracks the failure rate.
2. **Open** (tripped). The failure rate exceeds a threshold — say, 50% of calls failed in the last 30 seconds. The breaker stops all requests immediately and returns a fallback or error. No traffic reaches the struggling service.
3. **Half-Open** (probing). After a cooldown period (e.g., 30 seconds), the breaker lets a small number of test requests through. If they succeed, it resets to Closed. If they fail, it goes back to Open.

### Why This Matters for Notifications

Consider your delivery workers calling APNs (Apple Push Notification service). APNs goes down. Without a circuit breaker, thousands of workers keep sending requests, getting timeouts, and retrying — which wastes resources, clogs retry queues, and can cascade failures upstream. With a circuit breaker, the system detects APNs is down within seconds, stops sending, queues notifications for later, and periodically checks if APNs is back.

Libraries like Hystrix (now in maintenance), Resilience4j, and Polly implement this pattern out of the box.

---

## How These Mechanisms Work Together

In a real notification pipeline, these four mechanisms layer:

1. **Rate limiting** at the API gateway stops abusive or misconfigured clients from flooding ingestion.
2. **Backpressure** between the message broker and consumers prevents queue buildup from overwhelming workers.
3. **Load shedding** inside workers drops low-priority notifications when the system is saturated.
4. **Circuit breakers** on outbound calls to delivery providers (APNs, FCM, SMTP) prevent cascading failures when a provider goes down.

No single mechanism is enough. Rate limiting doesn't help when the overload comes from legitimate internal traffic. Backpressure doesn't help when a downstream service is dead. Each solves a different failure mode.

---

## Recap

- **Backpressure** signals upstream to slow down when downstream is overwhelmed. Implemented via bounded queues, credit-based flow control, or reactive streams.
- **Rate limiting** caps request volume at the edge. **Token bucket** allows bursts within an average rate; **leaky bucket** enforces a constant output rate.
- **Load shedding** deliberately drops low-priority work so high-priority work survives overload.
- **Circuit breakers** stop calling a failing service, wait for recovery, then probe before resuming full traffic.
- These four mechanisms layer together — each protects against a different failure mode.

---

## Check Yourself

1. Your notification system processes 50,000 messages per second normally, but a product launch spikes volume to 500,000/s. Walk through how backpressure, rate limiting, load shedding, and circuit breakers each contribute to keeping the system alive. In what order do they activate?

2. A downstream email provider starts returning 503 errors on 60% of requests. Explain what happens with and without a circuit breaker. What state transitions does the breaker go through once the provider recovers?
