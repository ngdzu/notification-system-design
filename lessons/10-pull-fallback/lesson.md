# Lesson 10 — Pull Fallback: The Backup Plan When Push Fails

## Why this matters

Push delivery is fast, but it is never 100% reliable. Phones go into
airplane mode. WebSocket connections drop when someone walks through a
tunnel. APNs and FCM tokens expire when a user reinstalls an app. If push
is your only delivery path, every one of those situations means a lost
notification — and lost notifications erode trust. The solution every
large-scale system uses is a **pull fallback**: when the client comes back
online or the user opens the app, the client asks the server "what did I
miss?" This lesson covers exactly how that catch-up works, how you compute
the little red number on the app icon, and how you let users scroll back
through their notification history without the results shifting under them.

## Sync-on-reconnect: catching up after going dark

**Sync-on-reconnect** is the pattern where a client, immediately after
regaining connectivity or opening the app, calls an API to fetch every
notification it missed while it was away.

Here is the analogy: imagine you leave a meeting early. When you come back,
you don't ask the room to replay the entire meeting — you ask "what
happened since I left?" That is exactly what sync-on-reconnect does. The
client sends the server a timestamp or token representing the last
notification it successfully received, and the server returns everything
newer than that.

A typical API call looks like this:

```
GET /v1/notifications?since=<last-seen-id>&limit=50
```

The server queries the notification store for all rows belonging to this
user that were created after `last-seen-id`, ordered by time, and returns
the first 50. If there are more than 50, the response includes a cursor
(more on cursors below) so the client can page through the rest.

### When does sync-on-reconnect fire?

Three common triggers:

1. **App open (cold start).** The user taps the app icon. The client has no
   active connection, so it pulls immediately.
2. **Reconnect after network loss.** The WebSocket or long-poll connection
   drops and re-establishes. On reconnect, the client pulls to cover the
   gap.
3. **Background wake.** On mobile, the OS periodically wakes the app for a
   few seconds. The app can use that window to sync.

In all three cases the logic is the same: send the last-seen marker, get
back what you missed.

### Why not just re-push everything?

You could, in theory, have the server re-push every missed notification the
moment the client reconnects. The problem is volume: if a user was offline
for a day and received 200 notifications, re-pushing all 200 over the
push channel would jam the connection and delay new, time-sensitive
notifications. Pull lets the client fetch missed items at its own pace, in
batches, without blocking the push path.

## Badge count: the little red number

The **badge count** is the number displayed on an app icon (or a tab, or a
bell icon in a web app) showing how many unread notifications exist. It
looks simple — just a number — but computing it at scale has a few
subtleties.

The badge count is not "how many notifications arrived while you were
away." It is "how many notifications you have never marked as read,"
regardless of when they arrived. That means the server needs to track a
read/unread state for each notification per user. In practice most systems
maintain a counter rather than scanning every notification row:

- When a new notification is created for a user, increment the counter.
- When the user reads a notification (taps it, opens the detail), decrement
  the counter.
- When the user taps "mark all as read," reset the counter to zero.

This counter lives in a fast store — often Redis or Memcached — because
clients query it frequently (every app open, every pull request) and it
must respond in single-digit milliseconds.

### Badge count in the pull response

A well-designed pull API returns the badge count alongside the list of
notifications:

```json
{
  "notifications": [ ... ],
  "unread_count": 12,
  "next_cursor": "eyJpZCI6MTAwMH0="
}
```

This saves the client a separate round-trip just to update the badge.

## Cursor-based pagination: scrolling through history safely

Users sometimes want to scroll back through old notifications — "show me
everything from last week." The notification list can be long, so you need
pagination: return results in pages rather than all at once.

The naive approach is **offset-based pagination**: "give me page 2, where
each page is 50 items" (`?page=2&limit=50`, meaning skip the first 50
rows). This works fine for static data, but notification lists are not
static. New notifications arrive constantly. If a new notification lands
between your page-1 request and your page-2 request, every item shifts
down by one — and you either see a duplicate or skip an item entirely.

**Cursor-based pagination** solves this. Instead of saying "skip N rows,"
the client says "give me the next 50 items after this specific point." The
cursor is an opaque string — the client does not parse it or construct it;
it just passes back whatever the server gave it. Under the hood, the cursor
typically encodes the sort key of the last item returned (for example, a
base64-encoded notification ID or timestamp).

Here is the analogy: imagine reading a long book with no page numbers. You
could say "start at page 40" (offset-based), but if someone rips out a page
near the beginning, page 40 now points to the wrong place. Instead, you
use a bookmark: "continue right after the paragraph that starts with these
words." No matter how many pages are added or removed before your bookmark,
you pick up exactly where you left off.

### How it works in practice

1. Client requests the first page: `GET /v1/notifications?limit=50`
2. Server returns 50 items plus `"next_cursor": "abc123"`.
3. Client requests the next page: `GET /v1/notifications?limit=50&cursor=abc123`
4. Server decodes `abc123`, finds the item it points to, and returns the
   next 50 items after that item.
5. When there are no more items, the server omits `next_cursor` (or returns
   null), and the client knows it has reached the end.

Because the cursor points to a specific item rather than a numeric
position, new inserts at the top of the list do not affect pages you have
already fetched or are about to fetch.

### Trade-offs

Cursor-based pagination does not support "jump to page 7" — you can only
go forward (or backward, with a previous-cursor). For notification
history this is fine because users scroll sequentially, but it would be
awkward for a UI that needs random-access page jumps.

## How pull fallback fits the architecture

In the broader notification system (Lessons 2 and 8), push and pull are
two parallel paths:

- **Push path:** Event arrives → fanout → delivery service → push channel
  (APNs/FCM/WebSocket) → client.
- **Pull path:** Client opens or reconnects → calls pull API → API queries
  notification store → returns missed notifications + badge count.

Both paths read from the same notification store. The push path writes to
it ("notification created"), and the pull path reads from it ("give me
everything since X"). This shared store is why you never lose a
notification even if push fails — the data is always there, waiting for
the client to ask.

## Recap

- **Sync-on-reconnect** is the client asking "what did I miss?" every time
  it comes back online or the app opens. It sends a last-seen marker and
  gets back everything newer.
- **Badge count** is the total unread count per user, maintained as an
  incrementing/decrementing counter in a fast cache, returned alongside
  pull responses.
- **Cursor-based pagination** uses an opaque pointer to a specific item
  instead of a numeric offset, so new data arriving at the top of the list
  does not cause duplicates or skipped items.
- Push and pull read from the same notification store. Push is the fast
  path; pull is the reliable path. Together they form a hybrid that is both
  fast and complete.

## Check yourself

1. A user's phone was in airplane mode for six hours. When they turn it
   back on, how does the app know which notifications to fetch — and why is
   pulling them better than having the server re-push all of them?

2. You are paginating a notification list using offsets (`?page=3&limit=20`).
   Between your page-2 and page-3 requests, five new notifications arrive.
   What goes wrong, and how does cursor-based pagination prevent it?
