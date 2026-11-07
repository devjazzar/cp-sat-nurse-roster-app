# Web Push for things with a deadline

Status: ready-for-agent
Type: enhancement
Published: 2026-11-07 by /to-spec

Spec drawn from the grilling of 2026-11-07 (three rounds, 23 questions, every recommendation taken). Vocabulary:
`GLOSSARY.md` (**Notification**, **Push subscription**, **Push**). Decisions and their reasons: `docs/ARCHITECTURE.md`,
`docs/adr/0012-web-push-carries-no-personal-data.md` and the ADRs it rests on (0001, 0006, 0009). Where this spec and those
documents disagree, the documents win and this spec is wrong.

## Problem Statement

**The bell is the only notification, and it is read only by someone who opens the app.** A Staff Nurse whose colleague
proposed a swap learns of it when she next signs in; if that is after the swap's first date, the swap has expired and the
colleague's plan is dead. A request window opens and closes while a nurse on nights never looks. A Unit Manager is not told
that a swap awaits him or that the approver sent his roster back until he opens the app; the CNO and the Deputy CNO learn of
a submitted roster the same way, while the month approaches. The design left email, SMS and push out of v1 on purpose, so
nothing of ours reaches a nurse outside the app.

**Anything that does reach a phone must say nothing about anyone.** A notification on a lock screen, in a shade or in a
screenshot is read by whoever holds the phone. The app's rule that no name, leave, date or unit of a nurse leaves the server
has to hold for a push too.

## Solution

**A push on the phone or desktop, through the browser's own push service, for the six kinds of notification that have a
deadline**, and for nothing else:

| Who is told | Of what | The push says |
|---|---|---|
| each colleague whose cells a swap changes | the swap is proposed, and expires when its first date passes | You have a swap to answer |
| the unit's manager | every colleague accepted, and the swap awaits his decision | A swap waits for your decision |
| the staff nurses of the target month | a request window opened, and closes on its date | Requests are open for a coming month |
| the unit's manager | a window closed with requests waiting, which expire at month close | Requests wait for your decision |
| the CNO and the Deputy CNO | a roster was submitted | A roster waits for your approval |
| the unit's manager | the approver rejected his roster | A roster was sent back to you |

Every push is titled "Nurse roster" and carries only which kind of thing waits. No name, no date, no month, no unit, no
identifier of a swap or a roster. Tapping it opens the app on the page for that kind (Swaps, the unit's swaps, My month,
Requests, the roster overview, the Roster page), at the page's own default month. A roster approved, a roster changed, a
solve's end, a decision on a request, the other steps of a swap and a month's close stay on the bell alone.

**Opt-in per device**, on the Notifications page, in a section about this device. "Turn on" asks the browser's permission
inside the tap and subscribes this device; "Turn off" ends it; "Turn off on every device" ends every subscription of the user,
for a phone that was lost. On an iPhone or iPad the app must first be added to the Home Screen, and the page says so.
Pressing Log out turns this device off; a session that merely expires does not, since reaching someone who is not using the
app is the point. Deactivating an account ends all its subscriptions.

**Nothing of ours but the worker reaches the internet.** The worker sends each push through one new network with a way out;
`web`, the database and the solver stay on internal networks as they are. The installation's own key pair identifies it to
the push services and is made at first start and kept in the database, so a backup restores the key with the devices bound
to it.

## User Stories

