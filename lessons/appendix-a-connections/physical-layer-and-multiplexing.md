# The Physical Layer: How Bits Actually Get on the Wire

The rest of this appendix treats a connection as memory — state held in sockets. This file zooms in one level further: what happens the instant a byte leaves your socket's send buffer and has to become an electrical signal, and how that signal shares a wire or a slice of radio spectrum with every other device in your house without the bits getting scrambled together.

## From socket to signal: encapsulation

When your app calls `write()`, the byte doesn't jump straight to the network. It passes through a stack of wrapping steps, each adding its own header:

```
Application data ("Hello")
  └─ TCP header added   → segment  (adds ports, sequence number)
       └─ IP header added   → packet   (adds source/dest IP)
            └─ Ethernet/WiFi header added → frame (adds MAC addresses, CRC checksum)
                 └─ NIC serializes → bits → electrical/light/radio signal
```

Each layer only knows about its own envelope. Ethernet doesn't know what's inside the IP packet; IP doesn't know what's inside the TCP segment. This is why swapping the physical medium (Ethernet cable → WiFi → cellular) mid-journey is a non-event for TCP — the outer wrapping is replaced at each hop, but the TCP segment inside rides along untouched. Only the **NIC (network interface card)** — the hardware that turns frames into actual physical signals — cares about the literal medium.

One more detail worth naming: the link-layer header (MAC address) is addressed to the *next hop only*, e.g. your router — never to the final destination. Every router along the path strips the old link-layer header off, decides the next hop by reading the IP header, and slaps on a *new* link-layer header for the next leg. IP addressing is end-to-end; link-layer addressing is hop-by-hop.

### It's one buffer growing backward, not nested objects

The diagram above looks like nesting — a struct containing a struct containing a struct, each a separate allocation with a pointer to the next. That's not what actually happens. The kernel allocates **one contiguous chunk of memory** (Linux calls it an `sk_buff`, socket buffer) with extra empty space — **headroom** — reserved at the front, before it even knows how big the headers will be. As data descends the stack, each layer writes its header directly into that headroom, immediately in front of what the layer below it already built, and moves the buffer's "start" pointer backward to include it: TCP writes its header first, then IP writes its header in front of TCP's, then Ethernet/WiFi writes its header in front of that. By the end, the buffer looks like `[Ethernet header][IP header][TCP header][your bytes]` — one region of memory, no chained allocations, no pointer-chasing. Each header's byte layout *is* described by a C struct (e.g. `struct iphdr`, `struct tcphdr` — a template for which byte offset means what), but that struct is a lens for reading/writing bytes at a fixed offset within the one shared buffer, not a separately-allocated object.

"NIC serializes → bits" is a distinct, later step done by hardware, not the kernel. Once the buffer (now a complete frame) is ready, the kernel hands it to the NIC — often via **DMA** (direct memory access), letting the NIC read straight out of RAM without the CPU copying it byte by byte. The NIC's **PHY** (physical-layer chip) reads the buffer's bytes in order and converts each one into a sequence of physical signal changes — voltage transitions on copper, light pulses on fiber, radio-wave patterns on WiFi — using an agreed encoding scheme (Ethernet has historically used Manchester encoding or 4B/5B; WiFi uses OFDM). This is the one place in the whole pipeline where "bit by bit, over time" is literally true, rather than just a conceptual layering.

## Multiple devices, one link: how they don't collide

This is the part that looks like it should be a problem — five devices in a house, all "constantly sending data" — but the collision is avoided differently depending on the medium:

- **Wired Ethernet to a switch:** each device gets its own dedicated, full-duplex cable to a switch port. Nothing is shared *on that segment* — your laptop's cable is physically yours alone. The switch receives frames from every port and queues them internally; if two frames need to go out the same port at once (e.g., both to your router), one waits in a microsecond-scale buffer. No bits ever collide — a frame is either transmitted whole or briefly delayed, never interleaved with another frame mid-stream.
- **WiFi:** this is a genuinely shared medium — every device on the network is transmitting into the same air. It uses **CSMA/CA** (listen before you talk, and back off randomly if the channel's busy) to take turns. At human timescales this looks simultaneous; at the microsecond level, devices are serialized onto the channel one frame at a time.

Either way, the result is the same principle the main lesson opens with: nothing is reserved. Frames from different devices **interleave**, whole-frame-at-a-time, on any shared link — this is statistical multiplexing happening one hop from your laptop, not just out on the wider internet.

## Getting past the router: NAT reuses one public identity

Your home router's **NAT** (see [lesson.md](lesson.md)'s "one important exception") is what lets all these devices share one public IP without their traffic being confused for each other:

1. Your laptop sends a packet with source `192.168.1.50:54321`.
2. The router rewrites the source to its own public IP and a new port, e.g. `73.22.1.9:61000`, and records that translation in a table.
3. The response comes back addressed to `73.22.1.9:61000`; the router looks up its table, rewrites the destination back to `192.168.1.50:54321`, and forwards it inward.

Past the router, it's ordinary stateless internet routing — every router in between reads the destination IP, makes a forwarding decision, and forgets the packet, exactly as [lesson.md](lesson.md) describes.

## Reliability is not a property of the wire

Here's the piece that resolves "how do bits travel without losing data": **they don't, reliably, at this layer.** The physical/link layer makes no delivery guarantee — WiFi interference, a marginal cable, or a congested switch buffer can and do drop or corrupt frames.

Two independent mechanisms handle this, at two different layers:

- **CRC checksum** (link layer): every Ethernet/WiFi frame carries a checksum. If a frame arrives corrupted, the receiving NIC just silently discards it — no retry happens at this layer.
- **TCP** (transport layer): this is the actual guarantee. TCP tracks sequence numbers (the "seq sent: 4021, acked: 4021" state from the socket in the main lesson), and if an ACK doesn't arrive within a timeout, it retransmits the segment.

So "reliable delivery" isn't a wire property — it's an illusion manufactured by TCP noticing gaps and re-sending, layered on top of a physical medium that drops things routinely. This is the same idea the main lesson makes about connections in general: the guarantee lives in state at the endpoints, not in anything physical in between.

## See also

- [lesson.md](lesson.md) — the packet-switched, stateless-routers framing this file zooms into
- [protocol-stack](protocol-stack.md) — how TCP/TLS/HTTP layer on top of what this file describes
- [sequence-numbers-and-buffers](sequence-numbers-and-buffers.md) — the seq/ack state that turns unreliable frames into reliable delivery
