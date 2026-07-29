# Lesson 8 — Push Delivery Mechanics: APNs, FCM, and Device Tokens

## Why this matters

Your server cannot reach a phone directly. Mobile networks, battery
optimization, and OS security all block it. Every push notification you have
ever received was routed through a middleman operated by the device's OS
vendor. Understanding how that relay works — and the constraints it imposes —
is essential before you can design a delivery pipeline that reaches 100M+
devices.

## The push notification service: your mandatory middleman

A **push notification service** (PNS) is a cloud service run by the OS vendor
that acts as the sole gateway for delivering push notifications to devices.
Apple runs **APNs** (Apple Push Notification service) for iOS and macOS.
Google runs **FCM** (Firebase Cloud Messaging) for Android. The operating
system will not let a third-party server wake an app or show a banner without
going through its PNS.

Think of it like sending mail to a gated community. You cannot walk up to
someone's front door — you hand the letter to the postal service, and they
deliver it. APNs and FCM are that postal service.

Why do OS vendors force this?

1. **Battery life.** If every app kept its own persistent connection to its
   server, the radio would never sleep and the battery would drain in hours.
   The OS keeps one single persistent connection to its PNS, shared by all
   apps.
2. **Security and control.** The OS enforces permission rules, rate limits,
   and payload restrictions before anything reaches the screen.

The diagram below shows the full delivery path from your server to a device,
including the success and failure branches the PNS can return:

```mermaid
sequenceDiagram
    participant Server as Your Server
    participant PNS as APNs or FCM
    participant Device as User Device

    Server->>PNS: HTTP/2 request with payload + device token
    PNS->>PNS: Validate token and payload

    alt Token valid, payload under 4 KB
        PNS->>Device: Deliver notification over persistent connection
        Device->>Device: OS displays alert or wakes app
        PNS-->>Server: 200 OK
    else Invalid or expired token
        PNS-->>Server: 410 Gone (prune this token)
    else Payload too large
        PNS-->>Server: 413 Payload Too Large
    end
```

Your server never talks to the device directly. It talks to the PNS, and the
PNS handles the last hop over its persistent OS-level connection to the device.

## Device tokens: addressing a specific app on a specific phone

When your app is installed and the user grants notification permission, the
app registers with the PNS. The PNS returns a **device token** — a long,
opaque string that uniquely identifies *this app install on this device*. It
is not a phone number, not a user ID, not a device serial number.

Key properties:

- **One token per app per device.** A user with an iPhone and an iPad has two
  tokens for your app.
- **Tokens can change.** The OS may rotate a token after an OS update, a
  backup restore, or just periodically. Your server must always accept and
  store fresh tokens from the app.
- **Tokens expire or become invalid.** Uninstalling the app kills the token.
  The PNS tells you via error responses (like the 410 Gone above). You must
  prune dead tokens or risk being throttled.
- **Tokens are platform-specific.** An APNs token only works with APNs; an
  FCM token only works with FCM.

Here is the registration flow that happens when a user first installs your app
and grants notification permission:

```mermaid
sequenceDiagram
    participant App as Mobile App
    participant OS as Device OS
    participant PNS as APNs or FCM
    participant Backend as Your Backend

    App->>OS: Request notification permission
    OS-->>App: Permission granted by user
    App->>PNS: Register for push notifications
    PNS-->>App: Return device token
    App->>Backend: POST /device-tokens with token + platform tag
    Backend->>Backend: Store user_id, token, platform (ios or android)
    Note over Backend: Upsert on every app launch in case token rotated
```

Your backend stores a mapping of `user_id -> [list of device tokens]`, each
tagged with the platform so delivery workers know which PNS API to call.
Most users have two or three devices; some power users have many more.

## The payload: what you actually send

The **payload** is a small JSON body your server sends to the PNS along with
the device token. It contains the notification title, body text, optional
sound or badge count, and custom data your app needs — such as a deep-link
URL or a conversation ID.

The critical constraint is **size**: both APNs and FCM cap the payload at
roughly **4 KB**. In practice you have room for a short title, one or two
sentences of body text, and a few small key-value pairs. You cannot put an
image or a long article in a push payload.

Below is a simplified breakdown of what a payload contains and how each
section is used:

