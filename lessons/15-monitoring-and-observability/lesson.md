# Lesson 15 — Monitoring, Metrics & Observability

## Why this matters

You built a notification system that handles 100M+ users, sharded queues,
fanout pipelines, retry logic, and multi-channel delivery. Everything looks
great in staging. Then one Thursday at 2 PM, push delivery latency spikes to
30 seconds for 5% of users — and nobody notices until support tickets pile up
an hour later. The system was running, but nobody could see what it was
doing. That gap is what this lesson is about.

## Observability: more than dashboards

**Observability** is the ability to understand what your system is doing
right now and *why*, purely from its external outputs — logs, metrics, and
traces. The word comes from control theory: a system is "observable" if you
can figure out its internal state from what it emits. In practice,
observability means you can answer novel questions about your system without
deploying new code. "Why are SMS deliveries slow for users in Brazil?" is the
kind of question you want to answer from your desk, not by adding a
one-off print statement and redeploying.

Monitoring (watching known metrics and alerting on thresholds) is a subset of
observability. Monitoring tells you *that* something broke. Observability
tells you *why*.

## SLIs and SLOs: measuring what you promise

An **SLI (Service Level Indicator)** is a carefully chosen metric that
captures how well your service is performing from the user's perspective. Not
CPU load, not queue depth — those are internal signals. An SLI is something
the user would care about. For a notification system, useful SLIs include:

- **Delivery latency** — time from event creation to notification arriving on
  the user's device.
- **Delivery success rate** — fraction of notifications that actually reach
  the device (not dropped, not expired, not rejected by the push provider).
- **Freshness** — for pull-based clients, how recent the data is when they
  see it.

An **SLO (Service Level Objective)** is a target you set for an SLI. It's
a promise to yourself (and often to internal teams or paying customers):
"99.9% of push notifications will be delivered within 5 seconds." That
sentence has both pieces — the SLI is "push delivery latency" and the SLO is
"99.9% within 5 seconds." SLOs give you a concrete threshold for when things
are fine versus when you need to act. Without one, "latency went up" is
ambiguous — up from what, and does it matter?

You will sometimes hear **SLA (Service Level Agreement)**. That's a
contractual SLO with consequences (refunds, credits) when you miss it. SLAs
live in legal documents. SLOs live in your engineering team's dashboards.

## The four golden signals

Google's SRE book distills the most important things to monitor into four
**golden signals**. Every service, including every component of your
notification pipeline, should track these:

1. **Latency** — how long requests take. Measure both successful and failed
   requests separately; a fast error is not "good latency." In a notification
   system: how long from "event ingested" to "push delivered."

2. **Traffic** — how much demand your system is handling. Requests per second
   to the ingestion API, messages per second flowing through Kafka, pushes
   per second sent to APNs/FCM.

3. **Errors** — the rate of failed requests. This includes explicit failures
   (HTTP 500s, rejected pushes) and implicit ones (a push that "succeeds"
   but the payload was malformed, so the user sees a blank notification).

4. **Saturation** — how full your system is. Queue depth growing faster than
   consumers drain it, CPU at 90%, database connection pool exhausted. This
   is your early-warning signal; problems here predict future problems in the
   other three.

If you instrument nothing else, instrument these four for every service in
your pipeline.

## Percentile latency: why averages lie

Suppose your notification delivery times over the last minute are: 50ms,
55ms, 60ms, 70ms, 80ms, 90ms, 100ms, 120ms, 200ms, 5000ms. The average is
582ms. But nine out of ten users experienced under 200ms — the average is
dragged up by one outlier. Worse, that outlier is a real user having a
terrible experience, and the average hides them.

**Percentile latency** fixes this. Sort all latency values from lowest to
highest:

- **p50** (the median) — the value where 50% of requests are faster. "Half
  of notifications arrive in under this time." This is your typical-case
  number.
- **p95** — 95% of requests are faster. "Only 1 in 20 users sees worse than
  this."
- **p99** — 99% of requests are faster. "Only 1 in 100 users sees worse."

In the example above, p50 is about 80ms (good), p95 is about 200ms (fine),
and p99 is 5000ms (terrible — someone is waiting 5 seconds).

For notification systems, your SLO should be defined on a percentile, not an
average. "p99 delivery latency under 5 seconds" is meaningful. "Average
delivery latency under 1 second" can be met while 1% of your users wait
30 seconds.

## Distributed tracing: following one notification across services

A single notification in your system touches many services: the ingestion
API, a priority router, a fanout service, a template renderer, a
per-channel delivery worker, and maybe a retry handler. When that
notification is slow, which service caused the delay?

**Distributed tracing** solves this by assigning a unique **trace ID** to
each request at the edge (when it enters your system) and propagating that ID
through every service the request passes through. Each service records a
**span** — a timestamped record of the work it did — tagged with the trace
ID. Stitch the spans together and you get a timeline showing exactly where
time was spent.

Concretely: notification `abc-123` enters the ingestion API (span: 2ms),
moves to fanout (span: 5ms), waits in the Kafka queue (span: 3100ms — found
it), reaches the push delivery worker (span: 40ms), calls FCM (span: 150ms).
The 3.1-second queue wait is immediately visible. Without tracing, you would
be guessing.

Tools like Jaeger, Zipkin, and cloud-native equivalents (AWS X-Ray, Google
Cloud Trace) implement this pattern. The key implementation detail: every
service must forward the trace ID in headers or message metadata. If one
service drops it, the trace breaks.

## How this connects to notification architecture

In previous lessons, you built ingestion APIs, Kafka topics, fanout workers,
per-channel delivery services, and retry queues. Each of those is a service
that needs:

- Golden-signal metrics (latency, traffic, errors, saturation).
- SLOs defined on the user-facing SLIs (end-to-end delivery latency and
  success rate, not just internal per-service numbers).
- Trace context propagated through Kafka message headers so you can follow a
  notification from ingestion to delivery.
- Percentile-based alerting: alert when p99 delivery latency exceeds your
  SLO, not when the average moves.

A common pattern: instrument the ingestion API to stamp each notification
with a trace ID and a creation timestamp. The final delivery worker records
the delivery timestamp. The difference is your end-to-end latency SLI. Emit
it as a metric, aggregate into percentiles, and alert against your SLO.

## Recap

- **Observability** = understanding what your system does and why, from its
  outputs (metrics, logs, traces).
- **SLI** = a metric measuring user-facing service quality. **SLO** = the
  target you set for that metric.
- **Golden signals** = latency, traffic, errors, saturation — the four
  things every service should measure.
- **Percentile latency** (p50/p95/p99) tells you what real users experience;
  averages hide outliers.
- **Distributed tracing** follows one request across services by propagating
  a trace ID through every hop.

## Check yourself

1. Your notification system has an average delivery latency of 200ms but
   users are complaining about slow notifications. What metric should you
   look at instead of the average, and why might it tell a different story?

2. You notice that your Kafka consumer group's lag (unprocessed messages) is
   growing steadily. Which of the four golden signals does this fall under,
   and what does it predict about the other three signals if left unchecked?
