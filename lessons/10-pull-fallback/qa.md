## Q1: you said push and pull both share the notification store. Where is the notification store located? (2026-07-30)

The notification store is a database table (or set of sharded tables) that holds every notification ever created for every user — a permanent record, independent of whether it was ever successfully pushed. It's not a new component invented in Lesson 10; it's the same store first introduced back in Lesson 2's five-stage pipeline (Producer → Ingestion → Fan-out → Queue → Delivery worker → Channel). When Lesson 2 said a delivery worker turns "notify Bob" into "insert a row into Bob's in-app notification list," that insert *is* the write into the notification store.

Concretely, it sits like this:

- **What it is:** a database (e.g., Cassandra, DynamoDB, or a sharded Postgres/MySQL cluster) with one row per notification, per user.
- **Where it's positioned in the pipeline:** the delivery worker writes to it *before* attempting any real-time delivery (Lesson 10's diagram: "New notification created → Write to Notification Store → Attempt push delivery"). So the write happens regardless of whether push succeeds.
- **How it's organized at scale:** Lesson 7 (sharding) explains that this table is sharded/partitioned by user ID, so all of one user's notification history lives on the same shard — that's what makes a per-user inbox read ("give me everything after my last-seen ID") a single-shard query instead of a scatter-gather across the whole cluster.
- **What it is not:** it's a separate thing from the badge-count counter (that lives in Redis, an in-memory cache, because it needs single-digit-millisecond reads) and separate from the message queue/broker like Kafka (that's transient — it holds "work to be done," not permanent history).

So the notification store is the durable system of record. The queue is a temporary staging area for work in flight; Redis is a fast cache for a derived number (unread count); the notification store is where the actual notification content and its "have you read this" state persistently lives.

## Q2: When you say push and pull, are we talking about APN or delivery in general? (2026-07-30)

In Lesson 10, "push" and "pull" are general terms, not APNs-specific ones. Here's the mapping to earlier lessons:

- **Push** = any mechanism where the *server* proactively sends the notification to the client without the client asking first. This includes APNs (Apple Push Notification service, iOS) and FCM (Firebase Cloud Messaging, Android) — covered specifically in Lesson 8 — but it also includes a live WebSocket push to a web/in-app client, covered in Lesson 9. All of these count as "push" in Lesson 10's sense: the server initiates delivery, and it's fast when it works.
- **Pull** = the client actively asking the server "what did I miss?" via a request/response API call (`GET /v1/notifications?since=...`), regardless of what channel would have been used for push. This is channel-agnostic — it doesn't matter whether the original notification was meant for APNs, FCM, or a WebSocket; if it never arrived, pull is the universal catch-up mechanism because it just reads from the shared notification store.

So when Lesson 10 says "push failed," it means *any* real-time delivery path failed — a dropped WebSocket, an expired APNs device token, a phone in airplane mode when FCM tried to deliver, etc. Pull fallback works the same way no matter which push mechanism was attempted, because all of them ultimately trace back to the same underlying write into the notification store.

## Q3: in the pipeline Producer → Ingestion → Fan-out → Queue → Delivery worker → Channel, there is no mention of the database, where does it live? (2026-07-30)

It lives inside the Delivery worker stage. The Delivery worker writes the notification to the database first, then hands off to Channel for actual delivery (push/in-app/email/SMS). It's not a separate box in the six-stage diagram — it's an action the Delivery worker performs as part of its job, before Channel runs.

## Q4: so you say the delivery worker owns the database? or is it shared between many of them? (2026-07-30)

Shared. The database is an independent, external data store (Lesson 2 said "many identical [delivery worker] processes running in parallel"), and every one of those delivery worker instances connects to the same shared database cluster to write rows. No delivery worker owns or holds a private copy — "owns" would imply the data lives inside the worker process, but it doesn't; the worker is just a client making a write to a database that lives elsewhere on the network, same as every other worker.

## Q5: when user pull for notification, how does client access the database? (2026-07-30)

The client never touches the database directly. It calls a server-side API (`GET /v1/notifications?since=<last-seen-id>&limit=50`), and that server queries the database on the client's behalf, then returns the results as JSON. Direct client-to-database access is avoided for the same reasons any production system avoids it: the database's schema, sharding scheme, and credentials all stay hidden behind the API, so the server can change the database's internals without breaking every client, and the server can enforce auth (only return the requesting user's own notifications).

## Q6: is there a server which serve data from the database? (2026-07-30)

Yes. Lesson 10's sequence diagram names it explicitly: `Client → Server → Store`. That "Server" is the pull API server — a stateless service whose job is to take the incoming `GET /v1/notifications` request, extract the user ID and cursor, query the notification store, and return the response (notifications + unread_count + next_cursor). It's typically a separate service from the delivery workers: delivery workers handle the write path (creating notifications, attempting push), while this pull API server handles the read path (serving history back to clients). Splitting them lets each scale independently — read traffic and write traffic don't have to compete for the same process pool.
