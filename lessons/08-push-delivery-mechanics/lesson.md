# Lesson 8 — Push Delivery Mechanics: APNs, FCM, and Device Tokens

## Why this matters

You might assume that "sending a push notification" means your server opens a
connection to a user's phone and delivers a message. It doesn't work that way.
You can't reach a phone directly — mobile networks, battery optimization, and
OS security all stand in the way. Instead, every push notification you've ever
received on a phone was routed through a middleman operated by the device's OS
vendor. Understanding how that relay works — and the constraints it imposes —
is essential before you can design a delivery pipeline that actually reaches
100M+ devices.

## The push notification service: your mandatory middleman

A **push notification service** (PNS) is a cloud service run by the OS vendor
that acts as the sole gateway for delivering push notifications to devices
running that OS. Apple runs **APNs** (Apple Push Notification service) for iOS
and macOS. Google runs **FCM** (Firebase Cloud Messaging) for Android. There
is no way around them — the operating system will not let a third-party server
wake up an app or show a banner without going through its PNS.

Think of it like sending mail through the postal service. You can't walk up to
someone's front door in a gated community and slide a letter under it — you
hand the letter to the postal service, and they deliver it. APNs and FCM are
that postal service. Your server talks to them over an API, and they handle
the last hop to the device.

Why do OS vendors force this? Two main reasons:

1. **Battery life.** If every app maintained its own persistent connection to
   its own server, the radio would never sleep and the battery would drain in
   hours. Instead, the OS keeps one single persistent connection to its PNS.
   All apps share that connection.
2. **Security and control.** The OS can enforce permission rules (the user
   said "no notifications for this app"), rate limits, and payload
   restrictions before anything reaches the screen.

## Device tokens: addressing a specific app on a specific phone

When your app is installed and the user grants notification permission, the
app registers with the PNS. The PNS returns a **device token** — a long,
opaque string (typically 64–256 characters) that uniquely identifies *this
app install on this device*. It is not a phone number, not a user ID, not a
device ID. It is specific to the combination of one app and one device.

Key properties of device tokens:

- **One token per app per device.** If a user installs your app on a phone
  and a tablet, you get two different tokens.
- **Tokens can change.** The OS can rotate a device token at any time — after
  an OS update, after restoring from backup, or just periodically. Your
  server must always accept fresh tokens from the app and update its records.
- **Tokens expire or become invalid.** If a user uninstalls the app, the
  token is dead. APNs and FCM will tell you (via error responses or a
  feedback service) when a token is no longer valid. You must stop sending
  to dead tokens, or the PNS may throttle you.
- **Tokens are platform-specific.** An APNs token only works with APNs; an
  FCM token only works with FCM. Your server needs to know which PNS to call
  for each token.

In practice, your backend stores a mapping of `user_id -> [list of device
tokens]`, each tagged with the platform (iOS or Android) so the delivery
worker knows which PNS API to call.

## The payload: what you actually send

The **payload** is the small JSON body that your server sends to the PNS along
with the device token. It contains the title, body text, maybe a sound name
or badge count, and any custom data your app needs to handle the notification
(like a deep-link URL or a conversation ID).

The critical constraint is **size**. APNs allows a maximum payload of **4 KB**
(4096 bytes). FCM allows up to **4 KB** for the notification portion of a
message. That sounds generous until you realize it includes everything — the
JSON structure itself, keys, values, and any custom data. In practice you have
room for a short title, a one-or-two-sentence body, and a handful of small
key-value pairs. You cannot stuff an image, a long article, or a complex data
structure into a push payload.

A simplified APNs payload looks like this:

```json
{
  "aps": {
    "alert": {
      "title": "New message",
      "body": "Alice: Hey, are you coming tonight?"
    },
    "sound": "default",
    "badge": 3
  },
  "conversation_id": "c-8821"
}
```

An FCM payload follows a different schema but carries the same kinds of
fields: a `notification` block for display, and a `data` block for custom
key-value pairs.

Because the payload is small, it is a *signal*, not the content itself. The
notification tells the user something happened and gives the app just enough
context to fetch the full content when the user taps it.

## Silent push / background push

A **silent push** (Apple's term) or **background push** (general term) is a
push notification that arrives on the device but shows nothing to the user —
no banner, no sound, no badge. Instead, the OS wakes the app briefly in the
background and hands it the payload. The app can then do a small amount of
work: fetch new data from your server, update a local database, refresh a
cache.

Why would you send an invisible notification? Common use cases:

- **Data sync.** A messaging app receives a silent push saying "new messages
  available," fetches them, and has them ready when the user opens the app —
  no loading spinner.
- **Content pre-fetch.** A news app fetches the latest headlines in the
  background so they're instantly visible on launch.
- **State updates.** A ride-sharing app silently updates the driver's
  location on the rider's phone without showing a visible alert every second.

Silent pushes have stricter limits than visible ones. Apple throttles them
aggressively — the system may delay or drop them if you send too many, and
the OS gives your app only about 30 seconds of background execution time per
wake-up. They are a best-effort mechanism, not a guaranteed delivery channel.

## How this fits in the architecture

Recall from Lesson 2 that the notification system has delivery workers
downstream of the message queue. Here is where those workers plug in:

1. A delivery worker picks a notification off the queue.
2. It looks up the recipient's device tokens (and their platforms) from the
   token store.
3. For each token, it builds a payload and calls the appropriate PNS API —
   APNs for iOS tokens, FCM for Android tokens.
4. The PNS accepts the message (or rejects it with an error — invalid token,
   payload too large, rate limited).
5. The PNS handles the final delivery to the device over its persistent
   connection.

Your server never talks to the device directly. It talks to the PNS, and the
PNS talks to the device. This means your server's job is to be a reliable,
fast *client* of the APNs and FCM APIs — maintaining connection pools,
handling errors and retries, and pruning dead tokens.

## Recap

- You cannot push directly to a phone. You must go through the OS vendor's
  **push notification service** — APNs for Apple, FCM for Google.
- A **device token** uniquely identifies one app install on one device. Tokens
  change, expire, and are platform-specific. Your backend must keep them
  up to date.
- The **payload** is a small JSON body (max ~4 KB) that carries the alert
  text and minimal custom data. It is a signal, not the full content.
- A **silent/background push** shows nothing to the user but wakes the app
  to do background work like data sync. It is throttled and best-effort.
- Delivery workers in your system are clients of the PNS APIs. They look up
  tokens, build payloads, and hand messages to APNs or FCM for final
  delivery.

## Check yourself

1. A user installs your app on their iPhone and their iPad. How many device
   tokens does your server store for that user, and why can't you use a
   single token for both devices?

2. You need to send a notification that includes a 10 KB image. Can you put
   the image in the push payload? If not, what is the standard approach?
