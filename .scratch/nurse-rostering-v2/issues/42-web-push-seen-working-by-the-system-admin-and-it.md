# 42: The System Admin and the hospital's IT see pushes working

**What to build:** The System Admin's health page says how many pushes were sent and how many failed in the last 24 hours and, in fixed words, why the last one failed (unreachable, refused, gone), and the metrics endpoint carries the same two numbers for the hospital's monitoring. Attempts older than seven days are removed by the daily retention. The install guide names the push services' hosts the server must let the worker reach, and says that a hospital that blocks them loses pushes and nothing else. The architecture says pushes are in, who sends them and through which network, what a device opts into and what housekeeping removes.

Spec: `.scratch/nurse-rostering-v2/specs/web-push-for-deadlines.md`.

**Blocked by:** 41 A push reaches the device and a tap opens the page

**Status:** ready-for-agent

- [x] The health answer and page gain a push block: sent and failed in the last 24 hours (attempts, never jobs), and the last failure's reason as `unreachable`, `refused`, `gone` or none; the OpenAPI document and the client regenerated
- [x] `/metrics` gains the two counts as gauges worked out at scrape, as its others are
- [x] The daily retention removes attempts older than seven days, under a lock of its own name like the others; the health page's counts are unaffected
- [x] `deploy/INSTALL.md`: a section on pushes naming `*.push.apple.com`, `fcm.googleapis.com`, `*.push.services.mozilla.com` and `*.notify.windows.com` over HTTPS from the worker; what a blocked firewall loses; the health line as the check; an item on the install checklist
- [x] `docs/ARCHITECTURE.md`: sections 1 and 12 no longer list push as out of scope or to revisit; section 2's table gives the worker `egress`; section 7 adds the push job and the attempts' retention; section 8 says what is pushed, how a device opts in, what Log out and deactivation do and what the health page shows; section 9's housekeeping lists attempts after seven days
- [x] `deploy/tests/operations.sh`: the worker is on a network that is not internal and `web`, the database and the solver are on none; the health answer carries the push block; `prepare` logged the key pair
- [x] Tests at the agreed seams: the backend suite (the health block's counts and last reason from scripted attempts, the two metrics, the retention's what goes and what stays); the operations check above

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

**Implemented on 2026-11-10,** on branch `claude/ticket-42-push-seen-working-9ef756`, draft pull request
Nurse-Fold/cp-sat-nurse-roster-app#31, from `main` at `1e2667e`, with `origin/main` (`5e0b884`, your review of ticket 41)
brought in by a fast-forward before the first commit. The commits:
- `68c807a`: the push block on the health answer and page, the two gauges, the retention, their tests and the regenerated
  client;
- `7fde425`: the install guide, the architecture, the test that holds the guide's hosts to the code's, and `operations.sh`;
- `b02e4ad`: "Gone" shown as ordinary on the health page;
- `2096af0`: the review's points;
- then this comment;
- then `origin/main` at `c27ef45` (ticket 43, compare two results) merged in, with no conflict. Both tickets changed
  `frontend/openapi.json`, the client and `docs/ARCHITECTURE.md`; after the merge the export and the regenerated client
  match what is committed and the typecheck is clean. On the merge, `f0133bb`, the suites ran again locally under the
  lock: the backend 3065 passed, `makemigrations --check` clean, the frontend 762 passed and built.
- **GitHub:** both workflows ran green on `ab5005f`, the last head before the merge. On `f0133bb` neither ran a job, on
  the pull request or when I dispatched both by hand: GitHub's own note on each job says the account's payments failed or
  its spending limit is reached. So the browser checks, `operations.sh` on GitHub and the six parallel frontend runs have
  not run on the merge.

The suites ran locally, one at a time under the heavy-run lock, the backend on a throwaway PostgreSQL 18 container of my own:
- the backend, on `b02e4ad`: 3031 passed. After `2096af0`, the files it touched again (the health, metrics, retention and
  install-guide tests and the try-again tests): 64 passed;
