# 42: The System Admin and the hospital's IT see pushes working

**What to build:** The System Admin's health page says how many pushes were sent and how many failed in the last 24 hours and, in fixed words, why the last one failed (unreachable, refused, gone), and the metrics endpoint carries the same two numbers for the hospital's monitoring. Attempts older than seven days are removed by the daily retention. The install guide names the push services' hosts the server must let the worker reach, and says that a hospital that blocks them loses pushes and nothing else. The architecture says pushes are in, who sends them and through which network, what a device opts into and what housekeeping removes.

Spec: `.scratch/nurse-rostering-v2/specs/web-push-for-deadlines.md`.

**Blocked by:** 41 A push reaches the device and a tap opens the page

**Status:** ready-for-agent

- [ ] The health answer and page gain a push block: sent and failed in the last 24 hours (attempts, never jobs), and the last failure's reason as `unreachable`, `refused`, `gone` or none; the OpenAPI document and the client regenerated
- [ ] `/metrics` gains the two counts as gauges worked out at scrape, as its others are
- [ ] The daily retention removes attempts older than seven days, under a lock of its own name like the others; the health page's counts are unaffected
- [ ] `deploy/INSTALL.md`: a section on pushes naming `*.push.apple.com`, `fcm.googleapis.com`, `*.push.services.mozilla.com` and `*.notify.windows.com` over HTTPS from the worker; what a blocked firewall loses; the health line as the check; an item on the install checklist
- [ ] `docs/ARCHITECTURE.md`: sections 1 and 12 no longer list push as out of scope or to revisit; section 2's table gives the worker `egress`; section 7 adds the push job and the attempts' retention; section 8 says what is pushed, how a device opts in, what Log out and deactivation do and what the health page shows; section 9's housekeeping lists attempts after seven days
- [ ] `deploy/tests/operations.sh`: the worker is on a network that is not internal and `web`, the database and the solver are on none; the health answer carries the push block; `prepare` logged the key pair
- [ ] Tests at the agreed seams: the backend suite (the health block's counts and last reason from scripted attempts, the two metrics, the retention's what goes and what stays); the operations check above

**From ticket 40 (2026-11-10):**
- **`prepare` logs "Made the installation's push key pair."** once, on the start that makes it: `bootstrap` prints it and
  `prepare` turns each printed line into a JSON log line of logger `ops.prepare`. That is the line for `operations.sh` to find
  in `web`'s first-start logs. A later start prints nothing about the pair.
- **Docs ticket 40 left for this one.** `docs/ARCHITECTURE.md` section 8 still says the PWA's worker sends "no push". It now
  listens for `pushsubscriptionchange` (still no `fetch`), and the Notifications page has "On this device". Section 2's
  first start does not mention the key pair, and `rotate_push_keys` is in neither section. Section 8's security paragraph
  does not list `push.turned_on`, `push.turned_off` or `push.keys_rotated`, all three of which hold nothing of the device
  and no IP.
- **Backups and restores need nothing new.** `ops.backups` takes a whole-database `pg_dump`, so the key pair and the
  subscriptions come back with a restore.

**From ticket 41 (2026-11-10):** pushes are sent. What this ticket builds on:
- **The attempts:** `notifications.models.PushAttempt`, one row a send to one subscription (`at`, indexed, and `outcome`:
  `sent`, `gone`, `refused` or `unreachable`). A retry's every try is a row, so the 24 hours' counts are attempts, as the spec
  says. The last failure's reason is the latest row that is not `sent`. Nothing writes to it but `notifications.pushes`, and
  nothing removes it yet: the seven days' retention is yours.
- **The hosts** in `notifications.subscriptions` (`PUSH_SERVICE_HOSTS`, `PUSH_SERVICE_DOMAINS`) are what the install guide
  should name: `fcm.googleapis.com`; `push.services.mozilla.com` and any name under it (the bare host is allowed too, as
  Mozilla's own examples use it); any name under `push.apple.com`; any name under `notify.windows.com`. Ticket 41's comment
  cites each service's page. Only HTTPS on 443.
- **The networks:** the worker is on `backend`, `solver` and `egress`; only `egress` is not internal. Check it on the
  operations stack (`deploy/compose.yaml` with `deploy/tests/compose.test.yaml`), where `web` stays internal. Under
  `e2e/compose.e2e.yaml` `web` is also on `public`, for the browser checks' HTTP port.
- **For section 7:** the job `notifications.tasks.push`, under the lock `push`, deferred by `notify` in the change's
  transaction; retries at 1, 3 and 6 minutes at priority −1, so a waiting retry holds back no new push.
- **For section 8:** a tap focuses an open window and moves it through the app's router (a message, `open-page`), so an
  unsaved roster still asks; with none open it opens one. Still no `fetch` listener.
- **A failure count** goes up once a push that did not get there (a refusal at once, an unreachable service after its last
  try), so the health page's failed attempts can be up to four a push while a subscription's count moves by one.
- **Look for Chrome's own notice.** In ticket 41's drive, a hand-started Chrome with its own profile showed "This site has
  been updated in the background" beside the push in the three runs with the app not the focused tab, and a click on it opened the
  app's home. That Chrome also reported no notifications straight after showing one, so it is probably that Chrome and not
  the worker. On a real host name, in an ordinary Chrome, check that one push shows one notification.
- **Driving one:** a Playwright-launched Chrome receives no push (`--disable-background-networking`, and a permission granted
  over CDP lapses with the connection). Allow notifications in a profile of its own and start the installed Chrome with
  `open -na "Google Chrome" --args --user-data-dir=… --remote-debugging-port=…`, with no other Chrome running; a click on a
  notification reached no Chrome started by running its binary.
