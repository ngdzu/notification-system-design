# Kernel Memory and Socket Allocation

## RAM regions: kernel space vs. user space

All RAM on your machine is divided into two protected regions:

```
┌─────────────────────────────────────────┐
│  Kernel Memory Space (protected)        │
│  ├── Socket table (indexes all sockets) │
│  ├── Socket objects (your connections)  │
│  ├── Device drivers                     │
│  ├── Interrupt handlers                 │
│  └── Other kernel data structures       │
├─────────────────────────────────────────┤
│  User Space Memory                      │
│  ├── Your browser process               │
│  ├── Server application                 │
│  ├── Web server (Nginx, Node.js)        │
│  └── Your program's heap/stack          │
└─────────────────────────────────────────┘
```

**Kernel space** is protected — user programs cannot read or write it directly. This is a CPU-enforced boundary that prevents bugs in one program from corrupting kernel data or another program's memory.

## Where sockets live

Sockets are **kernel data structures**. They live entirely in kernel memory space. When you call `connect()` from your browser or server application, the kernel:

1. Allocates memory for a socket object in kernel space
2. Initializes the socket with the 4-tuple, sequence numbers, buffers
3. Adds an entry to the socket table pointing to it
4. Returns a file descriptor (a small integer) to your application

Your application never sees the actual socket object. It only gets a **file descriptor** — like `3` or `42` — which is just a handle. When you read or write to a socket, you pass that file descriptor to the kernel, and the kernel looks it up in the socket table to find the real socket.

Example:
```c
// In your browser or server code
int fd = connect(server_address);  // kernel returns 42
write(fd, "Hello", 5);              // kernel translates 42 → actual socket
```

## Socket allocation: dynamic and efficient

When your machine boots, the kernel initializes an empty **socket table** (a hash table or tree structure). It does NOT pre-allocate millions of socket objects ahead of time.

Instead, when a connection is made:
1. Kernel allocates a socket object (often using a **slab allocator** — a memory pool designed for fast allocation of fixed-size objects)
2. Kernel adds an entry to the socket table
3. Later, when the connection closes, the kernel frees the socket and removes the table entry

This is why **connection count is directly tied to RAM usage**. Each socket consumes ~10–50 KB in kernel memory. One million connections = one million socket objects in kernel space, consuming 10–50 GB of unswappable kernel RAM.

## Why "can't swap to disk"?

You may hear "kernel socket memory cannot be swapped to disk." Here's why:

- Swapping means moving inactive memory pages to disk to make room for active data
- But sockets are **always active** — a packet can arrive at any moment, and the kernel must instantly look up the socket in its table
- If a socket were swapped to disk, the kernel would have to wait for a disk read just to deliver an incoming packet — destroying latency and throughput
- So the OS simply **forbids swapping** kernel data structures like sockets

This is why you budget RAM carefully for connection-heavy servers like chat gateways and notification systems.

## See also

- [socket-table](socket-table.md) — how the kernel indexes all sockets by 4-tuple
- [sequence-numbers-and-buffers](sequence-numbers-and-buffers.md) — the per-connection state stored inside each socket
- [connection-death-and-detection](connection-death-and-detection.md) — what happens during connect/close