- the frontend, on `b02e4ad`: one `npm test` run, 748 passed, and `npm run build` succeeded; after `2096af0`, the health
  page's tests (11) and the typecheck again;
- `deploy/tests/operations.sh`, twice (below): every check passed, on `b02e4ad` and again on `2096af0`;
- `makemigrations --check`: "No changes detected" (no model changed);
- `frontend/openapi.json` and the client regenerated from the export.

**What the dev stack needs:** a **rebuild** (`docker compose up -d --build`), for the backend's and the page's code only.
- No new dependency, no migration, and no change to `deploy/compose.yaml`, the `Dockerfile` or the solver.
- The worker gains one daily job, `notifications.tasks.remove_old_push_attempts`.

**What was built, criterion by criterion.**
- **The push block:** `GET /api/ops/health` (the System Admin's; the public `/api/health` is untouched) gains
  `push: {sent, failed, last_failure}`. `ops.status.push_state` counts `PushAttempt` rows of the last 24 hours: `sent`, and
  everything else as failed. `last_failure` is the outcome of the latest of those failed rows, `unreachable`, `refused` or
  `gone`, an enum in the OpenAPI document, or null. Nothing else is in it: an attempt holds no user and no device.
- **The page:** a "Pushes" card beside Storage: "Sent, last 24 hours", "Failed, last 24 hours", "Last failure" (None, or the
  word as a badge), one sentence under it saying what that word means and what to do, and a line saying that every send and
  every try again counts, and that a failed push stays on the bell.
- **`/metrics`:** `nurse_roster_push_attempts{result="sent"}` and `{result="failed"}`, gauges worked out at scrape from
  the same function as the health answer, so the two cannot differ.
- **The retention:** `notifications.tasks.remove_old_push_attempts`, daily at 22:30 UTC, its lock and queueing lock under
  its own name, removes attempts older than seven days whatever came of them. The health block reads 24 hours, so it reads
  the same before and after.
- **`deploy/INSTALL.md`:** a section "Pushes": who sends and through which network, the names to allow over HTTPS, what a
  blocked firewall loses, the health card as the check with what each word means, a one-line way to try the way out from
  the worker, and the key pair with `rotate_push_keys`. Also a line in "Install", an item on the checklist (which carries
  ticket 41's ask about Chrome's own notice), the gauges under "Metrics" and the attempts under "What the queue keeps".
- **The hosts, kept in step:** the guide names five: `fcm.googleapis.com`, `push.services.mozilla.com`,
  `*.push.services.mozilla.com`, `*.push.apple.com` and `*.notify.windows.com`. That is the criterion's four and the bare
  Mozilla host ticket 41 settled. `notifications/tests/test_install_guide.py` reads the section's list and fails unless
  it equals `PUSH_SERVICE_HOSTS` and `*.` before each of `PUSH_SERVICE_DOMAINS`, in both directions. So a host added to
  either alone fails the backend suite.
- **`docs/ARCHITECTURE.md`:**
  - section 1 and 12: push is no longer out of scope or to revisit;
  - section 2: the worker's `egress` in the table and a paragraph on it, the key pair at first start, `rotate_push_keys`;
  - section 7: the `push` job and `remove_old_push_attempts`;
  - section 8: the service worker's three push listeners (still no `fetch`), what is pushed, how a device opts in, what
    Log out, an expired session and a deactivation do, the host check; the three audit actions under Security; the push
    block under Observability;
  - section 9: a push attempt after seven days.
- **`deploy/tests/operations.sh`** now also checks, on its own stack:
  - `web` logged "Made the installation's push key pair." once, from logger `ops.prepare`, and the database holds one pair;
  - the worker's container is on exactly one network Docker calls not internal, `<project>_egress`, and `web`, `db` and
    the solver are on none (read from the running containers, not from the file);
  - `remove_old_push_attempts` succeeds, and an attempt eight days old goes while one six days old stays;
  - the health answer carries the push block: empty at first, then `{"sent": 1, "failed": 2, "last_failure":
    "unreachable"}` after three rows in the day and one 25 hours old, with `/metrics` saying the same. The System Admin's
    answer is closed during a forced password change, so the script changes the reset's password through the API first.
- **Tests at the agreed seams:**
  - `ops/tests/test_installation.py`: the block empty, the counts by attempt with the 24 hours' edge on both sides, each
    of the three words, a failure over a day old no longer the last, the block's three fields and nothing else, and the
    public answer saying nothing of pushes;
  - `notifications/tests/test_pushes.py`: through the real job, one window opened with a phone that stays unreachable and
    a laptop reached reads `sent 1, failed 4, unreachable`: attempts, not the one job;
  - `ops/tests/test_metrics.py`: the two gauges with rows and with none;
  - `notifications/tests/test_retention.py`: what goes and what stays at the seven days' edge, the health block the same
    before and after, the job's two locks;
  - `notifications/tests/test_install_guide.py`: the hosts;
  - `src/app.test.tsx`: the card with nothing sent, and with counts and each of the three words and its sentence.

**What was driven, and how.** On 10 November 2026, under the lock.
- **`operations.sh`, the way it is meant to be run:** `TEST_HTTPS_PORT=18442 deploy/tests/operations.sh t42ops`, from the
  checkout. It builds the image, starts `deploy/compose.yaml` with `deploy/tests/compose.test.yaml` as project `t42ops`,
  runs every check and removes the project, its volumes and its image. All passed, twice.
- **My scratch stack:** `E2E_PORT=18482 E2E_HTTPS_PORT=18942 e2e/stack.sh up t42`.
  - **Real sends, no browser.** In the stack's worker I gave Amal two subscriptions with keys of their own: a made-up
    address on `fcm.googleapis.com`, and one on a host under `notify.windows.com` that does not exist. Emad then proposed
    the stack's sound swap to her through the API, and the stack's own worker ran the job at 04:53:33.
    - Google answered that the made-up address is gone: one `gone` attempt, and the subscription was ended at once.
    - The other host could not be found: `unreachable` at 04:53:33, then again at 04:54:33, 04:57:36 and 05:03:42
      (1, 3 and 6 minutes on), four attempts, after which the subscription's failures in a row read 1.
  - **The health page,** as the System Admin in the desktop app's browser pane on `http://localhost:18482`: the Pushes
    card read 0 sent, 2 failed, "Unreachable" with its sentence, then 1 and 3 after I added a `sent` row, and the answer
    read `{"sent": 1, "failed": 5, "last_failure": "unreachable"}` after the last try. At 375 px the card kept within the
    width and the page did not scroll sideways.
  - **`/metrics`,** from Caddy's container: the two gauges with the same numbers as the page (under the label `outcome`,
    which the review then renamed `result`; that name was seen in the second `operations.sh` run).
  - **The retention.** I added rows 8 days, 7 days and an hour, 6 days and 2 hours old, then
    `e2e/stack.sh fire t42 notifications.tasks.remove_old_push_attempts`: the first two went, the others and the day's
    attempts stayed, and the health block read the same.