1. As a Staff Nurse, I want a push on my phone when a colleague proposes a swap that changes my cells, so that I answer before its first date passes and it expires.
2. As a Staff Nurse, I want a push when a request window opens for my unit, so that I make my requests before it closes.
3. As a Unit Manager, I want a push when a swap awaits my decision, so that it does not expire while I am away from the app.
4. As a Unit Manager, I want a push when a request window has closed with requests waiting, so that I decide them before the month closes and expires them.
5. As a Unit Manager, I want a push when an approver sends my roster back, so that I redo it before the month begins.
6. As the CNO or the Deputy CNO, I want a push when a roster is submitted, so that the unit is not left waiting for its roster.
7. As a Staff Nurse, I want a push to say only that something waits for me and never a name, a date or a unit, so that whoever sees my lock screen learns nothing about me or my colleagues.
8. As a nurse, I want a tap on the push to open the app on the right page, so that I go straight to the thing that waits.
9. As a nurse, I want a second push of the same kind to replace the first on my phone rather than pile up under it, so that my shade shows one line a kind.
10. As a nurse, I want a push that is a day old to be dropped rather than delivered late, so that I am not woken by stale news; the bell keeps the notification.
11. As a nurse who answered a swap on another device while this phone was off, I want no push about it to arrive afterwards, so that I am not told to answer what I have answered.
12. As a nurse, I want every roster approval, change and decision to stay on the bell and not on my phone, so that pushes stay rare and I keep them on.
13. As a nurse, I want to turn pushes on for this device from the Notifications page, with one tap that asks my browser's permission, so that I decide per device.
14. As a nurse, I want to turn pushes off for this device as easily, so that a device I no longer carry stops buzzing.
15. As a nurse who lost a phone, I want to turn pushes off on every device from any other device, so that the lost phone goes quiet.
16. As a nurse, I want the page to say whether this device is on and on how many devices pushes are on in all, so that I know what I have turned on.
17. As a nurse on an iPhone that has not added the app to the Home Screen, I want the page to tell me to add it first, so that I know why there is no button.
18. As a nurse on a browser that cannot receive pushes, I want the page to say so, so that I do not look for a button.
19. As a nurse who blocked notifications in the browser, I want the page to say they are blocked there, so that I know where to undo it.
20. As a nurse on a shared computer, I want Log out to turn this device's pushes off, so that the next person at the computer gets none of mine.
21. As a nurse, I want a session that expires on its own to leave my phone's pushes on, so that I keep being reached while I am not using the app.
22. As a nurse whose browser renewed its subscription behind the scenes, I want the app to carry on pushing to the new one without a visit, so that nothing is missed.
23. As a nurse whose permission or subscription the browser has withdrawn, I want the app to notice at the next send and stop, so that no dead address is kept.
24. As a nurse, I want a push to be shown even while the app is open on that device, so that the behaviour is the same everywhere and no browser shows a generic notice instead.
25. As a Unit Manager with a nurse profile, I want the kinds for a manager and for a nurse both, so that each thing that waits for me reaches me.
26. As the System Admin, I want deactivating an account to end its push subscriptions, so that a person who has left is reached by nothing of ours.
27. As the System Admin, I want the audit log to show who turned pushes on and off and when, and nothing of their device, so that the log holds a person's choice and no address.
28. As the System Admin, I want the health page to show how many pushes were sent and failed in the last day and the last failure's reason in fixed words, so that I know when the push services are unreachable from the server.
29. As the System Admin, I want the same two numbers on the metrics endpoint, so that the hospital's monitoring alerts on failures.
30. As the hospital's IT, I want the install guide to name the push services' hosts the server must reach, so that the firewall can allow them and nothing else.
31. As the hospital's IT, I want the solver, the database and `web` to stay unreachable from and to the internet, so that opening a way out for pushes widens nothing else.
32. As the hospital's IT, I want the installation's key pair made at first start with no step of mine, so that `docker compose up -d` with the `.env` file stays the whole installation.
33. As the hospital's IT, I want a restore from a backup to keep every device's subscription working, so that a recovery does not silently end everyone's pushes.
34. As the hospital's IT, I want a command to replace the key pair after a compromise, after which each device re-subscribes on its next visit without being asked again, so that a leaked key is retired without a campaign.
35. As the hospital's IT, I want a blocked outbound connection to lose pushes and nothing else, so that the app works as before behind a strict firewall and the health page says what is lost.
36. As a developer, I want the sending library behind one module of ours, so that it can be replaced without touching the events, the pages or the worker.
37. As a developer, I want a feature with a new deadline (such as a cover offered) to add one kind code and its words and nothing else, so that pushes grow with the app.

