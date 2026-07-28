# Appendix A — Anatomy of a Connection

## Why this appendix exists

Lesson 1 said push works by "the server holding open some channel to the
client," and that this costs resources per connected client, 24/7. This
appendix zooms all the way in on that sentence. What *is* a connection,
physically? Where does it live? How many megabytes does one cost, and why?
And what actually happens when one dies — say, when you press Ctrl+C in a
terminal? You don't need this to follow the main course, but Lessons 8, 9,
and 10 all get easier once you can picture a connection as a concrete thing
instead of a magic pipe.

This appendix is a hub: the core idea is below, and the deep-dive details
each live in their own linked file.

## A connection is memory, not a wire

Start with the physical layer. Between your phone and a server there is no
dedicated wire reserved for you. The internet is **packet-switched**: your
data is chopped into **packets** (small chunks, each stamped with a
destination address) that hop router-to-router, sharing every link with
millions of strangers' packets. Nothing along the path is "yours." (For how
bits actually get pushed onto a shared cable or airwaves without colliding,
and why the wire itself never guarantees delivery, see
[physical-layer-and-multiplexing](physical-layer-and-multiplexing.md).)

So where does the "connection" live? In **RAM, at the two ends**. When a
client opens a TCP connection (TCP is the internet's standard reliable
transport protocol), both machines run a **handshake** — a three-message
exchange ("can we talk?" / "yes, can you hear me?" / "yes") — and then each
side allocates a **socket**: a kernel data structure (the kernel is the core
of the operating system) that remembers the connection's state (see
[kernel-memory-and-sockets](kernel-memory-and-sockets.md) for exactly where that lives in RAM). That
state includes the 4-tuple identity, sequence numbers tracking every byte
sent, and send/receive buffers — see [sequence-numbers-and-buffers](sequence-numbers-and-buffers.md) for
the last two.

### The 4-tuple: naming your connection

