# 40: A device turns pushes on and off

**What to build:** A signed-in user opens the Notifications page and finds a section about this device. On a browser that can receive pushes they tap **Turn on**; the browser asks its permission inside that tap, the device subscribes with the installation's own public key, and the page says "Pushes are on for this device." and on how many devices pushes are on in all. **Turn off** ends this device's push subscription; **Turn off on every device** ends every one of theirs, from any device. On an iPhone or iPad not added to the Home Screen the page says to add it first; a browser without push support, or one where notifications are blocked, is told so in a line. Pressing Log out turns this device off first; a session that expires on its own leaves it on. Deactivating an account ends all its push subscriptions. The audit log shows who turned pushes on and off and when, and nothing of the device. The installation's key pair is made at first start with no step of the hospital's, and a command replaces it after a compromise, after which each device re-subscribes silently at its next start of the app. Nothing is sent yet: that is ticket 41.

Spec: `.scratch/nurse-rostering-v2/specs/web-push-for-deadlines.md`. Words: `GLOSSARY.md` (Push subscription, Push). Reasons: `docs/adr/0012-web-push-carries-no-personal-data.md`.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [x] A one-row key pair (VAPID) in the notifications app, made by `prepare` at first start when none exists and logged; kept across later starts and restored with a backup
- [x] A management command `rotate_push_keys` replaces the pair, deletes no push subscription, and writes an audit entry from the server with no actor
- [x] The push subscription table: user, the push service's address (unique), the browser's two keys, turned on at, failures in a row, last success; no user agent, device name or IP; UUIDv7 key
- [x] API, for the signed-in user only, none taking a user: read this device's state (a POST taking the browser's address if any; answers the public key, whether this device is on, how many devices are on); turn on (address, keys, optional replaced address; creates, moves an address held by another user to this one, or replaces the old address; idempotent); turn off this device (the same answer held or not); turn off every device
- [x] Audit entries `push.turned_on` and `push.turned_off` (actor the user, target their username, nothing of the device); none for a repeated turn on, a replaced address, or an ending by the server
- [x] Log out ends this device's subscription (the page unsubscribes in the browser and tells the server before signing out, and signs out whether or not that call succeeded); an expired session ends none
- [x] Deactivation ends every subscription of the user, in both the single deactivation and the end-of-day one, beside ending their sessions
- [x] The Notifications page's section "On this device" in its states, by feature detection and permission state only: no push support; an iPhone or iPad not running as a Home Screen web app; permission denied; off (what a push tells, and Turn on); on (Pushes are on for this device, and Turn off); the device count and Turn off on every device
- [x] Turn on runs inside the click: permission, subscribe with the server's public key (`userVisibleOnly`), post the subscription, show the new state; a refusal shows the blocked state; failures are said in the page's status line
- [x] At app start for a signed-in user with permission granted and a browser subscription present: a subscription the server holds but bound to another public key is replaced silently (unsubscribe, subscribe with the new key, turn on with the old address as replaced); one the server does not hold is left alone and shows as off
- [x] The service worker's `pushsubscriptionchange` listener re-subscribes with the current public key and tells the server the new address with the old one it replaces; still no `fetch` listener, and its test asserts that instead of the exact two listeners
- [x] Controls 44 px on a touch screen; the section's state announced in a status region
- [x] Tests at the agreed seams: the backend suite (key pair made once and kept, rotation with its audit entry, the four calls in every case including another user's address, each a 401 signed out, the audit entries, Log out, both deactivation paths); the frontend app-level suite with `PushManager`, `Notification`, the service worker registration and the standalone mode stubbed (the six states, Turn on's steps and a refusal, the app-start replacement and the not-held case, Turn off and Turn off on every device, Log out, 44 px); the service worker's test (`pushsubscriptionchange`, no `fetch`)
- [x] `makemigrations --check` clean; the OpenAPI document matches the export and the client is regenerated; six parallel frontend runs pass

