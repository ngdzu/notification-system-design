# Connections All the Way Up the Stack

"Connection" means something slightly different at each protocol layer, and
the layers stack:

- **UDP** — the *connectionless* transport: fire-and-forget packets, no
  handshake, no state, no delivery guarantee. Used for DNS, video calls.
- **TCP** — the connection described in the main appendix: handshake,
  ordering, retries.
- **TLS** — encryption layered *on top of* TCP. A "secure connection" is a
  TCP connection plus an extra handshake where both sides agree on secret
  keys; those keys are more per-connection state.
- **HTTP/1.1** — request/response on top of TCP/TLS. **Keep-alive** reuses
  one TCP connection for many requests to avoid re-handshaking.
- **HTTP/2** — multiplexes many parallel request **streams** over one TCP
  connection.
- **WebSocket** — starts as an HTTP request, then **upgrades** the same TCP
  connection into a free-form two-way pipe. This is the main push channel
  in Lesson 9.
- **SSH** — its own encrypted protocol on TCP; one connection carries
  multiplexed channels (your shell, port forwards, file copies).
- **QUIC / HTTP/3** — rebuilds TCP's ideas (streams, reliability,
  encryption) *on top of UDP*, proving the point: a connection is just
  state and rules, so you can build one on anything.

## See also

- [sockets-vs-connections](sockets-vs-connections.md) — why UDP still uses sockets, how HTTP/2 streams and SSH channels multiplex over one socket, and what genuinely doesn't use a socket at all
- [connection-death-and-detection](connection-death-and-detection.md) — how the "goodbye" (or lack of one) plays out for TCP-based connections in this stack