The **4-tuple** is the connection's globally unique ID:
- **source IP** (the client's IP address)
- **source port** (the client's ephemeral port, typically something like 51823)
- **destination IP** (the server's IP, e.g., 10.0.0.5)
- **destination port** (the server's port, typically 443 for HTTPS)

For example: `92.1.7.3:51823 ⇄ 10.0.0.5:443`. **The kernel uses this tuple to route packets to the right socket** — when a packet arrives, the OS reads the source and destination IPs and ports, looks it up in the [socket-table](socket-table.md), and delivers the packet to the matching socket. From the server's perspective, the tuple reads backwards: `10.0.0.5:443 ⇄ 92.1.7.3:51823`. Both machines hold this identity in their socket; they just swap the sides.

**Why is it unique even for multiple connections?** Here's the trick many people miss. You open two browser tabs to youtube.com — same destination IP and port. But the OS assigns each tab a *different source port*:

- **Tab 1:** `192.168.1.100:54321 → 172.217.0.0:443`
- **Tab 2:** `192.168.1.100:54322 → 172.217.0.0:443`

The destination is identical, but the source ports (54321 vs. 54322) are different — so the 4-tuples are *completely different*. The kernel maintains a separate socket for each one in its connection table. When a response packet arrives from YouTube's server addressed to port 54321, the kernel knows it belongs to Tab 1; port 54322 goes to Tab 2. The OS allocates these **ephemeral ports** (temporary, short-lived port numbers) automatically when you call `connect()` — it just picks an unused port in a range like 49152–65535.

### The matching state at both ends

That's the whole trick: a "connection" is just two computers holding
*matching state* about each other and agreeing to interpret packets in its
light. The server's socket says "I'm connected to 92.1.7.3:51823, I've sent
4021 bytes and acked 4021 bytes from them." The client's socket says the
exact same thing, just from its perspective: "I'm connected to 10.0.0.5:443,
I've received 4021 bytes and will send acks for them." Both sides agree on
what bytes were sent, in what order, and what was acknowledged.

Here's the payoff: the server holding one million connections doesn't need
to know which user owns which socket — it just stores the 4-tuple + state
for each one. When YouTube's server receives a packet from your laptop's
port 54321, it looks it up in its table and finds "this is Tab 1's socket,
Tab 1 sent this." When a packet arrives from your port 54322, it's a
completely different socket — Tab 2's. The beauty is that the server scales
to millions of users not by tracking "user IDs," but by maintaining the
kernel's socket table. Each socket is independent; the server just iterates
over all of them asking "which ones have data to read?" using an event loop
(see [threads-vs-event-loop](threads-vs-event-loop.md)).

The routers in between remember nothing (with one important exception —
your home router's **NAT**, the box that shares one public IP among your
devices, *does* keep a table entry per connection; that matters later). A
connection is a shared belief held in memory at both ends — "logical," not
physical.

## Inside a connection: the RAM picture

Here's what that looks like in practice. The **kernel's socket table in RAM**
(see [socket-table](socket-table.md) for details) is just a lookup table keyed by the 4-tuple.
On one side, the server's RAM holds one entry for this connection:

```
4-tuple: 10.0.0.5:443 ⇄ 92.1.7.3:51823
├── seq sent: 4021, acked: 4021
└── send/recv buffers: 16 KB each
```

On the other side, the client's RAM holds a socket naming the same
connection:

```
4-tuple: 92.1.7.3:51823 ⇄ 10.0.0.5:443
├── seq recv: 4021, next: 4022
└── send/recv buffers: 16 KB each
```

(Notice the flipped direction — each side sees itself first.) The 4-tuples
are matching, and the sequence numbers mean the same thing. When your
YouTube tabs connect from the same machine, the client kernel holds
*multiple* socket entries:

```
4-tuple: 192.168.1.100:54321 ⇄ 172.217.0.0:443  ← Tab 1
4-tuple: 192.168.1.100:54322 ⇄ 172.217.0.0:443  ← Tab 2
4-tuple: 192.168.1.100:54323 ⇄ 172.217.0.0:443  ← Tab 3 (maybe you opened another)
```

Same destination, different source ports. The kernel keeps each separate.

Between them: the internet. Packets carrying data hop through routers. Every
router on the path asks one simple question: *"Where does this packet go?"* —
it reads the destination IP and port, makes a routing decision, and forwards
it. **No router holds any state** about the connection. They have no idea who
you are or whether this packet is part of "your" connection — they are purely
stateless. The connection is remembered only at the two ends. This is why
losing one box in the middle (a crashed router, a cut fiber, a network
reroute) doesn't kill your connection — the two endpoints still remember
each other and can keep talking once a new path forms.

## What one connection costs

Because a connection is memory, its cost is measured in kilobytes, not
megabytes:

- **Kernel socket structure:** a few KB (see [kernel-memory-and-sockets](kernel-memory-and-sockets.md)).
- **Send + receive buffers:** the big variable — see
  [sequence-numbers-and-buffers](sequence-numbers-and-buffers.md).
- **TLS state** (if the connection is encrypted): the session keys and
  encryption buffers, roughly 10–20 KB.
- **Your application's per-connection object:** whatever your code keeps —
  who this user is, a read buffer, a queue of pending notifications.

A tuned idle connection lands around **~10 KB; call it 10–50 KB** with TLS
and application state. So one million idle connections ≈ **10–50 GB of
RAM** — and it must be RAM, because kernel socket memory can't be swapped
to disk. This is why real chat/notification gateways (WhatsApp famously)
push 1–2 million connections per beefy machine: entirely doable, but you
budget for it. Two more per-connection costs to remember: each socket
consumes a **file descriptor** (the OS's numeric handle for an open
resource, capped by a configurable limit — the default is often a comically
low 1,024), and each *client* pays too — a phone keeping its radio awake
for a connection burns battery, which is why the OS maintains **one**
shared push connection (to APNs or FCM, see Lesson 8) instead of one per
app.

The programming model used to be the real bottleneck, not the memory — see
[threads-vs-event-loop](threads-vs-event-loop.md) for the C10K problem and how event loops and
goroutines solved it.

## Connections all the way up the stack

"Connection" means something slightly different at each protocol layer —
TCP, TLS, HTTP/1.1, HTTP/2, WebSocket, SSH, and QUIC all stack or rebuild
the same idea. See [protocol-stack](protocol-stack.md) for the full layer-by-layer
breakdown, and [sockets-vs-connections](sockets-vs-connections.md) for how "socket"
and "connection" relate — including why UDP still uses sockets and how HTTP/2
streams or SSH channels multiplex over just one.

## How connections die

There are exactly three endings: the polite close (**FIN**, sent even on
Ctrl+C or `kill -9`), the slam (**RST**), and **silence** — a half-open
connection where the two ends' beliefs diverge from reality until something
forces a check. See [connection-death-and-detection](connection-death-and-detection.md) for how each plays
out, including why SSH survives a local Ctrl+C but not a closed laptop lid.

## Back to the notification system

Now reread Lesson 1's claim with X-ray vision. "Push requires holding a
connection per client" means: an event-driven gateway server holding ~1
million sockets ≈ tens of GB of RAM, ~33k heartbeats/sec of overhead, and a
worst-case window of one heartbeat interval during which the server pushes
messages to clients that silently died. That last number is why Lesson 10's
pull fallback is not optional, and the question "which of my thousand
gateways holds user X's socket?" is exactly Lesson 9's presence problem.

## Recap

- A connection is **matching state in RAM at both ends** — a shared belief,
  not a reserved wire. Routers in between keep nothing (except NAT).
- Bits reach the wire through encapsulation (TCP → IP → Ethernet/WiFi →
  signal); shared links interleave whole frames rather than colliding, and
  the wire itself drops/corrupts data routinely — TCP's retransmission, not
  the physical layer, is what makes delivery reliable.
  ([physical-layer-and-multiplexing](physical-layer-and-multiplexing.md))
- One idle connection ≈ **10–50 KB** (socket + buffers + TLS + app state);
  a million ≈ tens of GB of unswappable RAM. ([kernel-memory-and-sockets](kernel-memory-and-sockets.md))
- **Thread-per-connection** dies around 10k (C10K); **event loops**
  (epoll — Nginx, Node) and **goroutines** make millions cheap.
  ([threads-vs-event-loop](threads-vs-event-loop.md))
- The stack layers connections on connections: TCP → TLS → HTTP/WebSocket/
  SSH; QUIC rebuilds it all on connectionless UDP. ([protocol-stack](protocol-stack.md))
- Three deaths: **FIN** (polite — sent even on Ctrl+C or `kill -9`),
  **RST** (slam), and **silence** (half-open — detected only by writing,
  a 2-hour TCP keepalive, or the app's ~30 s heartbeat).
  ([connection-death-and-detection](connection-death-and-detection.md))

## Check yourself

1. Your gateway server shows 1M `ESTABLISHED` connections, but only 950k
   users are really online. Where did the other 50k go, and what three
   mechanisms could reveal them?
2. Ctrl+C on a local `curl` informs the server almost instantly, but a
   dead laptop battery leaves the server clueless for seconds-to-hours.
   What's the one-sentence explanation for the difference?
3. Why does an event-driven server pay ~10 KB per idle connection while a
   thread-per-connection server pays ~1 MB?