## Implementation Decisions

### What is pushed

- **Kind codes**, one per row of the table in Solution: `swap_to_answer`, `swap_to_decide`, `requests_open`,
  `requests_to_decide`, `roster_to_approve`, `roster_sent_back`. The kind of a notification follows from its event and, for
  a swap, its step: swap step `proposed` and `awaiting`, window opened, window closed (the manager's, which is sent only
  when requests wait), roster submitted, roster rejected. Every other event and step has no kind and is never pushed.
- **The payload is the kind code alone**, as a small JSON object, encrypted end to end as Web Push requires. The service
  worker holds the title, the words and the page for each kind. The words are those of the table, title "Nurse roster".
- **Headers to the push service:** a time to live of 24 hours, urgency normal, and a topic equal to the kind, so an
  undelivered push of the same kind is replaced at the push service too. The notification shown carries the kind as its
  tag, so a second of the same kind replaces the first in the device's shade.
- **Always shown.** The service worker shows a notification for every push, whether or not the app is open and focused on
  that device.
- **Tap:** the service worker closes the notification, then focuses an open window of the app and sends it to the kind's
  page, or opens a new window on that page. The page is reached by its address with no month, so it shows its default. The
  page per kind: Swaps for `swap_to_answer`, the unit's swaps for `swap_to_decide`, My month for `requests_open`, Requests
  for `requests_to_decide`, the roster overview for `roster_to_approve`, the Roster page for `roster_sent_back`.

### Who sends, and when

- **The worker sends.** The one way to tell users something (`notifications.sending.notify`) stays the only entry: after
  writing the notification rows, and only when the event and step have a kind, it defers one push job carrying those rows'
  identifiers, inside the same transaction, so the job commits or rolls back with the rows (ADR 0006). One job per call,
  however many users it tells.