**Implemented on 2026-11-10,** on branch `claude/ticket-40-push-on-off-9a72bf`, draft pull request
Nurse-Fold/cp-sat-nurse-roster-app#28, from `main` at `0ac72d8`. The commits:
- `6195029`: the backend, its tests and the regenerated client;
- `a4e4df9`: the frontend, the service worker and their tests;
- `091b6a2`: the push calls added to the authorization test's list, and a leave test that failed on its own dates (below);
- `616c3e6`: the review's points;
- `origin/main` merged in (the certificates spec and glossary; no file of this ticket's);
- then this comment.

The suites ran locally, one at a time under the heavy-run lock, on a throwaway PostgreSQL 18 container of my own:
- the backend, on `a4e4df9`: 2953 passed and 2 failed. Both are fixed in `091b6a2`, and their files pass in full (791 and 76);
- the frontend, on `a4e4df9`: one `npm test` run, 723 passed, and `npm run build` succeeded;
- `makemigrations --check`: "No changes detected";
- the OpenAPI document and the client were regenerated from the export, after both API commits.

After `616c3e6` I reran `notifications/tests/test_push.py` (39 passed), the frontend's push tests (23 passed), the service
worker's test (7 passed) and the typecheck. GitHub ran every suite, and the six parallel frontend runs, on that head.

**What the dev stack needs:** a **rebuild** (`docker compose up -d --build`).
- One new backend dependency: `cryptography` (50.0.x), with `uv.lock`.
- One migration, `notifications/0007_push`.
- No change to compose, the `Dockerfile` or the solver.

At its first start after the rebuild, `web` makes the key pair and logs "Made the installation's push key pair.".

**What was built, criterion by criterion.**
- **The key pair:** `notifications.PushKeyPair`, one row, `pk=1` under a check constraint.
  - The private key is a PEM (PKCS #8, P-256). The public key is the uncompressed point in base64url, as
    `applicationServerKey` takes it.
  - `notifications.push_keys.ensure()` makes it. `bootstrap` (so `prepare`) calls it before its early return, so an
    installation that predates the ticket gets one too, and prints the line above.
  - A later start keeps the pair and prints nothing.
  - A backup is a whole-database `pg_dump`, so a restore brings the pair back with the subscriptions. That needs nothing
    new.
- **`rotate_push_keys`** writes a new pair and its time, deletes no subscription, and records `push.keys_rotated` with no
  actor and `after: {"from": "the server"}`, as the admin password reset does.
- **`PushSubscription`:** user, `endpoint` (unique), `p256dh`, `auth`, `turned_on_at`, `failures_in_a_row` and
  `last_success_at`, with a UUIDv7 key. It holds no user agent, name or IP.
- **The four calls** sit under `/api/notifications/push/`, all POST, none taking a user (`notifications.push_api` and
  `notifications.subscriptions`):
  - `state` takes the browser's address, if any, and answers the public key, `this_device` and `devices`.
  - `on` takes the address, the two keys and an optional `replaces`. It creates the row, or moves an address another user
    holds to this one, or replaces the old address. It is idempotent per user and address, and one user's calls are
    serialised on their row.
  - `off` answers the same whether or not the address was theirs.
  - `off-everywhere` ends every subscription of the user.
  - The two turn-offs are also open during a forced password change, because Log out is.
- **The audit:** `push.turned_on` and `push.turned_off` have the user as actor and their username as target. `before`,
  `after` and the IP are all empty. A repeated turn-on, a replaced address, a turn-off of nothing and a deactivation
  write none.
- **Log out** (`session.ts`): the page ends this device's browser subscription, tells the server, then signs out whether
  or not that call succeeded. An expired session ends nothing.
- **Deactivation:** `subscriptions.end_for` sits beside `_end_sessions` in both `deactivate` and `deactivate_many`. That
  covers a manager deactivated by the System Admin, a nurse whose end date is today and the hourly end-of-day job.
- **The page:** "On this device" sits above the list on the Notifications page (`components/push-on-this-device.tsx`,
  `lib/push.ts`). Its states come from feature detection and the permission, in this order:
  - an iPhone or iPad not run from the Home Screen: Safari's `navigator.standalone` on a touch screen, checked first,
    because Safari there has no `PushManager`;
  - no push support;
  - blocked;
  - off;
  - on;
  - and, with one device or more, the count and Turn off on every device.

  The words are the spec's. The section's state and every failure are in one status region named by its heading.
- **Turn on** asks for permission before anything else is awaited, ends a browser subscription made with another key,
  subscribes with `userVisibleOnly`, posts and shows the new state. A refusal shows the blocked state. A dismissed
  question, a failed subscribe and a failed post each have their own line.
- **At each start** (`_signed-in.tsx`, once per mount): with permission granted and a browser subscription present, the
  app reads the state.
  - A subscription the server holds but bound to another key is ended, made again with the new key and posted with the
    old address as `replaces`, with no question.
  - One the server does not hold is left alone.
- **The service worker** gains `pushsubscriptionchange`.
  - It reads the CSRF token from `cookieStore` and asks the state for the old address. Only if that address is held does
    it subscribe with the current key and post the new address with `replaces`.
  - Still no `fetch` listener; the test asserts exactly that instead of the two listeners.
- **Controls** are the page's `Button`, 44 px on a coarse pointer.
- **Tests at the agreed seams:**
  - `notifications/tests/test_push.py` (39): the key pair made once, kept, a valid P-256 point matching its private key;
    rotation, its time and its entry; every case of the four calls, another user's address included; each 401; the entries
    and their emptiness; turning off during a forced change; Log out.
  - `accounts/tests/test_users.py` and `nurses/tests/test_end_dates.py`: both deactivation paths, and an end date of today.
  - `src/app.test.tsx`, "pushes on this device" (23): the six states, an iPhone from the Home Screen, Turn on's steps and
    each failure, Turn off and its failure, every device, the start's replacement, the not-held and current-key cases,
    Log out (also with the server failing and with notifications blocked since), and 44 px.
  - `src/sw.test.ts`: the renewal, the not-held case, no token, no old subscription, and no `fetch`.

**What was driven, and how.** I used my own scratch stack, `e2e/stack.sh up t40` (ports 18480 and 18943), on 10 November
2026.
- **The browser:** the installed Google Chrome, driven by Playwright with fresh profiles, against the stack's Caddy over
  HTTPS. Notifications were granted to that origin, and the certificate check was off in that throwaway browser for
  Caddy's self-signed certificate, as the browser checks do.
  - The desktop app's browser pane refused the self-signed certificate. On `http://localhost` its notifications were
    `denied` and could not be asked again, so it could not drive Turn on.
  - Each subscription was a real one with Google's push service (`fcm.googleapis.com`). The first one in a fresh profile
    took about ten seconds.
- **As Amal.**
  - Turn on: "Pushes are on for this device.", a row on the server and a subscription in the browser. Turn off: back to
    off, and the row and the browser subscription were gone.
  - A second profile, the laptop, turned on: "Pushes are on on 2 devices.". From it, Turn off on every device left no row.
  - The phone's next start then showed off and kept its browser subscription, and the server still held none.
- **Log out.** With both devices on, Log out on the phone left one row (the laptop's) and no browser subscription on the
  phone.
- **Rotation.** `docker exec t40-web-1 python manage.py rotate_push_keys` printed its line. At the laptop's next start
  (`/`), it re-subscribed with the new key at a new address. The server held that address, not the old one, still one row,
  and the page read on.
- **Deactivation.**
  - Omar (a manager) turned on, then the System Admin deactivated him through `POST /api/users/{id}/deactivate` (200). His
    rows: 0.
  - Badr turned on. His end date was set to today in the database, the clock moved two days, and
    `nurses.tasks.close_ended_nurses` was fired. He was deactivated and his rows were 0.
- **The audit**, read in the database:
  - `push.turned_on` and `push.turned_off` by Amal, Omar and Badr: actor and target themselves, `before`, `after` and
    `ip` all null;
  - `push.keys_rotated` with no actor and `{"from": "the server"}`;
  - the deactivations' own `user.deactivated`, and no push entry of theirs.
- **At 375 px** with touch, Turn on and Turn off on every device measured 44 px, and the page did not scroll sideways.
- The first start's log was not read: the stack was rebuilt before driving and the new container's log replaced it. The
  pair from the first start (00:15) was still the one in use after the rebuild's start.

The stack is down and its volumes gone.

**What was found, and fixed.**
- `nurses/tests/test_leave.py::test_the_system_admin_reads_no_type_no_date_and_no_count_in_the_log` failed on 10 and 11
  November 2026. It looked for the leave's dates in the whole entry, and the entry's own time is today. It now leaves the
  time out.
- The authorization test's list of calls any role may make gained the four push calls.

**Findings for you, not fixed:** none.

**What was NOT checked.**
- **An iPhone or iPad.** The Home Screen state, Safari's push and its permission inside a tap were checked only with stubs.
- **`pushsubscriptionchange` in a real browser.** A browser cannot be made to renew a subscription on demand, so the
  service worker's test is all there is.
- **A push sent:** that is ticket 41's.
- **A restore** bringing the pair back. That is by the whole-database dump, not driven here; ticket 42's
  `operations.sh` covers restores.
- **The blocked and unsupported states in a real browser** beyond the pane's own "blocked", which it showed correctly.
- **A screen reader**, beyond the accessibility tree and the status region.
- **The six parallel frontend runs and the browser checks, locally:** GitHub runs them on the pull request.

**Decisions taken here.**
- **`cryptography` alone, pinned `>=50.0.2,<51`**, for the key pair. pywebpush is left for ticket 41, whose criterion is to
  confirm it installs and sends on Python 3.14 before building on it. It depends on `cryptography` itself.
- **The private key is a PEM**, and the public key is what `applicationServerKey` takes.
- **The key pair is also made on demand** when a call reads it and there is none (a test, or a database `prepare` never
  ran on), so a read never fails. `prepare` remains what makes it on an installation.
- **No IP on the push entries:** `record` gets no request. A turn-on happens on the device, so its IP is the device's
  network. Other entries keep theirs.
- **An entry only when something changed:** a turn-off of an address not held, or every device when there were none,
  writes nothing.
- **A replacement of an address no longer held turns nothing on** (the review's point). Turning off on every device from
  another device is therefore never undone by a renewal, at a device's start or in its worker.
- **Turn off tells the server first, then ends the browser's subscription**, so a failure leaves the device as it was.
  **Log out ends the browser's first**, since the next person at a shared computer must get none, whatever the server
  answers.
- **Turn off on every device also ends this browser's own subscription.**

**Worth your review.**
- **The service worker's renewal needs `cookieStore`** for the CSRF token. A worker cannot read `document.cookie`, and
  exempting a call from CSRF was not considered. Browsers whose worker lacks `cookieStore`, or that give no
  `oldSubscription`, renew nothing there. The device then shows as off at its next visit and needs Turn on again. The
  app's own check at each start covers only a rotated key, since a renewed address the server does not hold is "left
  alone" by the spec. **Recommendation:** keep it, and watch ticket 42's failure counts.
- **The start's replacement is not atomic.** It must end the old browser subscription before subscribing with the new
  key, because a browser holds one.
  - If the subscribe or the post then fails, the device is off. The server keeps the old row until ticket 41's ten failed
    sends end it, and counts it among "on N devices" until then.
  - **Recommendation:** accept it. It happens only after a rotation, which is rare.
- **An address is any `https://` URL** (2000 characters at most). Ticket 41's worker will send to it from three networks.
  - Refusing hosts other than the four push services, at turn-on or at send, would close a request-forgery path through the
    worker.
  - **Recommendation:** decide before ticket 41 starts. A note on ticket 41 says so.
- **The word "device"** is in the API (`this_device`, `devices`) and the code, as the page's "On this device" and "on N
  devices" are, though the glossary lists it under _Avoid_ for a push subscription. Each is about the physical device, not
  the subscription. Renaming the API fields to `this_subscription` and `subscriptions` is cheap now if you want it.

**Review.** `code-review` against `0ac72d8` ran its two axes in parallel.
- **Spec.** Fixed in `616c3e6`:
  - the rotation now dates its pair;
  - a renewal of an address no longer held turns nothing on (the race with Turn off on every device);
  - Log out ends this device's subscription even when notifications were blocked since.

  Kept: the non-atomic replacement and the service worker's limits, above; the leave test fix and the on-demand key pair,
  which are decisions above; and Turn on's awaits before `subscribe`, since only the permission question needs the tap.
- **Standards:** no hard breach. Fixed:
  - two tests that showed nothing happened by counting calls now answer both reads inside `act` before looking;
  - Turn off on every device and the query key moved into `lib/push`;
  - the unused `SAID.blocked` is gone;
  - `sent()` is `subscriptionBody()`;
  - the public key's read makes no extra query;
  - the two copies of `bytesOf` and of the renewal point at each other.

  Kept:
  - "device" (above);
  - `ARCHITECTURE.md`, left to ticket 42 with a note there;
  - the repeated counters in `turn_on`'s branches, which read plainer than a helper.

**Things later tickets should know.**
- **Ticket 41:** see the note on it.
  - Hand pywebpush a `Vapid.from_pem(...)`.
  - `failures_in_a_row` and `last_success_at` are yours to write.
  - Ending a row is a plain delete with no entry.
  - Decide on the hosts.
  - The service worker's test takes `self`, `caches` and `fetch` as parameters.
- **Ticket 42:** see the note on it.
  - `prepare`'s line is "Made the installation's push key pair.".
  - The architecture's sections 2 and 8, and the security paragraph's audit actions, are yours.
- **Any page can read this device's state** through `lib/push` (`deviceState`, `PUSH_STATE_KEY`). Log out already goes
  through `turnThisDeviceOffForLogOut`.

**Reviewed by the user (2026-11-10):** all four points kept as recommended.
- The worker's renewal needs `cookieStore`; watch ticket 42's failure counts.
- The start's replacement is not atomic; accepted.
- Push addresses are to be limited to the push services' hosts, in ticket 41.
- "device" stays in the API and on the page.
