# 41: A push reaches the device and a tap opens the page

**What to build:** A colleague proposes a swap; the nurse's phone, with pushes on, shows "Nurse roster: You have a swap to answer", and a tap opens the app on Swaps. The same for the other five kinds with a deadline: a swap awaiting the manager ("A swap waits for your decision", the unit's swaps), a request window opened ("Requests are open for a coming month", My month), a window closed with requests waiting ("Requests wait for your decision", Requests), a roster submitted ("A roster waits for your approval", the roster overview) and a roster rejected ("A roster was sent back to you", the Roster page). Nothing else is ever pushed. The push carries only its kind code: no name, date, month, unit or identifier. The worker sends it, through one new network with a way out, and only after checking the thing still waits and the reader still has a page for it. A dead subscription is ended at once; one failing ten sends in a row is ended; a retry reaches only the subscriptions that failed. A window opening reaches forty phones once each.

Spec: `.scratch/nurse-rostering-v2/specs/web-push-for-deadlines.md`. Reasons: `docs/adr/0012-web-push-carries-no-personal-data.md`, with ADR 0001, 0006 and 0009.

**Blocked by:** 40 A device turns pushes on and off

**Status:** ready-for-agent

- [x] `deploy/compose.yaml`: a network `egress`, not internal, joined by the worker only; `web`, `db`, `solver` and `caddy` unchanged; the development and browser-check compose files give the worker a way out as their other services have
- [x] The sending library (pywebpush 2.5.x) as a backend dependency, imported only by `notifications.pushing`, which alone knows the protocol, headers, encryption and status codes and answers in the app's words: sent, gone, refused, unreachable; confirmed to install and send on the image's Python 3.14 before building on it; a scripted stand-in for the tests
- [x] `notifications.sending.notify` defers one push job per call, inside the same transaction, only when the event and step have a kind: swap step `proposed` → `swap_to_answer`, `awaiting` → `swap_to_decide`, window opened → `requests_open`, window closed (the manager's) → `requests_to_decide`, roster submitted → `roster_to_approve`, roster rejected → `roster_sent_back`; every other event and step defers none
- [x] The job runs under its own lock `push`; before each send it checks the reader still has a page for the notification (the Notifications page's own rule) and the thing still waits by kind (swap still pending or awaiting the manager; window still open, or closed with requests still pending; roster still submitted; a rejected roster still a draft not resubmitted); otherwise it sends nothing, counts no failure and retries nothing
- [x] The payload is the kind code alone; headers: time to live 24 hours, urgency normal, topic the kind
- [x] Per subscription: success resets the failures and sets the last success; 404 or 410 ends the subscription at once; any other failure adds one, and the tenth ends it; these ends write no audit entry
- [x] A transient failure is tried again three times over about ten minutes for the failed subscriptions only; those reached, ended or skipped are not sent to again; each attempt is recorded once per subscription in an append-only attempts table (bigint key: when, outcome, nothing of the user or device)
- [x] The service worker's `push` listener shows a notification with title "Nurse roster", the kind's words, the kind as tag; always shown, app open or not; an unknown kind shows the title alone
- [x] The `notificationclick` listener closes the notification, focuses an open window of the app and sends it to the kind's page with no month, or opens a new window on it
- [x] Tests at the agreed seams: the backend suite with the scripted sender and the real queue (each of the six events makes one job for its recipients and nobody else, every other makes none, a rolled-back change makes none; payload and headers; the still-waits and still-has-a-page checks for each kind; 404/410, the count to ten and the reset; the partial retry and once-per-subscription attempts; a manager with a nurse profile gets both roles' kinds, the System Admin none); the service worker's test (the six kinds' words and tags, the unknown kind, the tap with and without an open window, no `fetch`)
- [x] Driven on a scratch compose project: with the worker's way out, a real browser subscribed on the implementer's own device or desktop browser receives a push for a proposed swap and the tap opens Swaps; say in the comment what was and was not driven
- [x] `makemigrations --check` clean; the dev stack's rebuild and `up -d` named in the comment

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

**From the review of ticket 40 (2026-11-10), decided by the user:** limit a push subscription's address to the browser push services' own hosts, to close a request-forgery path through the worker.
- **Hosts:** Google's `fcm.googleapis.com`, Mozilla's `updates.push.services.mozilla.com` and `*.push.services.mozilla.com`, Apple's `*.push.apple.com`, and Microsoft's `*.notify.windows.com`. Confirm the current list from the services' own documentation.
- **Where:** refuse any other host at turn-on, in `notifications.subscriptions` (a field error, as for a malformed address), and check again before each send.
- **Rows held already:** treat a held row whose host is not allowed as ended, deleted with no entry.
- **Tests:** at the web API seam, for turn-on and for the send.

**Implemented on 2026-11-10,** on branch `claude/ticket-41-push-sent-44e74e`, draft pull request
Nurse-Fold/cp-sat-nurse-roster-app#29, from `main` at `0c4393f`. The commits:
- `5b04fae`: pywebpush, alone, so GitHub built the image with it before anything rested on it;
- `905d307`: the backend: kinds, the job, the sender, the attempts, the host allow-list, and their tests;
- `ded1689`: the service worker's `push` and `notificationclick`, the app following a tap, and their tests;
- `f26ea4b`: the `egress` network;
- `7b51ed1`: a tap still moves the window when the browser refuses the focus (found while driving);
- `fab6e57`: the review's points;
- then this comment.

The suites ran locally, one at a time under the heavy-run lock, the backend on a throwaway PostgreSQL 18 container of my own:
- the backend, on `7b51ed1`: 3016 passed. After `fab6e57`, `notifications/` again: 129 passed;
- the frontend, on `7b51ed1`: one `npm test` run, 744 passed, and `npm run build` succeeded; after `fab6e57`, `src/sw.test.ts`
  again: 26 passed;
- `makemigrations --check`: "No changes detected", on both heads;
- the API's shape is unchanged (a field error on an existing call), so `openapi.json` and the client are untouched.

GitHub ran both workflows green on `5b04fae`, the image built with pywebpush on `python:3.14-slim-trixie` with uv 0.13.7.

**What the dev stack needs:** a **rebuild and `up -d`** (`docker compose up -d --build`).
- One new backend dependency, `pywebpush>=2.5,<2.6` (2.5.0, with `py-vapid` 1.9.6, `http-ece` 1.2.1, `requests` and
  `aiohttp`), with `uv.lock`. `cryptography` stays 50.0.2, inside pywebpush's range.
- `deploy/compose.yaml` changed: the network `egress`. `up -d` creates it and recreates the worker on it.
- One migration, `notifications/0008_push_attempts`, which also ends any held subscription off the push services' hosts.
- No change to the `Dockerfile` or the solver. Vite serves the changed service worker at once.

**What was built, criterion by criterion.**
- **`egress`:** a network that is not internal, joined by the worker alone (`backend`, `solver`, `egress`). `web`, `db`,
  `solver` and `caddy` are as they were. None of `compose.dev.yaml`, `e2e/compose.e2e.yaml` and `deploy/tests/compose.test.yaml`
  overrides the worker's networks, so each keeps `egress`; `docker compose config` of all four combinations shows it.
- **The library:** pywebpush is imported only by `notifications.pushing`, as is py-vapid. It knows the protocol, the headers,
  the encryption and the status codes, and answers `sent`, `gone` (404, 410), `refused` (any other 4xx, a redirect, keys that
  cannot be encrypted to) or `unreachable` (no connection, a timeout, 429, 5xx). It never raises. It signs with
  `Vapid.from_pem(...)`, as ticket 40 said, and posts through one `requests` session that follows no redirect, with a 10 s
  timeout. Before building on it I sent with it on Python 3.14.10 to a local receiver that decrypted the body (aes128gcm) and
  read the TTL, Urgency and Topic headers; then the image built on GitHub, and the stack's worker sent with it for real.
- **Which notification is pushed:** `notifications.kinds` maps the event and step to the six kind codes; every other event
  and step has none. `notify` defers one `push` job per call, carrying the new rows' ids, in the caller's transaction, only
  when rows were made and the kind is one of the six.
- **The job:** `notifications.tasks.push`, under the lock `push` (`under_its_own_lock`). Before each send
  (`notifications.pushes`) it reads, per notification:
  - the kind's own check, as the pages read it, from the dates as well as the stored state: a swap `pending` by
    `swaps.expiring.state_now` and this colleague's answer still pending; a swap `awaiting_manager`; a window open by
    `requesting.windows.state_today`; a window closed with a request still `pending`; a roster `submitted`; a roster `draft`
    with no submission since the notification;
  - the Notifications page's own rule, `reading.link_of`, for the reader as they are now, and active.

  A thing no longer waiting sends nothing, counts no failure and is tried again never.
- **What is sent:** `{"kind": "<code>"}` and nothing else; TTL 86400, `Urgency: normal`, `Topic: <code>`.
- **Per subscription:** a success sets `failures_in_a_row` to 0 and `last_success_at`; 404 or 410 deletes the row at once; a
  push that does not reach it adds one, and the tenth deletes it; none of these writes an audit entry. The moves live in
  `notifications.subscriptions` (`reached`, `not_reached`, `end`), beside its other ends. A retried push counts once: see
  "Worth your review".
- **Trying again:** an `unreachable` send is tried again after 1, 3 and 6 minutes (`RETRY_IN`), for the failed
  subscriptions alone: the job defers itself with the remaining pairs of notification and subscription. Each try reads the
  checks again and sends only to a subscription still the reader's, so an address moved to another user in between is not
  sent this one. Each send is one row of `notifications.PushAttempt` (bigint key, `at`, `outcome`), nothing of the user or
  the device.
- **The service worker's `push`:** it always shows "Nurse roster", with the kind's words and the kind as tag, app open or not.
  An unknown kind, no kind, a body that is not JSON, or none at all shows the title alone. It fetches nothing.
- **`notificationclick`:** it closes the notification, then finds a window of the app (`includeUncontrolled`), focuses it and
  posts it `{type: "open-page", path}`. The app (`__root.tsx`, `lib/service-worker.ts`) goes there through its own router,
  so a page with unsaved changes still asks first. With no window open, it opens one on the page. Pages, with no month:
  `/swaps`, `/unit-swaps`, `/my-month`, `/requests`, `/rosters`, `/roster`. An unknown kind opens `/`.
- **The hosts:** a turn-on (`POST /api/notifications/push/on`) to any other host is refused with a 422 field error on
  `endpoint`, "The address is not a browser push service's."; the state, Turn off and a renewal's `replaces` still read any
  address. The job checks each row again before each send, and ends one off the list unsent. The migration ends any already
  held. An address is allowed only over `https`, on the default port, with no user name, and no trailing dot on the host:
  - `fcm.googleapis.com`. Google's network configuration page for FCM names it as the host for sending
    (firebase.google.com/docs/cloud-messaging/network-configuration), and every Chrome subscription in the drive was on it;
  - `push.services.mozilla.com` and any name under it. The autopush documentation's examples post to
    `updates.push.services.mozilla.com` and also to the bare `push.services.mozilla.com`
    (mozilla-services.github.io/autopush-rs/http.html);
  - any name under `push.apple.com`. Apple's "Sending web push notifications in web apps and browsers" says to allow
    `https://*.push.apple.com` when the network limits which URLs the server can reach;
  - any name under `notify.windows.com`. Microsoft's "Adding WNS traffic to the firewall allowlist" lists `*.notify.windows.com`
    as the hosts a cloud service sends to (learn.microsoft.com/windows/apps/develop/notifications/push-notifications/
    firewall-allowlist-config).
- **Tests at the agreed seams:**
  - `notifications/tests/test_pushes.py` (60), on the real queue, with the push services scripted at their HTTP side:
    - each of the six events reaching exactly its readers;
    - every other change pushing nothing, and a rolled-back change nothing;
    - forty phones once each from one job;
    - the payload decrypted as a browser would, the headers and the installation's key;
    - each kind's still-waits case, and the reader taken off the unit or deactivated;
    - 404, 410, the refusals, the count to ten and the reset, and no audit entry;
    - the partial retry, three tries more, one failure, one attempt a send;
    - no retry to a subscription turned on since, or to an address moved to another user;
    - a retry waiting for its time holding back no new push;
    - the allow-list, at turn-on (7 allowed, 12 refused) and at send.

    The root `conftest.py` makes any send in any other test fail, so no test reaches a real push service.
  - `src/sw.test.ts`: the six kinds' words and tags, five unknown or broken pushes, the tap with an open window for each kind
    and with none, an unknown kind's tap, no `fetch` listener and no `fetch` on a push.
  - `src/app.test.tsx`: a message from the worker brings the open app to Swaps, and the others are ignored.

**What was driven, and how.** I used my own scratch stack, `e2e/stack.sh up t41` (ports 18481 and 18941), on 10 November
2026. Its worker was on `t41_backend`, `t41_egress` and `t41_solver`.
- **The browser:** the installed Google Chrome 157, started by hand with a profile of its own, `--ignore-certificate-errors`
  for Caddy's self-signed certificate and remote debugging, driven over CDP. Notifications were allowed in that profile's own
  settings. Badr signed in over HTTPS and turned pushes on; the subscription was on `fcm.googleapis.com`.
- **The push:** a sound swap was proposed to Badr from another browser as Amal. The worker's job sent it, Google answered
  201, and Chrome's `gcm-internals` logged the message received. The service worker showed "Nurse roster / You have a swap
  to answer", tagged `swap_to_answer`, with Badr's window open on `/`. The attempts table held `sent` rows and nothing else.
- **A dead address, live:** a subscription Chrome had dropped got 404 or 410 from Google; the job ended it at once (one
  `gone` attempt, the row gone).
- **The tap, a real click, with a window open:** in a second session of the same stack and profile (Amal subscribed, Dana
  proposing), you clicked the macOS notification yourself. Chrome was started with `open -na "Google Chrome" --args …`,
  with no other Chrome running; started by running its binary, no click reached it. Traced inside the worker and the page
  at 03:28: one `notificationclick` carrying `{"kind": "swap_to_answer"}`, one `open-page` message with `/swaps`, and
  Amal's open window went from `/` to `/swaps` through the app's router. At 03:19 and 03:24 the window ended on `/swaps`
  too, but went to the app's home a second before (next points).
- **The tap, a real click, with no app window open:** a window opened and landed on `/swaps`. It was not a clean run of
  `openWindow("/swaps")`, though: the window opened on `/` and moved a second later, which I read, without a trace inside
  the worker for that run, as Chrome's own notice (next point) clicked first and ours after. So a real click opening a window from the worker was seen, with `/` as its page, and
  `/swaps` in a new window rests on `sw.test.ts`.
- **Chrome's own notice beside ours, in this Chrome only as far as I know:** in the three runs with the app not the focused
  tab, the window went home before Swaps; in the two with it focused, it did not. The 03:24 trace shows why: Chrome had
  added "This site has been updated in the background" 5 ms after our notification, and a click on it reached the worker
  with `data: null`, so it opened the app's home. Chrome adds that notice when it believes a push showed nothing. From
  about 03:21 on, `registration.getNotifications()` in this Chrome came back empty straight after `showNotification()`
  resolved, for a bare notification of my own as well as for a push; at 03:18 it had listed ours, and the hop home
  followed all the same. So my reading, not proven, is that this Chrome's bookkeeping was at fault and not the worker's
  order of work, and that the clicks that did nothing (one at 03:21, and on my bare notification) met a notification
  Chrome had dropped its record of. I could not tell whether an ordinary Chrome does this; see "What was NOT checked".
- **Before that,** when no real click got through, I ran the worker's own listener by dispatching the event on the real
  notification: the window went to `/swaps`. With no window open that dispatch opened none, as Chrome lets a worker open a
  window only in a real click's activation.
- **The allow-list:** as Amal, turn-ons of `https://collector.example/push`, `https://fcm.googleapis.com.collector.example/x`
  and `https://solver:8080/solve` each answered 422 with the field error on `endpoint`, and no row was kept.
- **The ways out:** from the containers, the worker reached `fcm.googleapis.com:443` and the solver could not resolve it.
  `web` reached it too, but only because `e2e/compose.e2e.yaml` already puts `web` on `public` for its HTTP port. In
  `deploy/compose.yaml` alone `web` is on internal networks only.

The stack is down and its volumes gone; the browser profile is deleted.

**What was found, and fixed.**
- **A tap with no user activation behind it:** `focus()` may be refused, and the window was then never moved. The tap now
  posts the page whatever the focus answers (`7b51ed1`).

**Findings for you, not fixed:** none in the app. One for whoever drives pushes next: a browser launched by Playwright
receives none. Its default `--disable-background-networking` cuts Chrome off from its push service, and a permission granted
with `grantPermissions` lapses when that connection closes, after which Chrome drops the subscription. Allow notifications in
the profile, and start Chrome with `open -na "Google Chrome" --args --user-data-dir=… --remote-debugging-port=…` with no
other Chrome running: a click on a notification reached no Chrome started by running its binary.

**What was NOT checked.**
- **An ordinary Chrome, started the usual way with a trusted certificate.** The one driven was started with its own profile,
  `--ignore-certificate-errors` and remote debugging, and it lost track of the notifications it showed (above). Whether a
  nurse's Chrome adds its own notice beside ours is not known. It is the first thing to look at when ticket 42 is seen
  working on a real host name.
- **A new window opening straight on `/swaps`** from a real click (above).
- **An iPhone, an iPad, Safari, Firefox or Edge:** only Chrome on macOS through Google's service. Apple's, Mozilla's and
  Microsoft's services, their status codes and their reading of the VAPID `sub`, are untested beyond the scripted stand-in.
- **A real retry against a push service that was down,** a 429 or a 5xx from a real service: the scripted ones only.
- **A real 401 or 403 after `rotate_push_keys`.**
- **Pushes for the other five kinds in a real browser:** each was shown only in `sw.test.ts`, except `swap_to_decide` and
  `requests_open`, which I sent by hand through `pushing.send` and saw shown.
- **The six parallel frontend runs and the browser checks, locally:** GitHub runs them on the pull request.

**Decisions taken here.**
- **The stand-in is at the HTTP seam**, `pushing.push_service`, rather than replacing `pushing.send`. The real library
  encrypts and signs in every test, and a test reads the body as the browser would, decrypted with the device's own keys.
- **A retry has priority −1.** Procrastinate does not fetch a job while an earlier waiting job of the same lock and priority
  exists, even one scheduled for later, so a retry waiting six minutes would hold back every new push. At a lower priority
  it holds none back (`ops.queue.enqueue_later`, and a test).
- **What a tap does to an open window:** a message to the app's own router, not `client.navigate()`, which is a full load
  that would drop a roster's unsaved edits and a password shown once without asking.
- **A refusal is not tried again;** only `unreachable` is "transient", as the ticket says.
- **The VAPID subject** is `https://<DOMAIN>` when the installation has a domain, else `mailto:push@nurse-roster.invalid`,
  which names no one. Apple refuses one that is neither a URL nor `mailto:`.
- **The data migration keeps its own copy of the hosts,** so it does what it did whatever the app's list becomes.
- **The swap to answer also checks this colleague's own answer,** so a swap she answered elsewhere, still waiting for
  others, is not pushed to her (user story 11).

**Worth your review.**
- **How a retried push counts toward the ten: decided by you on 10 November 2026, one per push.** The spec says any failure
  other than gone adds one. A refusal counts at once; an unreachable service counts once, after its last retry. Counting
  every try would end every subscription after a ten-minute outage spanning three pushes. Criterion 6 is ticked on that
  reading.
- **The bare `push.services.mozilla.com`** is allowed beside the names under it: Mozilla's own example uses it. Your list
  named `updates.push.services.mozilla.com` and `*.push.services.mozilla.com`. Recommendation: keep.
- **"A manager with a nurse profile gets both roles' kinds"** cannot happen today: a manager's cells are never swapped and a
  manager makes no requests (section 3), so no nurse kind reaches a manager on the bell, and the push follows the bell. The
  test asserts that: a manager with a nurse profile gets the manager's kinds alone. Recommendation: keep; widening it would
  be your decision.
- **An unknown kind's tap opens the app's home.** The spec said nothing of it. Seen while driving: a click on Chrome's own
  "updated in the background" notice reaches the worker the same way, with `data: null`, and sends an open window home.
  Having such a click do nothing instead is your decision; I changed nothing.

**Review.** `code-review` against `0c4393f` ran its two axes in parallel.
- **Spec.** Nothing asked for is missing. Fixed: the migration's live import of the host check. Kept: the count of a retried
  push, the bare Mozilla host, the HTTP-level stand-in and the router message, all above.
- **Standards.** No hard breach. Fixed:
  - the subscription's ends moved into `notifications.subscriptions`;
  - `still_waits` is one check per kind in a map;
  - the worker's known-kind test is one helper;
  - a comment in `compose.yaml` that pointed at an install-guide section not yet written;
  - unclear names in the retry's filter.

  Kept:
  - `pushes` beside `pushing` (the job's work and the protocol);
  - the three fields passed to `send`, which keep the sender free of the models;
  - `Pairs` as lists, which a job's JSON arguments need;
  - `open-page` written in both the worker and the app, since a worker cannot import the app's modules.

**Things later tickets should know.**
- **Ticket 42:** see the note on it.
- **A new kind with a deadline** (a cover offered): one code in `notifications/kinds.py`, its check in `pushes._STILL_WAITS`,
  and its words and page in `frontend/public/sw.js`.

**Reviewed by the user (2026-11-10):** the retried push counts once, as the user decided with the ticket's session, and the other three points are kept as recommended.
- The bare `push.services.mozilla.com` is allowed.
- A manager with a nurse profile gets the manager's kinds alone.
- An unknown kind's tap opens the app's home.