- **The job** runs under its own lock named `push`, as ADR 0009 requires of every job, so pushes go one job at a time and a
  waiting one takes no slot. When a send fails for a reason other than a dead subscription, the job tries again, three times
  over about ten minutes, **only the subscriptions that failed that way**: those reached, ended or skipped are not sent to
  again (the simplest shape is the job carrying the remaining subscriptions forward with a delay; the bookkeeping is the
  implementer's). Each attempt is recorded once per subscription, and the health page counts attempts, never jobs.
- **Before each send the job checks the thing still waits**, and that the reader still has a page for it (the rule the
  Notifications page already applies: a manager taken off the unit gets no link, so no push). Still waits, by kind: a swap still `pending` (to answer) or
  `awaiting_manager` (to decide); a request window still open (`requests_open`), or closed with requests still `pending`
  (`requests_to_decide`); a roster still `submitted` (to approve); a rejected roster still a `draft` not resubmitted since
  (`roster_sent_back`). A thing that no longer waits sends nothing, with no failure counted and no retry.
- **Per subscription:** a success resets the failure count and sets the last success. A 404 or 410 ends the subscription at
  once. Any other failure (unreachable, timed out, 429, 5xx, a refusal such as 401, 403 or 413) adds one to the failures in a
  row; at ten, the subscription ends. These ends are nobody's act and have no audit entry.
- **The sending module** (`notifications.pushing`) is the only place the library (pywebpush, pinned at 2.5.x) is imported,
  and the only place that knows the push services' protocol, headers, encryption and status codes. The rest of the app asks
  it to send a kind to a subscription and gets back an outcome in the app's own words: sent, gone, refused, unreachable. In
  tests it is replaced by a scripted stand-in, as the solver client is.
- **Attempts are recorded**, append-only with a bigint key (ADR 0007): when, the outcome, and nothing of the user or the
  device. The health page reads the last 24 hours from them; the daily retention removes attempts older than seven days,
  beside the queue rows it already removes.

### The subscription and the key pair

- **Push subscription** (new table in the notifications app, UUIDv7 key): user, the push service's address (unique), the two
  keys the browser gave, when it was turned on, failures in a row, last success. No user agent, device name or IP. An address
  belongs to whoever last subscribed it: subscribing an address another user holds moves it to the signed-in user.
- **Ends of a subscription:** turned off on the page (this device, or every device of the user), Log out (this device),
  deactivation of the user (every device; beside ending their sessions, in both the single and the end-of-day deactivation),
  404 or 410 from the push service, ten failures in a row. Rows are deleted, since a subscription is no one's record. No
  retention run: a live subscription costs nothing.
- **Key pair** (one row, in the notifications app): the VAPID private and public keys and when they were made. `prepare`
  makes the pair at first start when none exists, logging that it did. The private key sits in the database like every other
  secret the database holds (sessions, password hashes) and is covered by the backup and the restore.
- **Rotation:** a management command `rotate_push_keys` replaces the pair and writes an audit entry from the server with no
  actor, as the admin password reset does. It deletes no subscription. Sends to subscriptions bound to the old key fail as
  refusals and count toward the ten; each device re-subscribes on its next visit to the Notifications page (below). No
  scheduled rotation.

### API

Under the notifications router, every call for the signed-in user only, none taking a user:

- **Read this device's state**, a POST taking the browser's current subscription address if it has one, answering the
  installation's public key, whether this device is on (the address is held for this user), and how many devices of the
  user are on. A POST because the address is a capability and goes in no query string.
- **Turn on**, a POST taking the address and the two keys, and optionally the address it replaces (for a browser that
  renewed its subscription, or a device re-subscribing after a rotation): creates the subscription, or moves an address held
  by another user, or replaces the old address. Idempotent for the same user and address. Writes `push.turned_on` unless it
  only replaced an address or repeated an existing one.
- **Turn off this device**, a POST taking the address: deletes it if held by this user, answering the same whether or not it
  was. Writes `push.turned_off`.
- **Turn off every device**: deletes every subscription of the user. Writes one `push.turned_off`.
- **Audit entries:** actor the user, target their username, before and after holding nothing of the device. The renewal of
  an address and the ending by the push service write nothing.
- The health answer gains a push block: pushes sent and failed in the last 24 hours, and the last failure's reason as one of
  `unreachable`, `refused`, `gone`, or none. The metrics endpoint gains the two counts as gauges worked out at scrape, as
  its others are. The OpenAPI document and the generated client are regenerated.

### Frontend

- **The service worker** gains `push` and `notificationclick` listeners and still no `fetch` listener; ticket 23's rules
  on what must never be cached are untouched. Its `pushsubscriptionchange` listener re-subscribes with the current public
  key and tells the server the new address with the old one it replaces. Its test, which today asserts exactly the install
  and activate listeners, asserts instead that there is no `fetch` listener, and tests the new three.
- **The Notifications page** gains a section, "On this device", above or below the list, in these states, decided by
  feature detection and the browser's permission state, never by browser name:
  - the browser has no push support: "This browser cannot receive pushes.";
  - an iPhone or iPad not running as a Home Screen web app: "Add the app to your Home Screen to turn these on." with the
    Share, Add to Home Screen steps in a line;
  - permission denied: "Notifications are blocked for this site in your browser's settings.";
  - off: a line saying what a push tells ("You are told when a swap, a request window or a roster waits for you, and
    nothing more.") and a **Turn on** button;
  - on: "Pushes are on for this device." and a **Turn off** button;
  - when the user has one device or more: "Pushes are on on N devices." and **Turn off on every device**.
- **Turn on** runs inside the click: ask permission, subscribe with the installation's public key, send the subscription to
  the server, then show the new state. A refusal of permission shows the blocked state. Every step's failure is said in a
  status line in the page's existing style.
- **At every start of the app** for a signed-in user, where the service worker is registered, with permission granted and
  a browser subscription present: the app reads this device's state; a subscription the server holds but bound to a public
  key other than the server's is replaced silently (unsubscribe, subscribe with the new key, turn on with the old address as
  replaced), which needs no new permission, so a device re-subscribes after a rotation whether or not its user ever opens
  the Notifications page. A browser subscription the server does not hold is left alone and shows as off on the page (so
  "Turn off on every device" from another device is not undone by a visit).
- **Turn off** unsubscribes in the browser and tells the server; **Log out** does the same for this device before signing
  out, and signs out whether or not the server call succeeded. The bell, the list and the rest of the page are unchanged.
- Controls are 44 px on a touch screen as the page's others are; the section's state is announced in a status region.

### Deployment and documents

- **`deploy/compose.yaml`** gains a network `egress`, not internal, joined by the worker only (`backend`, `solver`,
  `egress`); `web`, `db`, `solver` and `caddy` are unchanged. The development and browser-check compose files give the
  worker a way out as their other services have one.
- **The image** gains the sending library as a backend dependency; a rebuild follows.
- **`docs/ARCHITECTURE.md`:** section 1 and 12 no longer list push as out of scope or to revisit; section 2's table gives
  the worker `egress` and the configuration paragraph says nothing new (no variable); section 7 adds the push job and the
  attempts' retention; section 8 says what is pushed, how a device opts in and what the health page shows; section 9's
  housekeeping lists attempts after seven days. ADR 0012 is already written; ADR 0001's claim about the solver still holds.
- **`deploy/INSTALL.md`** gains a section naming the hosts the worker must reach over HTTPS: `*.push.apple.com`,
  `fcm.googleapis.com`, `*.push.services.mozilla.com`, `*.notify.windows.com`; a hospital that blocks them loses pushes
  and nothing else, and the health page says so.
- **Glossary:** Push subscription and Push are written. No new term.

## Testing Decisions

- **What a good test is here:** it drives a public interface and checks what a user, a device or the System Admin gets:
  which users a push job is made for, what reaches the stand-in push service and with which headers, which page a tap
  opens, what the Notifications page says, what the audit log and the health page show. It does not read the job table's
  columns, the service worker's internals or the library's calls, and it never asserts that something did *not* happen by
  waiting.
- **Seam 1, the backend suite** (pytest on a throwaway PostgreSQL 18 container, the real queue run for the job tests as
  the solves' tests run it), with the sending module replaced by a scripted stand-in that records every send (subscription,
  kind, headers) and answers what the test scripts (sent, 404, 410, 429, 5xx, unreachable):
  - each of the six events and steps makes one job for its recipients and nobody else; every other event and step makes
    none; a rolled-back change makes none;
  - the payload is the kind code and nothing else, and the headers are the kind as topic, 24 hours, urgency normal;
  - the still-waits check for each kind: answered, decided, closed, approved or resubmitted since means no send;
  - 404 and 410 end the subscription at once; other failures count and the tenth ends it; a success resets the count;
  - a retry reaches only the subscriptions that failed transiently, once more each, and each attempt counts once per
    subscription on the health page;
  - the four endpoints: state, turn on (new, moved from another user, replaced address, repeated), turn off this device
    (held, not held, another user's), turn off every device; each audit entry and its emptiness of the device; each a 401
    when signed out;
  - Log out's turning off, and deactivation ending every subscription in both the single and the end-of-day paths;
  - `prepare` making a key pair once and keeping it; `rotate_push_keys` replacing it with an audit entry from the server;
  - the health block's counts and last reason, and the two metrics; attempts removed after seven days by the retention;
  - a manager with a nurse profile getting both roles' kinds; the System Admin getting none.
  - Prior art: the notifications app's event and reading tests, the solves' scripted solver and its real-queue fixture,
    the ops app's health, metrics, retention and installation tests, the accounts' deactivation tests.
- **Seam 2, the frontend's app-level Vitest suite** (the whole app at an address over a mocked API; `start` and `hold`,
  ticket 11's rules), with `navigator.serviceWorker`, `PushManager`, `Notification` and the standalone display mode stubbed
  per test:
  - the section's six states by feature detection and permission;
  - Turn on asking permission, subscribing with the server's key and posting the subscription, then showing on; a refusal
    showing blocked;
  - a browser subscription the server does not hold shown as off; one bound to an old key replaced silently at app start;
  - Turn off and Turn off on every device, and the status line's words; Log out turning this device off first;
  - 44 px controls on a coarse pointer. Prior art: the notifications page tests, the PWA and header tests from ticket 23,
    the session tests from ticket 25.
- **Seam 3, the service worker's own test** (the worker run against a stand-in of its global scope, as today): a push
  shows a notification with the kind's title, words and tag; an unknown kind shows the title alone; a tap focuses an open
  window and sends it to the page, or opens one; `pushsubscriptionchange` re-subscribes and posts the replacement; the
  listeners include no `fetch`.
- **Seam 4, the compose-level operations check** (`deploy/tests/operations.sh` on a scratch project): the worker is on a
  network that is not internal and `web`, the database and the solver are on none (what the compose change promises; whether
  the hospital's firewall lets it out is the install checklist's); the health answer carries the push block; `prepare`
  logged the key pair. **No Playwright check** is added: a browser push needs a real push service, which the checks' stacks cannot and
  must not reach; the browser side is seam 2 and 3.
- The backend's `makemigrations --check` stays clean; the OpenAPI document matches the export; six parallel frontend runs
  pass.

## Out of Scope

- Email, SMS, any provider or service of ours, and any push of a kind without a deadline (roster approved or changed, a
  solve's end, a request's decision, the other swap steps, month close). A cover offered is another feature's kind to add.
- A badge count on the app's icon, sounds, actions on the notification, or a notification that says more than its kind.
- Choosing which kinds to receive, quiet hours, or a hospital-wide switch: opt-in is per device, all six kinds or none.
- Naming devices, listing them, or turning one off from another device (only all at once).
- A push when a session expires, or ending subscriptions when a password changes.
- Scheduled key rotation, or keys in `.env`.
- Arabic or any second language for the words, with the rest of the app.
- Browser checks of a real push; dark mode and anything else ticket 23 did not check.

## Further Notes

- **Decisions this spec took beyond the grilling**, none reversing an agreed one, each the user's to veto: attempts kept in
  an append-only table and removed after seven days (a new housekeeping line); the rotation command writing an audit entry
  from the server with no actor; an address moving to whoever last subscribed it; a retry reaching only the subscriptions
  that failed; the key check at app start rather than on the Notifications page alone.

- **Browser facts the implementer should not re-research:** iOS and iPadOS deliver Web Push only to a web app added to the
  Home Screen with a `standalone` or `fullscreen` manifest (ticket 23 set `standalone`), and allow the permission question
  only inside a user gesture; Chrome requires `userVisibleOnly` and shows a generic notice when a push shows no notification;
  a 404 or 410 from any push service means the subscription is gone; Apple's service sometimes answers success for a dead
  one, which the ten-failure count does not catch and the bell covers.
- **The library:** pywebpush 2.5.0 (one maintainer, a PyPI critical project; depends on `cryptography`, `http-ece`,
  `py-vapid`, `requests`, `aiohttp`). It is why `notifications.pushing` is the only importer. Python 3.14 is the image's
  version: the ticket confirms the library installs and sends there before building on it.
- **The dev stack** needs a rebuild (a new dependency, `compose.yaml` changed) and `up -d` to create the `egress` network;
  the main session does that when the branch reaches `main`. Vite serves the changed service worker at once.
- **Tickets** (`/to-tickets`) can split along: the backend (subscriptions, key pair, job, endpoints, health, retention,
  compose and documents) and the frontend (service worker, the page section, Log out), the first blocking the second, or one
  ticket if the user prefers one session.