The stack is down and its volumes gone; the PostgreSQL container is stopped; the lock is released.

**The health page held against the three skills, by hand,** after loading each: nothing to change.
- `better-writing`: the labels follow the Queue card's ("Sent, last 24 hours" beside "Jobs failed, last 30 days"), in
  sentence case; each reason's sentence says what happened and what to do, or that nothing needs doing; the words are the
  Notifications page's (push, device, the bell). "The install guide" is not a link, since the guide is a file with the
  installation and not a page of the app.
- `better-accessibility`: no new control. A heading, a description list whose three terms name their values, and two
  paragraphs; the reason is a word, never colour alone (1.4.1); Refresh already announces "Checked.". The badge and the
  muted paragraph are the components and colours the cards beside it use; I measured no contrast.
- `better-interface`: the card fills the empty place beside Storage in the two-column grid, so nothing moved; red is
  kept for the two reasons that may need someone, grey for "Gone", as the Services card does for Unreachable.

**What was found, and fixed.** Nothing in code that was there before.

**Findings for you, not fixed.**
- **`ops/tests/test_logs.py::test_gunicorn_logs_its_own_lines_and_each_request_as_json` failed on this machine when run
  by itself:** three times on this branch and once on a checkout of `1e2667e`, each time with two access lines where it
  expects one. It passed in the full local suite, and in GitHub's on `b02e4ad`. I did not find the cause; my guess is a first request slower
  than the test's five-second timeout, which it then repeats. Not this ticket's code.

