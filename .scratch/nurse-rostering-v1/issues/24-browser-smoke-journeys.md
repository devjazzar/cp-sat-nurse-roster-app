# 24: Browser smoke journeys

**What to build:** The compose stack is exercised in CI the way the hospital will use it: the System Admin logs in and creates the CNO; the CNO sets up a unit and nurses; the unit manager generates and submits a roster; the Deputy CNO approves it; a nurse sees it, makes a request and proposes a swap a colleague and the manager accept; on desktop and phone sizes.

**Blocked by:** 21 Month close; 22 Operations; 23 Phones and PWA

**Status:** ready-for-agent

- [x] Playwright journeys per role against the compose stack with the real solver on a small unit
- [x] CI job builds the image, starts the stack, runs the journeys, and fails the build on any failure
- [x] Journeys run at desktop and phone sizes

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


**Implemented on 2026-11-07,** on branch `claude/ticket-24-smoke-journeys-a25eb7`, from `main` at `8226d8a`. The suites:
- backend under pytest on a throwaway PostgreSQL 18 container of my own: 2320 passed (2311, and 9 for the clock);
- frontend under Vitest: 550 passed (549, and 1 for a bug the journeys found), and `npm run build` passed;
- Playwright: 68 checks in 8 projects (ticket 23's 21 among them), passed twice in a row on the same two stacks (7.1 and 6.9 minutes);
- `e2e/ci.sh`, the CI definition's steps, run end to end here: passed, Playwright 68 of 68 and `operations.sh` to "every check passed", printing 30 `ok` lines (its 3 new clock checks among them; ticket 22 counted its checks as 31, so its lines and its count differ), in 11 minutes, with everything removed after.

`makemigrations --check` is clean. The API did not change, and `frontend/openapi.json` matches the export. The solver's suite was not run, since nothing in `solver/` changed.

**What was driven, and how.** Every check is in `e2e/` and runs in Playwright's Chromium against stacks `e2e/stack.sh` builds from the checkout, with the production compose file, the real worker at concurrency 4 and the real solver.
- **Two stacks.**
  - A **seeded** one (`stack.sh up <project>`; `e2e/seed.py`, all months solved for real in-process):
    - ticket 23's ER with its four nurses, Mona its manager, last month approved and not closed, next month approved, a request window for the month after;
    - ICU with **64** nurses, 16 of each of the sample's, with its headcounts 16 times the sample's. Omar is its manager and has a nurse profile there. Next month is approved and the month after is a draft;
    - Carla the CNO and Hala the Deputy CNO.
  - An **empty** one (`stack.sh up <project> --empty`): the System Admin with `INITIAL_ADMIN_PASSWORD` and a change due, as on a first start. Each journey empties it again first (`stack.sh reset`: `flush`, then `bootstrap`, then the clock put back).
- **The journey** (`tests/journey/journey.spec.ts`), seven steps in order, from the empty stack, run once on a 360 px phone (`journey-phone`) and once on a 1280 × 800 desktop (`journey-desktop`):
  1. The System Admin logs in with the initial password and is made to change it, then creates the CNO, the Deputy CNO and a unit manager, each with the password the dialog shows once.
  2. The CNO, at the first login and its forced change, makes the unit "Maternity" with its manager, then its four nurses.
  3. The manager sets the unit rules to the four-nurse sample's and solves next month with the real solver: a 10 s limit, through the queue. The draft is then submitted.
  4. The Deputy CNO approves it. The CNO had the same roster open, with Approve showing, and then confirms: the dialog says "This roster has been approved already by Yusuf Rahman." (**race: two approvers**).
  5. The manager opens a request window. A nurse reads the roster in force on My roster, follows the notification to My month, and makes a request, which the manager accepts; the nurse then reads "Accepted".
  6. A nurse proposes a two-cell swap that the app's own judging finds sound (`stack.sh swap`). The colleague accepts it on their Swaps, and the manager reads it checked and approves it. The roster in force is then version 2, origin Swap: the manager's version list says so, and both nurses' cells on My roster have changed.
  7. The Deputy CNO reads the versions. Version 2's reason is "Swap proposed by … approved: …, … on 1 December 2026." The default comparison of 1 against 2 shows the two cells.
  On a phone, no page the journey opens scrolls sideways.
- **After the journey** (`after-journey`, desktop, on what the desktop journey left):
  - `clock.spec`, **expiry by date**:
    - A nurse's request waits in the window. The clock moves to the day after its last day: My month says it has closed. The job then runs, and the manager is told "… has closed, and 1 request waits for your decision."
    - The manager opens next month's window from two days on, and both pages say it opens then. The clock moves to that day: My month says it is open. The job then runs, and the nurse is told "… opened requests for … until …".
    - A swap waits for its colleague. The clock moves to the day after its date: the proposer's page says Expired. The job then runs, and the colleague is told "… has expired, so it changes nothing."
  - `races.spec`:
    - **Two changes to an approved roster:** two tabs of the manager's are opened. The second, still showing the version before, saves after the first, and is the next version: "2 changes saved as version N+1", both in the list (the server's rule, "the second waits and is the next version").
    - **A swap approved while a re-plan waits**, and **leave recorded while a re-plan waits:** the worker is stopped, so the re-plan stays queued; the other change is made; the worker is started. The re-plan's page then says "The roster in force or the month changed while the re-plan ran, so its roster was not put in force …".
    - **A manager deactivated during an edit:** with two cells changed and unsaved, the System Admin deactivates them; Save then raises the page's "Leave without saving your changes?" and goes to the login page. The System Admin reactivates them and the CNO gives the unit back.
  - `replan.spec`: leave recorded late on a day someone works, then a real re-plan that covers it and is put in force as a new version, origin Re-planned. The Deputy CNO reads it with its reason ("Re-planned from 1 …") and its comparison with the version before (**the Deputy CNO reading a re-plan**).
  - `solver.spec`: with `solver` stopped, the manager's solve fails ("The solve failed, … It says: …"), and the System Admin's solve history reads "The solver could not be reached." `solver` is started again in a `finally`.
