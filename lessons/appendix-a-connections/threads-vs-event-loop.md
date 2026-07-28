# Threads vs. Event Loops: The C10K Problem

Memory per socket was never the historical bottleneck — the programming
model was. The obvious design is **thread-per-connection**: each connection
gets its own thread (an independent line of execution inside a process)
that sleeps until data arrives. Threads are expensive — a default stack is
~1 MB (Java, pthreads), and the OS burns CPU **context-switching** (saving
one thread's state and loading another's) between thousands of them. At
10,000 connections this design collapses; the industry called it the
**C10K problem** ("how do you handle ten thousand concurrent connections?").

The answer that won is **event-driven** I/O: *one* thread asks the kernel
"tell me which of my 100,000 sockets have something to read" using an API
like Linux's **epoll**, then handles the ready ones in a loop — the
**event loop**. No sleeping threads, no stacks per connection; cost per
idle connection drops to just its memory. This is the engine inside Nginx,
Node.js, and Netty. Go's **goroutines** are a comfortable middle path: they
*look* like thread-per-connection but each starts with a ~4 KB growable
stack, and the runtime multiplexes millions of them onto a handful of real
threads using epoll underneath.

One more cost: idle connections aren't free even when idle. Both sides send
periodic **heartbeats** (tiny "still there?" messages) — partly to detect
death (see [connection-death-and-detection](connection-death-and-detection.md)), partly because a NAT
table entry in a home router gets deleted after a few idle minutes,
silently black-holing the connection. A million connections heartbeating
every 30 seconds is ~33,000 messages per second of pure overhead the
server must absorb.

## See also

- [kernel-memory-and-sockets](kernel-memory-and-sockets.md) — the per-socket RAM cost this scaling model has to carry
- [connection-death-and-detection](connection-death-and-detection.md) — why heartbeats exist beyond just NAT timeouts