```mermaid
flowchart TD
    Payload[Push Payload - max 4 KB JSON]
    Payload --> SystemKeys[System keys - aps for APNs]
    Payload --> CustomKeys[Custom app data]

    SystemKeys --> Alert[alert: title and body text]
    SystemKeys --> Sound[sound: default or custom file name]
    SystemKeys --> Badge[badge: number shown on app icon]
    SystemKeys --> ContentAvail[content-available: 1 for silent push]

    CustomKeys --> DeepLink[deep_link: screen to open on tap]
    CustomKeys --> ConvID[conversation_id or entity ID]
    CustomKeys --> ActionHint[action: like reply or accept]
```

Because the payload is small, it is a *signal*, not the content itself. The
notification tells the user something happened and gives the app just enough
context to fetch the full content when tapped.

## Silent push and background push

A **silent push** (Apple's term) or **background push** is a push notification
that arrives on the device but shows nothing to the user — no banner, no
sound, no badge. The OS wakes the app briefly in the background and hands it
the payload. The app can then fetch new data, update a local database, or
refresh a cache before the user ever opens the app.

You trigger a silent push on APNs by setting `"content-available": 1` in the
`aps` dictionary and omitting the `alert` key. FCM has an equivalent
`data`-only message type.

Common use cases:

- **Data sync.** A messaging app fetches new messages so they are ready when
  the user opens the app — no loading spinner.
- **Content pre-fetch.** A news app pulls fresh headlines in the background.
- **State updates.** A ride-sharing app silently refreshes driver location
  without showing an alert every few seconds.

```mermaid
sequenceDiagram
    participant Server as Your Server
    participant PNS as APNs or FCM
    participant OS as Device OS
    participant App as App Process - Background

    Server->>PNS: Silent push payload - content-available 1, no alert
    PNS->>OS: Deliver silent notification
    OS->>App: Wake app process - up to 30 seconds runtime
    App->>Server: GET /messages?since=last_sync
    Server-->>App: Return new messages JSON
    App->>App: Write to local database
    App->>OS: Signal background task complete
    Note over OS,App: User opens app and sees messages instantly - no spinner
```

Silent pushes have stricter limits than regular pushes. Apple throttles them
aggressively — the system may delay or drop them under battery pressure — and
gives your app only about 30 seconds of background CPU time per wake-up.
Treat silent push as best-effort, not guaranteed delivery.

## How delivery workers use all of this

Recall from Lesson 2 that delivery workers sit downstream of the message
queue. Here is how they plug into the push delivery path end to end:

```mermaid
flowchart LR
    Queue[Message Queue] --> Worker[Delivery Worker]
    Worker --> Lookup[Token Store Lookup]
    Lookup --> iOS[Build APNs Payload]
    Lookup --> Android[Build FCM Payload]
    iOS --> APNs[APNs HTTP/2 API]
    Android --> FCM[FCM HTTP v1 API]
    APNs --> iDevice[iOS Device]
    FCM --> aDevice[Android Device]
    APNs -->|Invalid token 410| Prune[Prune Dead Tokens]
    FCM -->|Unregistered| Prune
```

The worker picks a notification off the queue, looks up device tokens and
their platforms, builds a per-platform payload, and calls the appropriate PNS
API. The PNS accepts or rejects the message. Your server's job is to be a
reliable, fast *client* of these APIs — maintaining HTTP/2 connection pools,
handling errors with retries and backoff, and continuously pruning dead tokens
to stay off throttle lists.

## Recap

- You cannot push directly to a phone. You must go through the OS vendor's
  **push notification service** — APNs for Apple, FCM for Google.
- A **device token** uniquely identifies one app install on one device. Tokens
  change, expire, and are platform-specific. Your backend must keep them
  current by accepting fresh tokens on every app launch.
- The **payload** is a small JSON body (max ~4 KB) carrying alert text and
  minimal custom data. It is a signal, not the full content.
- A **silent/background push** shows nothing to the user but wakes the app
  for background work like data sync. It is throttled, best-effort, and
  capped at ~30 seconds of runtime.
- Delivery workers are clients of the PNS APIs — they look up tokens, build
  payloads, call APNs or FCM, and prune any tokens reported as dead.

## Check yourself

1. A user installs your app on their iPhone and their iPad. How many device
   tokens does your server store for that user, and why can't you reuse a
   single token for both devices?

2. You need to send a notification that includes a 10 KB thumbnail image. Can
   you put the image in the push payload? If not, what is the standard
   approach?

3. You send a silent push to pre-fetch data. Two hours later the user opens
   the app and sees stale content. What are two reasons the silent push might
   not have triggered the background fetch?