- **On the seeded stack, at 1280 px** (`desktop`):
  - `roles.spec`: every page in each role's header opens, with no "could not be read": System Admin, CNO, Deputy CNO, manager, manager with a nurse profile, staff nurse. The CNO and the Deputy CNO each open ER's and ICU's approved rosters from Rosters, all 4 and all 64 nurses counted by `aria-rowcount`. Omar reads his own row on My roster, and his hours on My month with no requests card.
  - `close.spec` (ticket 21):
    - The hourly catch-up is run in the worker, and Mona is told ER's last month closed. Its card says closed with version 1 in force.
    - She records late leave, and the card says the facts changed. "Close … again" closes it again "by Mona Ali".
    - Removing the leave and closing once more puts it back.
    - A nurse reads My month of the closed month: "The month has closed: these are what really happened, with your leave."
  - `operations.spec` (ticket 22):
    - The health page's cards. The Backups card's first row has a time, a size and a Download, and the file comes down whole, named `nurse-roster-…Z.dump`.
    - The CNO, a manager and a nurse are each refused the file and `/api/ops/health` (403), and sent home from `/health`.
  - `large.spec`:
    - ICU's 64-nurse draft is windowed: fewer than 64 row headers are in the page.
    - The keyboard moves focus: ArrowRight, then ArrowDown to row 2, then PageDown to the last nurse's row, which was not in the page and is now in view, then End. Enter opens the cell's menu, a pin is one change unsaved, and Discard puts it back.
    - A real re-plan of the 64-nurse month, and its result's "Against the roster in force" with "Each rule, before and after".
    - A swap there is proposed and checked on the spot, read by the manager as breaking no hard rule, then withdrawn.
- **Narrow:**
  - `narrow.spec`, at 360 and 320 px: every page in the CNO's and the Deputy CNO's menus; a unit's roster from Rosters; the pages only a link reaches (a solve's result, the roster's and My roster's print pages, the nurse import). None scrolls sideways.
  - `phone-375`, at 375 px:
    - the manager's Requests page;
    - the manager's Swaps page, with a swap of its own proposed, read before and after, then withdrawn;
    - a real re-plan of ICU and its result's tables.
    None scrolls sideways.
