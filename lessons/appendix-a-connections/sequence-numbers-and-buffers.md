# Sequence Numbers and Buffers: Tracking Bytes in Flight

## Sequence numbers: tracking what bytes were sent

TCP is a **reliable ordered stream**: if you send "HELLO" followed by
"WORLD," the receiver gets exactly that, in order, even if packets arrive out
of sequence or some packets are lost and retransmitted. This is guaranteed by
**sequence numbers** — counters that mark every byte sent.

- **seq sent**: the byte count of data the machine has sent (and will start
  retransmitting from if a packet is lost).
- **acked** (acknowledged): the byte count of data the machine *knows* the
  other side received safely. When the peer sends an acknowledgment, this
  number moves forward.
- **seq recv / next**: from the receiver's perspective, the byte count of
  data it has received in order, and the sequence number of the next byte it
  expects.

Example: if the server sends "HELLO" (5 bytes) starting at seq 4000, it marks
seq 4000–4004 as sent. When the client acknowledges receipt, it says "acked
up to 4004" — meaning "I got everything through byte 4004." The server can
now discard those bytes from its send buffer and move on. If a retransmit is
needed, the server knows exactly where it left off.

## Send and receive buffers: holding bytes in transit

Packets don't carry all your data at once. If you send 1 MB to a server,
TCP breaks it into many packets (typically ~1.4 KB each). Until the
application on the far side is ready to read, bytes sit in a **receive
buffer** — a chunk of kernel memory (often ~16 KB by default, tunable).
Similarly, if you write data faster than the network can send it, bytes
accumulate in the **send buffer** waiting to be packetized and shipped.

These buffers are the only RAM the connection truly *needs* to hold in
flight data. The bigger the buffers, the more data can flow without the
sender waiting for acknowledgments — but bigger means less memory for other
connections. High-performance servers tune these down for idle connections
(a few KB) and let them grow only when data actually flows.

## See also

- [kernel-memory-and-sockets](kernel-memory-and-sockets.md) — where the socket holding these buffers lives in RAM
- [socket-table](socket-table.md) — how the kernel finds the socket these buffers belong to
