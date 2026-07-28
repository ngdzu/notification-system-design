# How Connections Die

There are exactly three endings, and which one you get depends on whether a
"goodbye" packet makes it out.

**1. The polite close (FIN).** When a program calls `close()` — or simply
exits — the kernel sends a **FIN** packet ("I'm done sending"), the peer
acknowledges and sends its own FIN back. Both sides free their state.
Crucially, this happens even for rude exits: press **Ctrl+C on `curl`** and
the process dies of a SIGINT, but the *kernel* outlives it, notices the
orphaned socket, and still sends the FIN. Even `kill -9` — as long as the
operating system itself survives, the other side gets told promptly.

**2. The slam (RST).** A **RST** ("reset") packet means "no such
connection — stop immediately." You get one when you connect to a port
nobody's listening on, when a peer crashes and receives packets for a
connection it no longer remembers, or when a load balancer kills a
connection that sat idle past its timeout. Abrupt, but at least it's
*information*: the other side finds out.

**3. Silence.** Pull the Ethernet cable. Battery dies. Laptop lid closes.
Phone enters a subway tunnel. Kernel panic. In all of these, **no packet is
sent at all** — and the server's socket just sits there in `ESTABLISHED`
state, buffers allocated, believing in a peer that no longer exists. This
is a **half-open connection**: the two ends' beliefs have diverged from
reality. The server discovers the truth only when something forces a check:

- **It tries to write** — retransmissions go unanswered and the connection
  errors out after *minutes* of retries.
- **TCP keepalive** — an optional kernel-level probe, but its default is
  absurd for real-time systems: **two hours** on Linux.
- **Application heartbeat** — the ping the app itself sends every ~30
  seconds. This is the only detection mechanism fast enough for a push
  system, and it's why every real one has heartbeats (see
  [threads-vs-event-loop](threads-vs-event-loop.md) for the overhead cost of running them at scale).

The **SSH Ctrl+C twist** ties it together. Inside an SSH session, Ctrl+C
does *not* kill your connection: your terminal sends the Ctrl+C *character
over the connection* to the remote shell, which kills the remote program —
the connection itself stays healthy. But close your laptop lid mid-session
(silence!) and the remote shell lives on, orphaned, until the server's
sshd heartbeats fail — which is exactly why tools like `tmux` exist to
keep remote sessions adoptable after your connection dies.

## See also

- [threads-vs-event-loop](threads-vs-event-loop.md) — why heartbeats cost real CPU/network overhead at scale
- [protocol-stack](protocol-stack.md) — where FIN/RST live (TCP) versus the layers built on top of it