- **Ticket 23's checks** run as before at 360 and 320 px, and `deploy` runs last.
- **No fixed sleep, no fake timers, no wait that proves something did not happen.**
  - Each step waits for what must appear.
  - A solve's or a re-plan's wait is raised to 90–120 s, and an action fails in its own words after 10 s (`actionTimeout`).
  - `stack.sh fire` waits on the queue's own rows: for no run of the job to be waiting or under way, then for ours to succeed, at most two minutes each.
  - Every check on the seeded stack puts back what it changed (requests and swaps withdrawn, leave removed, the month closed again) or leaves only what any run may leave: a re-plan's version, a withdrawn swap, a closed month.

**How long it takes.**
- Seeding: about 2 minutes, most of it the two 64-nurse solves.
- An empty stack: about 20 s once the image is built.
- All 68 checks: about 7 minutes on one pair of stacks (6.7 to 7.1 in four runs), on a Mac with Docker Desktop at 4 CPUs and 3.8 GB.
- `e2e/ci.sh` end to end, with the image build, both stacks, Playwright, `operations.sh` and the removal: 668 s, about 11 minutes. In it: 2 min 10 s for the image (cached) and the seed, 20 s for the empty stack, 6.7 min for Playwright, 1.6 min for `operations.sh`.

**What was found, and fixed.** Only what the ticket allowed: small, clearly a bug, with a test.
- **In a long roster grid, the keyboard lost focus** (`components/roster-grid.tsx`). The grid is windowed above 60 rows. PageDown, End, or an arrow past the rows drawn moved the active cell and scrolled to it, but the cell was not drawn yet when focus was given. Focus fell to the page's body, and the next key did nothing. Now the move waits for the cell to be drawn. Found by `large.spec`. A Vitest test in `app.test.tsx` gives jsdom a scroller and a scroll, and fails without the fix.
  - **A second cause, found when six `npm test` runs shared a machine** (reported by the session that verifies the branch; the test failed 6 of 6 there and passed alone). The virtualizer's scroll can render the grid once more inside the key's handler, before the new active cell is set. On that render the old cell is still drawn, so the move was spent focusing it, and the cell moved to never got focus.
  - Now the move remembers the cell it is for, and only that cell, once drawn, takes the focus.
  - The test waits for each focus rather than reading it once. It passed 12 of 12 in two rounds of six parallel `npm test` runs, and fails without the fix. `large.spec` passed again in Chromium on a fresh seeded stack.
- **Ticket 23's check counted the health page's own read** (`pwa.spec`). The System Admin's home is the Health page, which reads `/api/ops/health` itself, sometimes after the watch began, so "exactly two" failed now and then. It is now "at least our two". The proof that nothing came from a cache, "not from the disk cache", is unchanged.

**Findings for you, not fixed (beyond "small and clearly a bug"):**
- **A manager with a nurse profile has no link to My roster or My month.** Both pages are theirs (`onlyFor(staff_nurse, unit_manager)`), but the manager's header and Home name neither. The check opens them by their address.
- **A session that ends under an edit says nothing of why.** When a deactivated manager saves, the app goes to the login page. The page's guard asks first, "Leave without saving your changes? Your changes to the draft are not saved yet …": it says "the draft" on an approved roster, and never that the session ended. The login page says nothing either.

