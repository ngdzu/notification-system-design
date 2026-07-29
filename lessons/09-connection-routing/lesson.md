# Lesson 9 — Connection Routing: Who's Connected to Which Server?

## Why this matters

Your notification system can compose the perfect message, prioritize it
correctly, and hand it off to the right channel — but for in-app real-time
delivery, there's still one huge question left: *which server is this user
connected to right now?* With 100 million users online and thousands of
servers handling connections, you can't just broadcast every notification to
every server and hope for the best. You need a routing layer that knows
exactly where each user's connection lives.

## Three ways to hold a connection open

Before we can route, we need to understand how a user stays connected to a
server in the first place. There are three common techniques.

**WebSocket** is a protocol that upgrades an ordinary HTTP request into a
persistent, two-way channel between client and server. Once the upgrade
handshake finishes, both sides can send messages at any time — no waiting for
the other side to ask first. Think of it like a phone call: once you dial in,
either person can talk whenever they want. WebSocket is the gold standard for
real-time features because it's low-latency and bidirectional.

**Long polling** is a workaround for environments where WebSocket isn't
available. The client sends a regular HTTP request, but instead of responding
immediately, the server *holds the request open* until it has something to
deliver (or a timeout expires). When the response finally arrives, the client
immediately sends a new request, and the cycle repeats. It's like raising
your hand in class and waiting patiently until the teacher has an answer —
then raising your hand again. Long polling works everywhere HTTP works, but
it's less efficient: each cycle requires a new HTTP request with full
headers, and there's a small gap between responses where messages can queue
up.

**Server-Sent Events (SSE)** is a middle ground. The client opens a single
HTTP connection, and the server pushes messages down that connection whenever
it wants — but only server-to-client, not the other way. Think of it like a
radio broadcast: the station talks, you listen, you can't talk back over the
same channel. SSE is simpler to set up than WebSocket (it's just HTTP with a
special content type) and handles reconnection automatically, but the
one-way nature means the client must use a separate request if it needs to
send data back.

| Technique | Direction | Connection | Best for |
|---|---|---|---|
| WebSocket | Two-way | Single persistent TCP | Chat, gaming, any high-frequency back-and-forth |
| Long polling | One-way (simulated) | Repeated HTTP requests | Fallback when WebSocket is blocked |
| SSE | Server → client only | Single persistent HTTP | Notification feeds, dashboards, live scores |

In practice, most large notification systems default to WebSocket and fall
back to long polling for clients that can't upgrade.

## The routing problem

Regardless of which technique you pick, the result is the same: each user
has a persistent connection to *one specific server*. That server is called a
**gateway server** — its job is to hold open connections from clients and
forward messages to them. A gateway server does little business logic; it's
basically a switchboard.

Now imagine you have 2,000 gateway servers, each holding 50,000 connections.
A notification for user Alice arrives at a back-end worker. Which of those
2,000 servers is Alice connected to? The worker has no idea — unless
something tells it.

## The presence service

The solution is a **presence service**: a centralized lookup registry that
maps each connected user to the gateway server holding their connection. When
Alice opens the app and her WebSocket connects to gateway server G-417, that
server registers the mapping `alice → G-417` in the presence service. When
Alice disconnects (closes the app, loses network), the gateway removes the
entry.

The presence service is typically backed by an in-memory store like Redis
because lookups need to be fast (sub-millisecond) and the data is ephemeral —
if a gateway crashes, all its entries are stale and should expire anyway.

The flow looks like this:

1. Back-end worker says: "Deliver notification X to Alice."
2. Worker queries the presence service: "Where is Alice?"
3. Presence service replies: "Alice is on G-417."
4. Worker sends the notification payload to G-417.
5. G-417 pushes the message down Alice's open WebSocket.

If the presence service says Alice is not connected at all, the system falls
back to offline delivery (push notification via APNs/FCM, email, SMS —
whichever channel is appropriate).

## Sticky sessions

There's a related concept called a **sticky session** (sometimes called
session affinity). A sticky session is a load-balancer rule that pins a
user's requests to the same back-end server for the lifetime of a connection.
Without it, a load balancer might round-robin the user's WebSocket upgrade
request to server A, then route a later HTTP request to server B, which knows
nothing about the WebSocket.

Sticky sessions are usually implemented by hashing the user's ID or IP to
select a server, or by setting a cookie that the load balancer inspects.
They're simple but come with a trade-off: if the pinned server goes down, the
user must reconnect and get re-assigned. Sticky sessions also make it harder
to distribute load evenly — one popular user won't move to a less-loaded
server just because its current server is busy. For this reason, most
large-scale systems combine sticky sessions (for the connection layer) with
the presence service (for routing notifications from the back end).

## How this fits the bigger picture

In earlier lessons we covered message brokers, fanout strategies, and push
delivery mechanics. Connection routing is the last link in that chain for
real-time in-app delivery. The fanout system decides *who* gets the
notification, the message broker *queues* it, and the presence service +
gateway servers figure out *where to push it right now*. Without this routing
layer, every notification would require either broadcasting to all servers
(wasteful) or giving up on real-time delivery entirely.

## Recap

- **WebSocket**, **long polling**, and **SSE** are three techniques for
  maintaining persistent connections between clients and servers.
- Persistent connections create a routing problem: you must know which
  **gateway server** holds a given user's connection.
- A **presence service** is an in-memory registry mapping user → gateway
  server, updated on connect and disconnect.
- **Sticky sessions** pin a user to one server via load-balancer rules,
  simplifying connection management but trading off flexibility.
- The combination of presence service + gateway servers is how large-scale
  systems route real-time notifications to the correct connection.

## Check yourself

1. A user's WebSocket is connected to gateway server G-200, but that server
   crashes. What happens to the user's entry in the presence service, and how
   does the system recover?

2. Your system supports 100 million concurrent users across 2,000 gateway
   servers. Why would broadcasting every notification to all 2,000 servers be
   problematic, and how does the presence service solve this?
