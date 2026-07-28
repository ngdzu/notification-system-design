# The Socket Table: How the Kernel Finds Your Connection

## What is the socket table?

The **socket table** is the kernel's index for finding sockets. It's a data structure (typically a hash table) that maps **4-tuples to socket objects**.

When a packet arrives at your machine:
1. The kernel reads the packet's source and destination IPs and ports (the 4-tuple)
2. The kernel looks up the 4-tuple in the socket table
3. The lookup returns a pointer to the matching socket object
4. The packet is delivered to that socket

```
Packet arrives: src=92.1.7.3:51823, dst=10.0.0.5:443

Socket table lookup:
┌──────────────────────────────────────────────────────┐
│ 4-tuple: 10.0.0.5:443 ⇄ 92.1.7.3:51823  →  Socket #47 │
│ 4-tuple: 10.0.0.5:443 ⇄ 92.1.7.3:51824  →  Socket #48 │
│ 4-tuple: 10.0.0.5:443 ⇄ 92.1.7.3:51825  →  Socket #49 │
└──────────────────────────────────────────────────────┘

Deliver to Socket #47
```

## Why 4-tuple and not just IP?

The 4-tuple is necessary because multiple sockets can exist between the same pair of machines. When you open two browser tabs to the same server:

```
Browser tab 1: 192.168.1.100:54321 → 172.217.0.0:443  (Socket #1)
Browser tab 2: 192.168.1.100:54322 → 172.217.0.0:443  (Socket #2)
Browser tab 3: 192.168.1.100:54323 → 172.217.0.0:443  (Socket #3)
```

Same destination IP and port, but different source ports. The 4-tuple uniquely identifies each connection. Without it, the kernel wouldn't know which tab's data belongs to which socket.

## Socket table initialization

When the kernel boots, it initializes an empty socket table. The table is:
- **Persistent** — it exists for the entire lifetime of the OS
- **Dynamic** — it grows and shrinks as connections are made and closed
- **Efficient** — usually implemented as a hash table for O(1) lookup, or a tree for ordered iteration

As connections are made:
```
Boot:        socket table = {}
connect():   socket table = {4-tuple #1 → Socket #1}
connect():   socket table = {4-tuple #1 → Socket #1, 4-tuple #2 → Socket #2}
connect():   socket table = {4-tuple #1 → Socket #1, 4-tuple #2 → Socket #2, 4-tuple #3 → Socket #3}
close():     socket table = {4-tuple #2 → Socket #2, 4-tuple #3 → Socket #3}  ← entry #1 removed
```

## Lookup speed matters

The socket table must be fast — incoming packets arrive at line-rate (millions per second). A slow lookup would become the bottleneck. Hash tables provide O(1) average-case lookup, making them ideal.

For a busy server with 1 million active connections, the kernel is performing millions of socket table lookups per second, each one in constant time.

## See also

- [kernel-memory-and-sockets](kernel-memory-and-sockets.md) — where sockets live in RAM
- [sequence-numbers-and-buffers](sequence-numbers-and-buffers.md) — the state stored inside each socket this table points to