**What was NOT checked:**
- **CI on a CI service.** There is no remote, so `.github/workflows/browser-checks.yml` has never run on GitHub. Its one step that `e2e/ci.sh` does not take, `npx playwright install-deps chromium` (the system libraries on Ubuntu), has no macOS counterpart and was not run. Node 26 on `actions/setup-node@v4` and the runner's Compose version were not checked either.
- **Dark mode:** it cannot be switched to yet (the app is light only; `index.html` says `color-scheme: light`), so there is nothing to drive. Left for whenever it can be chosen.
- **A solver stopped during a solve.** It is stopped before the solve starts, which gives the same failure kind (unreachable, tried twice) without depending on when the stop lands.
- **"Leave or an edit while a re-plan ends"** is driven as leave and a swap while a re-plan waits on the queue, not while it runs: the same check at its end, forced in order rather than raced. An edit while one waits was not driven separately.
- **ICU's re-plan changes no cell** on a month the solver had just made (the `change` weight holds it), so its result reads "It changed no cell". A re-plan that changes cells is driven on the journey's unit, where late leave forces it.
- **The clock moves only the server's date.** The browser's own `new Date()`, which `nurses.tsx` (the start date's default) and `holidays.tsx` (this year) read, is not moved. Neither is in a check that moves the clock: a swap's dates and a window's state come from the server.
- **Timing a 64-nurse solve, draft read and re-plan on the real server:** ticket 22's install checklist's, not here.
- **Firefox, Safari, a real phone, a screen reader;** landscape; offline.
- **The month close at its own hour.** The catch-up job was run at once in the worker, not waited for at minute 30.

**Decisions taken here:**
- **Worth your review: the checks' clock.**
  - It moves the hospital's *date* by whole days, not the time. `nurses.membership.today`, which every page and job reads for the date, adds the number of days in the file `settings.E2E_CLOCK_FILE` names, read afresh at each call.
  - Timestamps stay real, so sessions, the queue's heartbeats and the health page are not disturbed.
  - The setting comes only from the environment variable `E2E_CLOCK_FILE`, which only `e2e/compose.e2e.yaml` passes, on a volume mounted in `web` (writable by root only) and the worker (read-only). `stack.sh clock` writes it with `docker compose exec -u root`.
  - **It cannot be switched on in an installation:** `deploy/compose.yaml` lists every service's variables explicitly and names this one for none, so no `.env` can reach it.
  - **It cannot be reached through Caddy:** it has no URL at all, so there is nothing for Caddy to pass. A request through Caddy could only show a 404 that proves nothing.
  - The tests that hold this:
    - `test_clock.py` (9): off by default, from the environment only, a file ignored while off, read afresh, bad content refused;
    - `operations.sh`, which now checks on its production-composed stack that `compose.yaml` gives no service `E2E_CLOCK_FILE`, and that `web`'s and the worker's setting is off and their date the real one.
- **Worth your review: the hourly jobs are run at once in the stack's own worker** (`stack.sh fire`, the queue's own `defer`), not waited for until their minute. So "firing in the real worker" is the real job in the real worker, at a moment the check chooses.
- **Worth your review: two stacks, an empty one reset before each journey.** The journey needs the System Admin's first login, which only an empty database has. `reset` is `flush` plus `bootstrap` on the running stack, much quicker than a new stack. It refuses a seeded stack.
- **Worth your review: `journey-desktop` depends on `journey-phone`, and `after-journey` on `journey-desktop`.** The two journeys share one stack, so they must not interleave. A failure on the phone therefore skips the desktop journey and everything after it.
- **Worth your review: ICU has 64 nurses, not 60,** because the grid is windowed only above 60 rows.
- **Worth your review: CI is GitHub Actions** (`.github/workflows/browser-checks.yml`, as section 10 planned), on every push and pull request.
  - Its one real step is `e2e/ci.sh`, so a checkout runs exactly what CI runs: the checks' `npm ci` and typecheck, the image and the seeded stack, an empty stack on the same layers, every Playwright project, `operations.sh` on its own stack, everything removed.
  - It fails if any of them fails, and Playwright's traces are uploaded when it does.
  - The backend's, the solver's and the frontend's suites are not in it: the ticket asked for the journeys and `operations.sh`, and section 10 now says so.
- **Worth your review: a race's loser is forced, not raced.** The loser's page is loaded first and the winner acts and is awaited, or the worker is stopped so a re-plan waits. Then the loser acts. It is the same order the server's tests force on real connections.
- **Worth your review: the two findings above are left for you,** not fixed: a manager's links to their own pages, and what an ended session says.
- **The journeys make their own secrets:**
  - the System Admin's first password from `INITIAL_ADMIN_PASSWORD` in the stack's own env file;
  - the others from the dialog that shows a created user's password once;
  - each person's chosen password at random, kept in `e2e/.stack/<project>.journey.json` (gitignored, 0600).
