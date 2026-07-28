# Sockets vs. Connections: Untangling the Terms

## The confusion this file clears up

"Socket" and "connection" get used almost interchangeably, but they're not
the same thing, and the mismatch causes real confusion once TCP, UDP,
multiplexed protocols, and non-network "connections" (USB, Bluetooth) all
enter the picture. This file is the map.

## A socket is the OS's endpoint abstraction — for both TCP and UDP

A **socket** is a kernel data structure (the kernel is the core of the
operating system) that represents one endpoint of network communication. It
is created via the OS's `socket()` system call and, once bound or connected,
is identified by the 4-tuple: source IP, source port, destination IP,
destination port (see the main [lesson.md](lesson.md) for the full
breakdown).

The easy mistake is thinking "socket" means "TCP connection." It doesn't —
**both TCP and UDP use sockets.** The real difference is how much state each
kind of socket carries:

- **TCP socket** — rich state. Before any data flows, both ends do a
  three-message handshake, then the socket tracks sequence numbers (which
  bytes have been sent and acknowledged), retransmission timers, and
  send/receive buffers. This bookkeeping is what makes TCP *reliable*: lost
  or out-of-order packets get detected and retried.
- **UDP socket** — thin state. UDP is *connectionless*: no handshake, no
  sequence numbers, no acknowledgments, no retries. A UDP socket is closer
  to a mailbox — "I'm bound to this local port, hand me any datagram
  addressed here" — than a tracked, ongoing conversation. UDP is used where
  speed beats guaranteed delivery: DNS lookups, video/voice calls.

So "connectionless" describes the *absence of handshake and ordering
guarantees*, not the absence of a socket. A UDP socket is still a socket.

## One socket can carry many logical "connections"

This is where people most often get tripped up, because plenty of things
casually called "a connection" are not 1:1 with sockets:

- **HTTP/2 streams** — dozens of parallel request/response streams
  multiplexed over a single TCP socket.
- **SSH channels** — your shell session, a port-forward, and a file copy can
  all run as independent multiplexed channels over one TCP socket, tracked
  by SSH's own channel-numbering, not by the kernel.
- **WebSocket** — a single upgraded TCP socket carrying a free-form stream
  of messages in both directions.

In all three cases, the kernel sees exactly **one socket** with **one
4-tuple**. The multiplexing — keeping several logical conversations apart —
happens in the application protocol's own bookkeeping (stream IDs, channel
numbers), layered on top of that one socket. So "I have 5 SSH connections to
this server" (5 terminal tabs in one login session) can mean 1 socket, not
5 — check whether it's 5 separate logins (5 sockets) or 5 channels inside
one login (1 socket).

## What genuinely doesn't open a socket

Within IP networking, nothing skips the socket abstraction — TCP, UDP, and
even raw protocols like ICMP (what `ping` uses) all go through
`socket()`. The real exception is **non-IP "connections"**: a USB cable, a
Bluetooth pairing, a serial port. People call these "connections" too, but
they never enter the TCP/IP stack — no IP address, no `socket()` call — so
the OS represents them with an entirely different kind of handle (a device
file, a Bluetooth-stack object), because "socket" specifically names the
IP-networking endpoint abstraction.

## QUIC: rebuilding TCP's guarantees without a TCP socket

One more twist, because it proves the whole point of this appendix. **QUIC**
(which powers HTTP/3) runs on top of a **UDP** socket — the OS only sees
UDP, thin state, no kernel-tracked handshake. But the QUIC library rebuilds
TCP's ideas — ordered streams, reliable delivery, encryption — itself, in
user space, above that UDP socket. The kernel's socket doesn't hold any of
that richer state; QUIC's own code does. This is the clearest proof that "a
connection is just state and rules" (the main lesson's core claim,
paraphrased here) — you can build TCP-grade guarantees on a transport (UDP)
that has none built in, as long as *something* tracks the state; it doesn't
have to be the kernel.

## Recap

- A **socket** is the OS's endpoint abstraction — TCP *and* UDP both use it.
  "Connectionless" (UDP) means no handshake/ordering, not no socket.
- **TCP sockets** carry rich state (handshake, sequence numbers, buffers);
  **UDP sockets** are thin (just a bound local port).
- **Multiplexed logical connections** (HTTP/2 streams, SSH channels,
  WebSocket messages) share **one** underlying socket — the kernel only
  sees one 4-tuple; the application protocol does its own bookkeeping on
  top.
- **Non-IP "connections"** (USB, Bluetooth, serial) never create a socket —
  they're outside the TCP/IP stack entirely.
- **QUIC/HTTP-3** rebuilds TCP-like reliability on top of a plain UDP
  socket, in the QUIC library itself rather than in the kernel — proof that
  the guarantees are just state and rules, not a property of the socket.

## See also

- [protocol-stack](protocol-stack.md) — how TCP, TLS, HTTP/1.1, HTTP/2,
  WebSocket, SSH, and QUIC stack or rebuild the connection idea
- [socket-table](socket-table.md) — how the kernel finds a socket from an
  incoming packet's 4-tuple
- `qa.md` in this folder — the original Q&A this file was distilled from