**What was NOT checked.**
- **Chrome's own "updated in the background" notice, and an ordinary Chrome on a real host name** (ticket 41's note): not
  seen. There is no real host name here, and ticket 41's way of receiving a push needs every other Chrome closed, which
  would mean closing yours, so I started no Chrome at all. It is now an item on the install checklist.
- **A push received by any browser.** The sends above reached Google's service and a name that does not resolve; no
  device showed anything. A `sent` row from a real delivery is ticket 41's drive, not repeated here; the `sent` counts I
  saw came from the scripted tests and from rows I added.
- **Playwright and pushes** (ticket 41's caveat): no Playwright check was added or run, as the spec says. Nothing here
  needed a browser to receive a push.
- **A firewall that really blocks the hosts.** "Unreachable" was seen from a name that does not resolve, not from a
  blocked port, where each try takes the sender's ten-second timeout.
- **A real 429 or 5xx, a real refusal,** and Apple's, Mozilla's and Microsoft's services: the scripted ones only.
- **A Prometheus scraping the gauges;** `wget` from Caddy's container only.
- **The one-line check in the install guide** from a stack's worker. I ran the same line in the image's base,
  `python:3.14-slim-trixie`, by itself: it ended in "HTTP Error 404: Not Found", the answer the guide calls fine, with no
  certificate error.
- **Which browser uses which push service,** the note beside each host in the guide: from what I know, not looked up
  again. The hosts themselves are ticket 41's, with its sources.
- **The card at 320 px.** Seen at 375 px and at the desktop width; GitHub's layout check opens the health page at its own
  widths.
- **A screen reader** on the card, beyond its markup: a heading, a description list and two paragraphs, as the cards
  beside it.
- **The six parallel frontend runs and the browser checks, locally:** GitHub runs them on the pull request.

**Decisions taken here.**
- **The block is on the System Admin's health answer alone.** The public `/api/health` says what it said; a test holds
  it to its three fields. Putting counts there would widen who sees them.
- **Everything not `sent` is failed,** `gone` included, as the spec lists it among the reasons. The page shows "Gone"
  as a grey badge and says nothing needs doing; the other two are red.
- **One reader for the page and the gauges** (`ops.status.push_state`), as two aggregate queries.
- **The gauge is one name with a label,** `nurse_roster_push_attempts{result=…}`, as `queue_jobs{status=…}` is. The label
  is `result`, since "failed" is not one of the four outcomes.
- **No column and no migration.** `PushAttempt` keeps a time and an outcome; nothing per push service was added.
- **The retention sits in `notifications/tasks.py`** beside the notifications' own, at 22:30 UTC, the free slot among
  22:10, 22:20 and 22:40.
- **`operations.sh` reads the networks from the running containers** and asks Docker whether each is internal, so it
  proves what the stack has, not what the file says. It makes no claim about Caddy.
- **`operations.sh` scripts its attempts as rows,** since its stack must reach no push service to pass.
- **The install guide also says how to replace the key pair,** since the hospital's IT is who would (user story 34).

**Worth your review.**
- **The last failure is the last of the 24 hours, not the last ever kept.** Ticket 41's note says "the latest row that
  is not `sent`", with no window; the ticket's own sentence reads "how many failed in the last 24 hours and why the last
  one failed". I took the second: with no window, a failure six days old would show beside "Failed: 0", and the answer
  would change when the retention ran. The cost: nothing reads days 2 to 7 of the attempts kept. Recommendation: keep;
  the other reading is a one-line change and one test.
- **The page says more than a word.** Each reason has one sentence under it (for `unreachable`: look at the firewall,
  the install guide names the hosts). The spec asked for "fixed words"; the sentences are fixed too, and are what makes
  user story 35's "the health page says what is lost" true. Recommendation: keep.
- **"Unreachable" is also a 429 or a 5xx** (ticket 41's mapping), so it does not always mean the firewall. The page says
  "could not be reached, or answered that it was overloaded", and both it and the guide point at the firewall only when
  failures keep coming with nothing sent. Splitting the word in two would be a change to ticket 41's outcomes.
- **"Device" on the health page and in the guide** ("every send to one device is counted"), where the glossary prefers
  push subscription. You kept "device" on the Notifications page and in the API at ticket 40's review, and a System Admin
  reads it more easily; the API's field descriptions say push subscription. Recommendation: keep.
- **A rotation can turn a device off.** While checking the documents the review found that a device not opened before
  ten pushes to it were refused after `rotate_push_keys` is ended like any other, and must be turned on again by hand,
  since the app's silent replacement needs the server to still hold it. The spec says so in pieces ("count toward the
  ten"), and the guide and the architecture now say it plainly. Changing it (not counting refusals after a rotation,
  say) would be a new decision; I changed no behaviour.
- **`operations.sh` changes the System Admin's password through the API** to read the health answer, on its own stack
  only. It is the only way to that answer short of reading the database.

**Review.** `code-review` against `1e2667e` ran its two axes in parallel. No `/codex:adversarial-review`, as you asked.
- **Spec.** Nothing asked for is missing. Fixed in `2096af0`:
  - the guide and the architecture said a rotation turns nobody off (above);
  - the architecture said `egress` reaches the push services "and nowhere else": the network is open, and the host list
    and the firewall are what limit it;
  - "unreachable" explained as the firewall alone;
  - the service worker's "third listener" (it has five) and "always tagged" (an unknown kind has no tag);
  - a missing gauge ended `operations.sh` without its own message.

  Kept: the 24 hours on the last failure, and the page's sentences (both above); `operations.sh` checking the retention,
  the key pair's row and exact counts beyond the criterion's three lines, since each is one line and proves something
  the criterion's words imply; the second host test with its five literal names, which is the independent list.
- **Standards.** No hard breach. Fixed:
  - the block's query loaded every row of the day and is now two aggregates;
  - the badge's colour moved into the map with the words;
  - the gauge's label renamed `result`;
  - the second read of the block in `operations.sh` says why it failed;
  - ADR 0012 was cited for "attempts, never jobs", which it does not say; the citation now names this ticket.

  Kept:
  - "device" (above);
  - the three outcome words written in the API's `Literal`, the page's map and the guide: the API's enum is what the
    client is generated from, and a new outcome should be a decision in each place;
  - the small `attempted` helpers in three test files, each with its own file's shape of time;
  - the health answer asserted from `test_retention.py` and `test_pushes.py` too: "the counts are unaffected" and
    "attempts, never jobs" are criteria, and each is shown where its cause is made.

**Things later tickets should know.**
- **Whoever sees pushes on a real host name first:** the install checklist's push item is the list of what to look at,
  Chrome's own notice first.
- **A new push outcome** needs a word in `ops/api.py`'s `Literal`, the page's `LAST_FAILURE` map and the guide's list of
  words; `push_state` counts anything not `sent` as failed without a change.
- **A new push service's host** goes in `notifications.subscriptions` and in the guide's list together, or
  `test_install_guide.py` fails.
- **`operations.sh` now ends signed in as the System Admin with a password only it knows;** a check added after it can
  read any System Admin page's data with `curl -b "$jar"`.