- **`stack.sh swap`** (`e2e/sound_swap.py`, which the seed's own sound-swap search became) finds a swap the app's judging finds sound, on the roster as it stands, from a date. Checks whose units a re-plan or a journey changed ask for one at their own time.
- **Helpers in `support.ts` changed for ticket 23's checks too:**
  - `signIn` clears the browser's cookies first, so one page can sign in as someone else;
  - `go` waits for the link's address and for the new page's heading in place of the old one, since the router changes the address before it draws the page;
  - `toMonth` does the same for a month's links.
  Ticket 23's checks pass with them.

`README.md`'s testing section (the two stacks, `ci.sh`) and `docs/ARCHITECTURE.md` section 10 (the clock, CI as it is, `.github/` in the layout) moved. The glossary did not: no new domain term. The journey's unit is called "Maternity", since the glossary says to avoid "ward".

**Review.** The `code-review` skill's two axes against `8226d8a`.
- **Spec found, fixed:**
  - the dark-mode statement (above);
  - "leave … while a re-plan ends" (a check added);
  - a 375 px check that relied on swaps another check left (it now makes its own);
  - an assertion that every region was in view, which proved nothing (removed);
  - an either-way branch on the row count (now `aria-rowcount` exactly);
  - a loose backup file name (now exact);
  - a duplicated line.
- **Spec found, kept and said above:** the solver stopped before the solve; the clock's Caddy proof being structural; the two findings left for you; the desktop smoke walk being a smoke walk.
- **Standards found, fixed:**
  - a check expecting version 1 of a roster that a re-plan may have moved on;
  - the swap form copied in five checks (now `proposeSwap`);
  - the hard-coded shift names (now read from the menu);
  - a timeout written out twice;
  - "Ward" against the glossary.
- **Standards left as judgement calls:** `on` and `as` as short names in the journey's files; the `Proxy` that says which variable to set when a stack is not named; `anotherPhone` kept as ticket 23's name.
- **Found by the second twice-in-a-row run, fixed:** `go` returned while the old page still showed, so a month link could be clicked on it. That is the `go` and `toMonth` change above.

**The CI criterion is left unticked:** the job is written and its steps (`e2e/ci.sh`) pass here, but it has never run as a CI job, for want of a remote.

**Things later tickets should know:**
- **The dev stack needs no rebuild:**
  - nothing changed in `deploy/compose.yaml`, `compose.dev.yaml`, the `Caddyfile` or the `Dockerfile`;
  - the backend change is `config/settings.py` and `nurses/membership.py`, which runserver reloads;
  - `roster-grid.tsx` is Vite's;
  - no new dependency anywhere.
  - `deploy/tests/operations.sh` gained a check, and `.github/workflows/` and `e2e/ci.sh` are new.
- **To run it all:** `e2e/ci.sh`, or the README's lines for two stacks of your own.

**Reviewed by the user (2026-11-07):** all points marked **Worth your review** are kept as built: the checks' clock (whole days, test stacks only, structural Caddy proof); hourly jobs fired at once in the real worker; two stacks with the empty one reset before each journey; the desktop journey depending on the phone one; ICU at 64 nurses; CI as GitHub Actions running `e2e/ci.sh`; races ordered, not raced; the `support.ts` helper changes. The two findings (a manager-nurse's links to My roster and My month; what an ended session says during an edit) go to the user's grilling before any ticket is written.

**CI criterion ticked (2026-11-08):** the repository is on GitHub (`MoustafaJazzar/cp-sat-nurse-roster-app`, private) and `browser-checks.yml` ran there: the first run failed its deploy check, because `up -d --wait web` recreated the container on the runner and the edited page was gone; `e2e/stack.sh redeploy` now restarts `web` and waits for its health check instead. The second run passed, 68 of 68 and every operations check, in 15 minutes (run 42420312238).
