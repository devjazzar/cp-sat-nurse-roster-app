# 41: A push reaches the device and a tap opens the page

**What to build:** A colleague proposes a swap; the nurse's phone, with pushes on, shows "Nurse roster: You have a swap to answer", and a tap opens the app on Swaps. The same for the other five kinds with a deadline: a swap awaiting the manager ("A swap waits for your decision", the unit's swaps), a request window opened ("Requests are open for a coming month", My month), a window closed with requests waiting ("Requests wait for your decision", Requests), a roster submitted ("A roster waits for your approval", the roster overview) and a roster rejected ("A roster was sent back to you", the Roster page). Nothing else is ever pushed. The push carries only its kind code: no name, date, month, unit or identifier. The worker sends it, through one new network with a way out, and only after checking the thing still waits and the reader still has a page for it. A dead subscription is ended at once; one failing ten sends in a row is ended; a retry reaches only the subscriptions that failed. A window opening reaches forty phones once each.

Spec: `.scratch/nurse-rostering-v2/specs/web-push-for-deadlines.md`. Reasons: `docs/adr/0012-web-push-carries-no-personal-data.md`, with ADR 0001, 0006 and 0009.

**Blocked by:** 40 A device turns pushes on and off

**Status:** ready-for-agent

- [ ] `deploy/compose.yaml`: a network `egress`, not internal, joined by the worker only; `web`, `db`, `solver` and `caddy` unchanged; the development and browser-check compose files give the worker a way out as their other services have
- [ ] The sending library (pywebpush 2.5.x) as a backend dependency, imported only by `notifications.pushing`, which alone knows the protocol, headers, encryption and status codes and answers in the app's words: sent, gone, refused, unreachable; confirmed to install and send on the image's Python 3.14 before building on it; a scripted stand-in for the tests
- [ ] `notifications.sending.notify` defers one push job per call, inside the same transaction, only when the event and step have a kind: swap step `proposed` → `swap_to_answer`, `awaiting` → `swap_to_decide`, window opened → `requests_open`, window closed (the manager's) → `requests_to_decide`, roster submitted → `roster_to_approve`, roster rejected → `roster_sent_back`; every other event and step defers none
- [ ] The job runs under its own lock `push`; before each send it checks the reader still has a page for the notification (the Notifications page's own rule) and the thing still waits by kind (swap still pending or awaiting the manager; window still open, or closed with requests still pending; roster still submitted; a rejected roster still a draft not resubmitted); otherwise it sends nothing, counts no failure and retries nothing
- [ ] The payload is the kind code alone; headers: time to live 24 hours, urgency normal, topic the kind
- [ ] Per subscription: success resets the failures and sets the last success; 404 or 410 ends the subscription at once; any other failure adds one, and the tenth ends it; these ends write no audit entry
- [ ] A transient failure is tried again three times over about ten minutes for the failed subscriptions only; those reached, ended or skipped are not sent to again; each attempt is recorded once per subscription in an append-only attempts table (bigint key: when, outcome, nothing of the user or device)
- [ ] The service worker's `push` listener shows a notification with title "Nurse roster", the kind's words, the kind as tag; always shown, app open or not; an unknown kind shows the title alone
- [ ] The `notificationclick` listener closes the notification, focuses an open window of the app and sends it to the kind's page with no month, or opens a new window on it
- [ ] Tests at the agreed seams: the backend suite with the scripted sender and the real queue (each of the six events makes one job for its recipients and nobody else, every other makes none, a rolled-back change makes none; payload and headers; the still-waits and still-has-a-page checks for each kind; 404/410, the count to ten and the reset; the partial retry and once-per-subscription attempts; a manager with a nurse profile gets both roles' kinds, the System Admin none); the service worker's test (the six kinds' words and tags, the unknown kind, the tap with and without an open window, no `fetch`)
- [ ] Driven on a scratch compose project: with the worker's way out, a real browser subscribed on the implementer's own device or desktop browser receives a push for a proposed swap and the tap opens Swaps; say in the comment what was and was not driven
- [ ] `makemigrations --check` clean; the dev stack's rebuild and `up -d` named in the comment

**From ticket 40 (2026-11-10):** the subscriptions and the key pair are in; nothing is sent. What this ticket builds on:
- **The key pair** is `notifications.models.PushKeyPair`, one row (`pk=1`): `private_key` is a PEM, PKCS #8, P-256 key and
  `public_key` the uncompressed point in base64url without padding. Hand py-vapid the PEM, as
  `Vapid.from_pem(row.private_key.encode())`, and pass that `Vapid` to pywebpush, rather than the string, which it reads
  differently. `notifications.push_keys.public_key()` is what browsers subscribe with. A rotation (`rotate_push_keys`) keeps
  every row, so sends to devices still bound to the old key fail as refusals until each one re-subscribes at its next start.
  Those failures count toward the ten, as the spec says.
- **pywebpush is not added yet.** Only `cryptography` (50.0.x) is. Your criterion says to confirm pywebpush 2.5.x installs and
  sends on the image's Python 3.14 before building on it, so the library and that check land together here. pywebpush pulls
  in py-vapid, http-ece, requests and aiohttp. `cryptography` is already pinned, so check that its range meets pywebpush's.
- **`PushSubscription`** has `user`, `endpoint` (unique), `p256dh`, `auth`, `turned_on_at`, `failures_in_a_row` and
  `last_success_at`. The last two are written by nothing yet: they are yours. Ending a row is a plain `delete()` with no
  audit entry (`notifications.subscriptions.end_for` deletes a user's).
- **An address is any `https://` URL up to 2000 characters.** Ticket 40 does not check the host. The worker sends to whatever
  a signed-in user posted, from the `egress` network and the `backend` and `solver` networks alike. Before the first send,
  decide whether to refuse an endpoint outside the push services' hosts (the four in ticket 42's install guide), at turn-on
  or at send. That closes a request-forgery path through the worker; the user's decision to take, not ticket 40's.
- **The service worker** has `install`, `activate` and `pushsubscriptionchange`, and still no `fetch`. Its test
  (`src/sw.test.ts`) runs the worker with `self`, `caches` and `fetch` as parameters; add `push` and `notificationclick`
  beside them. `self.registration` is already in the stand-in.
