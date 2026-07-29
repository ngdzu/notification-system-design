# Lesson 7 — Sharding & Partitioning for Notification Data

## Why this matters

In previous lessons we introduced message brokers, fanout strategies, and
priority tiers. All of those assume you can store and move notification data
somewhere. But what happens when "somewhere" is a single database or a single
queue, and you have 100 million users generating billions of notifications per
day? The answer: it falls over. One machine has finite disk, finite memory, and
finite throughput. This lesson is about the technique you reach for when one
machine isn't enough — splitting data into smaller, independent pieces so many
machines can share the load.

## Core vocabulary

A **partition** is a slice of your data that lives and operates independently
from the other slices. If you have a billion notification rows, you might split
them into 256 partitions so each partition only manages about four million rows.
Each partition can be read and written without touching the others.

A **shard** is essentially the same idea but usually refers to the physical
machine (or database instance) that holds one or more partitions. In casual
conversation — and in most interviews — people use "shard" and "partition"
interchangeably. The important point is the same: you're dividing data so no
single node has to handle everything.

A **partition key** is the field you use to decide which partition a given piece
of data belongs to. For a notification system, the most natural partition key
is the **user ID** — every notification targets a specific user, so you route
it to the partition that owns that user. This means all of one user's
notifications sit together, which keeps reads fast: when the app loads
"show me my unread notifications," it only queries one partition instead of
scanning all of them.

## The mailroom analogy

Imagine a company with 10,000 employees and one mailroom clerk sorting all
incoming packages. At some point the clerk can't keep up — packages pile up,
delivery slows, and the clerk becomes the bottleneck. The fix: hire ten clerks,
assign each one a range of employee last names (A–C, D–F, …), and stamp every
incoming package with the employee name so it goes straight to the right desk.
Each clerk works independently, handles only their slice, and the total
throughput is roughly ten times what one clerk could manage.

In this analogy the employee last name is the partition key, each clerk's desk
is a shard, and the pile of packages at each desk is a partition.

## Why user ID is a good partition key

Choosing the right partition key matters more than it might seem. A good key
has two properties:

1. **Even distribution.** You want each partition to get roughly the same
   amount of data and traffic. User IDs that are randomly generated (UUIDs,
   snowflake IDs) spread naturally across partitions. Sequential IDs can
   work too as long as you hash them first.

2. **Query alignment.** Most notification reads are per-user — "give me this
   user's last 50 notifications." If user ID is the partition key, that query
   hits exactly one partition. If you partitioned by, say, timestamp instead,
   a single user's notifications would be scattered across many partitions and
   every read would have to gather results from all of them. That's called a
   **scatter-gather** query; it's expensive and slow.

User ID satisfies both properties for a notification system. It's the default
choice you should reach for in an interview unless you have a specific reason
not to.

## Consistent hashing

Suppose you have N shards. The simplest partition rule is `shard = hash(userID)
% N`. This works — until you need to add or remove a shard. Change N and almost
every user's hash maps to a different shard, which means you'd need to move
almost all the data. At scale, that kind of bulk migration can take hours or
days and is dangerously disruptive.

**Consistent hashing** solves this. Picture the output range of your hash
function as a circle (0 at the top, max value going clockwise, wrapping back
to 0). Place each shard at a point on the circle. To find a user's shard, hash
the user ID to a point on the circle and walk clockwise until you hit the
first shard. That shard owns the user.

When you add a new shard, you place it on the circle and it takes over only
the portion of the ring between itself and the previous shard. The other
shards don't move. Roughly 1/N of keys migrate instead of nearly all of them.
Removing a shard works the same way in reverse — only that shard's keys move
to the next shard clockwise.

In practice, each physical shard is assigned multiple points on the ring
(called **virtual nodes**) to smooth out uneven distribution. Most distributed
databases and message brokers (Cassandra, DynamoDB, Kafka) use some variant of
consistent hashing internally, so you rarely implement it from scratch — but
you need to understand the concept because interviewers expect you to explain
why simple modulo hashing breaks and consistent hashing doesn't.

## How this connects to notification architecture

Sharding shows up in at least two places in the notification system:

1. **The notification store.** Whether you use a relational database or a
   NoSQL store, the table that holds "user X has notifications Y, Z, …" gets
   sharded by user ID. This keeps per-user reads fast and distributes write
   load across machines.

2. **Message broker partitions.** Kafka topics (or similar) are split into
   partitions. Producers hash the user ID to pick a partition, and each
   partition is consumed by exactly one consumer in a consumer group. This
   means all notifications for a given user flow through the same consumer in
   order — which matters for things like badge-count accuracy and
   deduplication.

In both cases the partition key is user ID, and the goal is the same: spread
load evenly, keep per-user data together, and make it possible to scale out
by adding shards or partitions without rebuilding everything.

## Potential pitfalls

- **Hot partitions.** If one user receives vastly more notifications than
  others (a celebrity account, a bot, a system alert), that user's partition
  becomes a hot spot. This is the celebrity / hot-key problem from Lesson 5 —
  sharding alone doesn't solve it. You still need the mitigation strategies
  discussed there (splitting hot keys, rate limiting, separate handling).

- **Cross-partition queries.** "Show me all notifications sent in the last
  hour across all users" now requires querying every partition. These
  analytics-style queries are expensive on a sharded system. The common
  solution is to stream events to a separate analytics store (like a data
  warehouse) that's optimized for full scans.

- **Rebalancing cost.** Even with consistent hashing, adding or removing
  shards requires migrating data. Plan for this to happen in the background
  with the system still serving traffic — never as a stop-the-world
  operation.

## Recap

- One database or queue can't handle notification traffic for hundreds of
  millions of users; you split data into **partitions** (logical slices) spread
  across **shards** (physical machines).
- The **partition key** — almost always user ID for notifications — determines
  which shard owns a piece of data.
- **Consistent hashing** maps keys to shards using a ring so that adding or
  removing a shard only moves ~1/N of the data instead of nearly all of it.
- Sharding applies to both the notification database and the message broker
  partitions.

## Check yourself

1. You're designing the notification store for a 200-million-user app. A
   teammate suggests partitioning by notification creation timestamp instead
   of user ID. What problems would that cause for the most common query
   ("fetch my unread notifications")?

2. Your system currently has 12 Kafka partitions for the notification topic.
   Traffic has doubled and you need to add 4 more partitions. Explain why
   simple `hash(userID) % N` would be disruptive here and how consistent
   hashing reduces the blast radius.
