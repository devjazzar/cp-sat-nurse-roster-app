# 24: Browser smoke journeys

**What to build:** The compose stack is exercised in CI the way the hospital will use it: the System Admin logs in and creates the CNO; the CNO sets up a unit and nurses; the unit manager generates and submits a roster; the Deputy CNO approves it; a nurse sees it, makes a request and proposes a swap a colleague and the manager accept; on desktop and phone sizes.

**Blocked by:** 21 Month close; 22 Operations; 23 Phones and PWA

**Status:** ready-for-agent

- [ ] Playwright journeys per role against the compose stack with the real solver on a small unit
- [ ] CI job builds the image, starts the stack, runs the journeys, and fails the build on any failure
- [ ] Journeys run at desktop and phone sizes

## Comments

**From ticket 20 (2026-11-06).** A swap journey: a staff nurse proposes on Swaps (`/swaps`) on an approved month, each colleague in it accepts on their own Swaps page, the unit's manager approves on Swaps (`/unit-swaps`), and the roster in force shows the new version. A refusal about a colleague reads only "This swap cannot work for … on …"; a journey can assert that it says nothing more.


**Decided by the user (2026-11-06): what tickets 01–20 never drove in a browser goes here.** Their "What was NOT checked" lists name these; the API and Vitest suites hold the logic, so a journey only has to show each works in a real browser on the compose stack.

- **Races:** two approvers at once, leave or an edit while a re-plan ends, two changes to an approved roster, a swap approved while a re-plan runs, a manager deactivated during an edit. The server tests force the order on real connections; a journey shows the loser's page says what happened.
- **Expiry by date:** a swap whose date passes and a request window opening and closing by its dates, with the hourly jobs firing in the real worker. Needs a clock the stack can move (the API tests patch `membership.today`).
- **The other roles in the browser:** the Deputy CNO approving and reading versions, a request's and a swap's version reasons and a re-plan's comparison; the CNO reading every unit's rosters; the System Admin's pages after the forced first password change; a manager with a nurse profile on My roster and My month.
- **320 px** for every page, the Users page's row buttons over names included (ticket 23), and 375 px for the manager's Requests and Swaps pages and the re-plan result.
- **Dark mode**, once it can be switched to.
- **A large unit:** a roster grid long enough to be windowed, edited with the arrow keys; a 60-nurse unit's draft, re-plan comparison and swap check (timing belongs to ticket 22's install checklist).

**From ticket 21 (2026-11-06).** Month close exists. The manager's journey can end on the Roster page's "Carry-over and month close" card: a month over closes on its own (the hourly catch-up), and a late leave then "Close … again". The nurse's journey can read My month of a closed month. The real clock must be past a month's end for either: seed an approved past month, as `nr-t21`'s seed script did (ticket 21's comment).

**From ticket 22 (2026-11-06).** Operations exist.
- **The System Admin's journey** can end on the health page: the Backups card lists the backups with their sizes and times and a Download for each, and another role is refused the file (403) and sent home from `/health`. A stack's first backup comes within five minutes of the worker starting, or at once from `docker compose exec worker python manage.py backup`.
- **`deploy/tests/operations.sh <project>`** is a compose-level test already: it builds the stack under its own project, secrets, volumes, image tag and HTTPS port (`TEST_HTTPS_PORT`, default 18443), checks a backup by the job, a failed and a real restore by `deploy/restore.sh`, the reset script lifting a lock, JSON logs, `/metrics` refused through Caddy, and the retention jobs, then removes everything. CI could run it beside the journeys; it needs Docker with Compose v2.24 or later, `curl`, `openssl` and `python3`, and takes several minutes for the build.
- **Through Caddy** the certificate is self-signed without a `DOMAIN`, so Playwright needs `ignoreHTTPSErrors`. The built-in browser here refuses such a certificate, so ticket 22 drove the pages on `web` published over HTTP under `DJANGO_DEBUG`, as ticket 21 did.
- **A solve's failure kind** on the System Admin's solve history ("The solver could not be reached.", and the like) was checked in Vitest only: a journey can stop the `solver` service during a solve and read it.

**From ticket 23 (2026-11-07).** Phones and the PWA exist, with Playwright checks at phone size to build on.
- **The harness is `e2e/`** (its own `package.json`, `@playwright/test` 1.64.1; `npx playwright install chromium` once):
  - `e2e/stack.sh up <project>` builds a stack from the checkout (its own project, secrets, volumes, image tag `<project>-app:e2e`), seeds it with `e2e/seed.py`, takes a backup, and writes `e2e/.stack/<project>.json`.
  - `E2E_STACK=<project> npx playwright test` runs the checks.
  - `rebuild` takes a new image and keeps the data, `redeploy` stands in for a deploy (edits `index.html` and `sw.js` in `web`, restarts it), and `down` removes everything. It refuses `nurse-roster`.
  - CI can run the same three lines; it needs Docker with Compose v2.24 or later, `openssl`, `python3` and Node 26.
- **The origin:**
  - The checks' `baseURL` is `web` over HTTP on `localhost:$E2E_PORT`, without `DJANGO_DEBUG`. Sign-in works there (`Secure` cookies are accepted on localhost).
  - Through Caddy (`caddyURL`, `ignoreHTTPSErrors`) the pages work, but **Chromium will not register the service worker behind the self-signed certificate**, whatever `ignoreHTTPSErrors` says.
  - A journey through Caddy runs without the worker, which changes nothing, since it handles no request. Only `pwa.spec` and `deploy.spec` need the localhost origin.
- **The seed** is ticket 23's minimum: the solver's four-nurse sample as ER, next month approved by a real in-process solve, a request window open for the month after, a sound two-cell swap in `stack.swap`, `admin` signed in with the seed's password, and every user's full name in `stack.names`. **Your journeys start from an empty stack instead** (the System Admin creates the CNO and so on). Give them a seed of their own, or `up` without seeding.
- **Projects:** `phone-360` and `phone-320` (a Pixel 7's touch screen and user agent; `phone()` in `support.ts`), and `deploy` last, since it restarts `web`. Add a desktop project. The checks run one at a time, because they share a stack and change it; each puts back what it changed.
- **Already covered at both phone widths, so not to repeat:** every nurse page through the Menu, none scrolling sideways, the controls 44 px; a request made and withdrawn; a swap proposed and accepted on two phones (not approved by the manager: yours); the System Admin's and a unit manager's pages within 320 px; the Users page's buttons not over the names; the PWA's manifest, icons, worker and caches; Caddy's headers and `/metrics` 404.
- **Left for you from 23:**
  - The CNO's and the Deputy CNO's pages at 320 px.
  - The manager's Requests and Swaps pages and the re-plan result at 375 px.
  - Dark mode once it can be chosen. Today `index.html` says `color-scheme: light`; change it with the switch.
- **The header on a phone** (below 640 px) is the name, the bell and a "Menu" button. Pages are reached in the `navigation` named "Main menu", which is in the page only while open; the one-row `navigation` "Main" is hidden by CSS there.

