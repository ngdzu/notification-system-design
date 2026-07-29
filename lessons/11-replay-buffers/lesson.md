# Lesson 11 — Replay Buffers & Missed-Message Recovery

## The Problem: What Happened While I Was Gone?

Picture your phone losing signal in a subway tunnel for three minutes. When you resurface, your messaging app needs to catch up — fast. But how does it know *what* it missed? And where does it get those messages without making the server redo all the work?

This is the problem replay buffers solve.

---

## Core Concepts

### Replay Buffer

A **replay buffer** is a short-term store that keeps a copy of every recently sent notification, indexed by position. Think of it like a DVR for your notification stream: the live broadcast keeps going, but the last N hours are recorded so anyone who missed something can rewind and catch up.

When a client reconnects, it says: "The last message I saw was at position 4,821." The server checks the replay buffer, finds everything from 4,822 onward, and streams it back. No need to re-query upstream databases, re-evaluate rules, or re-run delivery logic. The work was already done — it just needs to be *re-sent*.

In practice, a replay buffer is usually backed by an ordered log structure — Redis Streams, Apache Kafka, or even an append-only table in a relational database. The key property is that entries are ordered and addressable by position.

### Retention Window

A **retention window** is the time period (or size limit) for which the replay buffer keeps messages. A typical window might be 24 hours or 100,000 entries per user, whichever limit is hit first.

Why not keep everything forever? Cost and relevance. Storing every notification ever sent to 100M+ users adds up fast. And if a user has been offline for a month, replaying 30 days of notifications is a worse experience than showing a summary or pulling fresh state from the database.

The retention window is a design trade-off:

| Window size | Pro | Con |
|---|---|---|
| Short (1–4 hours) | Low storage cost | Clients offline longer must fall back to a full sync |
| Medium (12–24 hours) | Covers overnight disconnects, sleep cycles | Moderate storage |
| Long (3–7 days) | Handles weekend outages, vacations | High storage cost, stale data risk |

Most systems land on 12–24 hours. That covers the common case — a phone losing connectivity, an app being killed by the OS, a user sleeping — without excessive storage.

### Gap Detection

**Gap detection** is the mechanism a client uses to realize it missed messages in the first place. You cannot recover what you do not know you lost.

The most common approach uses **sequence numbers**. Every notification delivered to a client carries a monotonically increasing sequence number. The client tracks the last number it received. On reconnect (or even mid-session if the connection hiccups), it compares:

- **Expected next**: last received + 1
- **Server's current**: the latest sequence number on the server

If they match, nothing was missed. If there is a gap (client has 4,821, server is at 4,830), the client knows it missed messages 4,822 through 4,830 and requests a replay of that range.

Other gap detection strategies exist:

- **Timestamp-based**: the client sends its last-seen timestamp; the server returns everything newer. Simpler but less precise — clock skew between servers can cause duplicates or missed entries.
- **Vector clocks / version vectors**: used in multi-source systems where notifications arrive from different partitions. More complex, but handles partial ordering.

For most notification systems, per-user sequence numbers are sufficient.

---

## How It Fits Together

Here is the reconnection flow in a system using replay buffers:

1. **Client connects** and sends its last known sequence number to the server.
2. **Server checks the replay buffer** for that user.
   - If the sequence number falls within the retention window, the server streams all messages from that point forward. This is the fast path.
   - If the sequence number is older than the retention window (the client has been offline too long), the server falls back to a **full sync** — querying the notification database for unread items.
3. **Client processes replayed messages**, updates its local state and sequence number, then switches to the live stream.

This two-tier design is important. The replay buffer is the fast, cheap path that handles 95%+ of reconnections. The full sync is the slow, expensive fallback for edge cases. Without the replay buffer, *every* reconnection would hit the database.

### Scaling Replay Buffers

At 100M+ users, even a "simple" buffer needs thought:

- **Storage**: If each user averages 50 notifications/day at 1 KB each, a 24-hour buffer for 100M users is ~5 TB. Redis can handle this across a cluster, but it is not free.
- **Partitioning**: Shard the buffer by user ID so no single node holds everything. This also means a reconnecting client only hits one shard.
- **Eviction**: Use TTL-based expiration (Redis `XADD` with `MAXLEN` or `MINID`) so old entries are cleaned up automatically without batch jobs.

### Idempotency Matters

Replayed messages may include notifications the client *already* processed before disconnecting (the server may not know exactly where the client stopped). Clients must handle duplicates — typically by checking the sequence number or a unique message ID against local state before displaying a notification.

---

## Recap

- A **replay buffer** stores recent notifications so reconnecting clients can catch up without expensive re-derivation.
- A **retention window** bounds how far back the buffer goes, balancing storage cost against coverage of common offline durations.
- **Gap detection** (usually via sequence numbers) lets clients discover they missed messages and request exactly the range they need.
- When the gap exceeds the retention window, the system falls back to a full database sync.
- Clients must be idempotent — replays can include duplicates.

---

## Check Yourself

1. A user's phone dies at 11 PM and they plug it in at 7 AM (8 hours later). Your replay buffer has a 4-hour retention window. What happens when the app reconnects, and what would you change to avoid this scenario?

2. Your system uses per-user sequence numbers for gap detection. A client reconnects and reports its last sequence number as 500, but the server's replay buffer starts at sequence 450 and the current head is 520. Describe exactly what the server sends back and why the client might receive some messages it already saw.
