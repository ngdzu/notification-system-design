# Lesson 5: The Celebrity Problem — Hot Keys & Hybrid Fan-Out

## The Problem

Imagine a pop star with 100 million followers hits "post." Your fan-out service dutifully begins writing a notification to every single follower's inbox. That is 100 million writes triggered by one action. Meanwhile, the database partition holding that celebrity's data is melting. The queue worker responsible for that shard is buried. And 100 million delivery workers all wake up at the same instant, stampeding toward your push-notification provider.

This is the celebrity problem, and it breaks pure fan-out-on-write systems. Understanding why — and the fix — is essential for any notification system serving 100M+ users.

## New Terms

**Hot key.** A hot key is a single piece of data (a database row, a cache entry, a queue partition key) that receives a disproportionate share of traffic compared to everything else. If your system partitions work by user ID, and one user triggers 100 million operations, that user's ID becomes a hot key. The partition holding it gets overloaded while other partitions sit idle.

**Thundering herd.** A thundering herd happens when a sudden burst of near-simultaneous requests overwhelms a single resource. Picture a stadium where every exit is locked except one — everyone rushes the same door. In notification systems, this occurs when millions of delivery workers all try to send at the same moment, or millions of readers all query the same cache key right after it expires.

**Hybrid fan-out.** A strategy that combines fan-out-on-write (push) for normal accounts with fan-out-on-read (pull) for mega-accounts, choosing the approach based on follower count.

## Why Pure Fan-Out-on-Write Breaks

Recall from Lesson 4: fan-out-on-write means the system pre-computes each recipient's notification at write time. For a normal user with 500 followers, this is fast and efficient — 500 writes, done. But the cost scales linearly with follower count. Here is what goes wrong at celebrity scale:

**Write amplification.** One post becomes 100 million queue messages. Your ingestion service and fan-out workers must process all of them. If the celebrity posts three times in a minute, that is 300 million writes in 60 seconds.

**Hot partition.** Most systems partition data by some key (user ID, notification ID). All 100 million writes share the same source key. The database node or queue partition responsible for that key becomes a bottleneck while others are underutilized.

**Thundering herd on delivery.** Even if you manage to write all 100 million notifications, your delivery workers now attempt to push them out near-simultaneously. Your push-notification provider (APNs, FCM) will rate-limit or reject the burst. Downstream services get hammered.

**Wasted work.** Many followers are inactive. Maybe 40 million of those 100 million accounts haven't opened the app in months. Fan-out-on-write spent resources writing notifications those users will never see.

## The Fix: Hybrid Fan-Out

The insight is simple: not all accounts are equal, so don't treat them the same way.

### How It Works

1. **Classify accounts by follower count.** Set a threshold — say, 500,000 followers. Accounts above this are "mega" accounts. Everyone else is "normal."

2. **Normal accounts → fan-out-on-write (push).** When a normal user posts, the fan-out service writes a notification into each follower's inbox, exactly as before. The fan-out ratio is manageable, latency is low, and the notification is ready when the follower checks.

3. **Mega accounts → fan-out-on-read (pull).** When a celebrity posts, the system does *not* write 100 million individual notifications. Instead, it stores the post once and marks it as pending. When a follower opens the app, the system checks: "Are there new posts from any mega accounts I follow?" and assembles the notification at read time.

### An Analogy

Think of a small-town newsletter versus a national newspaper. The newsletter (normal account) gets hand-delivered to each subscriber's mailbox — there are only 200 of them. The newspaper (mega account) gets printed once and placed on newsstands. Readers pick it up when they walk by. You would never hire a courier to hand-deliver the New York Times to every subscriber in the country.

### Where Hybrid Fan-Out Sits in the Architecture

Recall the pipeline from Lessons 2–4: producer → ingestion service → fan-out service → priority queues → delivery workers → channels.

Hybrid fan-out modifies the fan-out service. Before fanning out, it checks the producer's follower count:

- **Below threshold:** fan-out-on-write as usual. Enqueue one message per follower into the priority queues.
- **Above threshold:** store the notification in a "mega posts" table. Skip the per-follower fan-out entirely. When a follower's client requests updates (pull / polling), a read-path service merges the user's regular inbox with any new mega-account posts they follow.

This means the read path for users who follow celebrities is slightly more complex — it must merge two sources (pre-written inbox + mega-account posts). But the write path no longer explodes.

### Handling the Threshold

The threshold is not magic. Some systems use a fixed number (e.g., 500K followers). Others use a dynamic threshold based on current system load. A few treat the threshold as a spectrum: accounts with 10K followers get full fan-out, accounts with 1M get partial fan-out (push to active users only, pull for inactive), and accounts with 50M get pure pull.

## Trade-Offs

| Approach | Write cost | Read cost | Latency for followers |
|---|---|---|---|
| Pure fan-out-on-write | Very high for mega accounts | Low | Low (pre-computed) |
| Pure fan-out-on-read | Low | High for every read | Higher (computed on demand) |
| Hybrid | Low (mega = pull) | Moderate (merge step) | Low for normal; slightly higher for mega |

Hybrid is a trade-off, not a free lunch. You accept more read-path complexity to avoid write-path collapse.

## Recap

- A **hot key** is a single data point overwhelmed by disproportionate traffic — like a celebrity's user ID during fan-out.
- A **thundering herd** is a burst of simultaneous requests that crushes a resource.
- Pure fan-out-on-write cannot handle mega-accounts because the write amplification, hot partitions, and delivery stampede are unsustainable.
- **Hybrid fan-out** solves this: push for normal accounts, pull for mega accounts. The fan-out service checks follower count and chooses the strategy per post.
- The read path becomes more complex (merging two sources), but the system stays alive.

## Check Yourself

1. A gaming platform sends notifications when streamers go live. One streamer has 80 million followers. Using pure fan-out-on-write, what two problems would you expect the system to hit first? How would hybrid fan-out address them?

2. Your team sets the mega-account threshold at 1 million followers. A product manager asks: "Why not set it at 100 followers so we avoid fan-out work for almost everyone?" What is the downside of an extremely low threshold?
