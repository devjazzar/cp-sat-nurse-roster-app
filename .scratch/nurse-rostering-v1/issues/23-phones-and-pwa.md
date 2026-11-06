# 23: Phones and PWA

**What to build:** A nurse opens the application on her phone: the roster grid scrolls horizontally, requests and swaps are usable with a thumb, and the app installs to the home screen as a progressive web app.

**Blocked by:** 19 Request windows and requests; 20 Swaps

**Status:** ready-for-agent

- [x] Responsive layout for every nurse screen and the login at phone width; grid scrolls horizontally with the nurse column fixed
- [x] Web app manifest and service worker for installability (no offline data, no push)
- [x] Playwright checks at phone size for the roster, a request and a swap

## Comments

**From ticket 18 (2026-11-06).** Nothing may cache a roster version's files: `GET /api/units/{id}/roster/export` (CSV or Excel, by `format`) answers `Cache-Control: no-store`, as the staff list and the nurse import do (ticket 08's comment), and a service worker must honour it. The print sheets, `GET /api/units/{id}/roster/sheet` and `GET /api/rosters/mine/sheet`, are JSON reads like any roster read: keep them out of any cache too, as they hold a unit's names. The print pages (`/roster/print`, `/my-roster/print`) are laid out for A4 landscape; on a phone the table scrolls sideways inside its own region, and printing from a phone was not checked.

**From ticket 22 (2026-11-06).** Two more things a service worker must never cache or serve from a cache: a backup (`GET /api/ops/backups/{name}`, the whole database, answered `Cache-Control: no-store` as an attachment) and the System Admin's `GET /api/ops/health`, which lists them. `/metrics` is not the SPA's at all: it answers only on the internal network, and Caddy refuses it, so keep it out of any route the worker handles. The health page's Backups table scrolls sideways inside its own region at 320 px, with the Download column at the far edge, as the other tables do.

**Implemented on 2026-11-07,** on branch `claude/ticket-23-phones-pwa-ad42fe` (`d8283e7`, `2272ceb`, `6c54696`). The backend ran under pytest on a throwaway PostgreSQL 18 container of my own (2311 passed: 2307 and 4 new). The frontend ran under Vitest (549 passed: 539, 3 for the menu, 3 for the service worker, 4 for a stale build) and `npm run build` passed. The Playwright checks passed 21 of 21, twice in a row on the same stack, against a stack built from the branch and seeded (scratch project `nr-t23`). `makemigrations --check` is clean. The API did not change, and `frontend/openapi.json` matches the export. The solver's suite was not run, since nothing in `solver/` changed.

What was built:
- **The phone header** (`routes/_signed-in.tsx`). From 640 px up it is one row, as before. Below that it is the name, the bell and a **Menu** button (`aria-expanded`, `aria-controls`). The button opens the role's pages, Change password, who is signed in and Log out, in rows 44 px tall. The menu closes when a page is chosen (the one already open too), on Escape, which puts focus back on the button, and when the path changes. Which header shows is decided by CSS alone. The menu is in the page only while open, so the links are never there twice for a screen reader or a test.
- **Thumb-sized controls.** On a touch screen (`pointer: coarse`), every `Button` size but `xs`, every `Input` and every `NativeSelect` is 44 px tall. So are the bell, a notification's link and the password page's "Back to home". A mouse keeps the compact sizes.
- **The month navigation** on a phone: the month above, Previous and Next each half the row beneath.
- **The roster grid's nurse column** is narrower below 640 px (`min-w-24`, `max-w-28`, wrapping), so about five days show beside it at 320 px. The grid already scrolled inside its own region with the column sticky; that is unchanged.
- **Tables that wrap on a phone** (`WRAP_ON_PHONE`): a nurse's requests and a swap's cells, so the outcome and "Becomes" are in view at 320 px rather than past the region's edge.
- **The Users page at 320 px:** the actions column is sticky only from 640 px up. Below that it scrolls with the row and comes last, so it no longer covers the names. The table is a named, focusable scroll region ("Users"), as the others are.
- **The PWA:**
  - `frontend/public/manifest.webmanifest`: "Nurse roster" / "Roster", `start_url` and `scope` `/`, `standalone`, white theme and background.
  - Icons 192, 512, a maskable 512 and Apple's 180, rendered by `e2e/render-icons.mjs` from `favicon.svg` (a month's grid on the app's near-black).
  - `index.html` links them and the manifest, with `theme-color`, `color-scheme: light` and `apple-mobile-web-app-title`.
- **The service worker** (`frontend/public/sw.js`) has **no `fetch` listener**. Every request reaches the network as it would without one, under the server's own `Cache-Control`: the page, the API, a roster's files and print sheets, backups, `/api/ops/health`, `/metrics`.
  - It takes over at once (`skipWaiting`, `clients.claim`) and on activating deletes any cache an earlier worker left.
  - It is registered at load with scope `/` and `updateViaCache: "none"` (`lib/service-worker.ts`). A browser that refuses it (see below) works as before, only not installable.
- **Headers** (`config/settings.py`, `config/urls.py`):
  - Every file with a fixed name answers `Cache-Control: no-cache`: the page and every client-side route, `index.html`, `sw.js`, the manifest and the icons. A browser asks again each time (a 304 when nothing changed).
  - The manifest is `application/manifest+json`.
  - **Found by the test: the build's hashed assets were never cached for good.** `WHITENOISE_IMMUTABLE_FILE_TEST = r"^assets/"` never matched, because WhiteNoise tests the URL with its leading `/`, so they went out at one hour. Now `^/assets/` (`SPA_ASSETS`), `immutable`.
- **A tab opened before a deploy** (`lib/stale-build.ts`). The tab asks for a page's code by its old hashed name, which the new image no longer has, and Vite raises `vite:preloadError`. The tab then loads once more and runs the new build. If that fails the same way within 10 s, the deploy itself is broken, and the error is left to show rather than reloading for ever.
- **How it is served:**
  - **Through Caddy:** `reverse_proxy web:8000` passes WhiteNoise's headers unchanged, so the `Caddyfile` did not change. The scope is `/` because the worker sits at the root, so no `Service-Worker-Allowed` header is needed. `/metrics` stays refused (404).
  - **In development:** Vite serves `frontend/public` at the root with the same headers. It already sends `no-cache` and the same media types (checked with `curl` on a Vite of my own on another port), so `compose.dev.yaml` did not change.
- **The browser checks, `e2e/`,** at the repo root as `docs/ARCHITECTURE.md` section 10 planned. **Playwright is a new dependency** (`@playwright/test` 1.64.1, the architecture's pin; 1.65.0 was a day old). It is in `e2e/package.json` of its own, not `frontend/`, so neither the image nor the dev stack's `npm ci` pulls it.
  - `e2e/stack.sh up|rebuild|redeploy|down <project>` builds a stack from the checkout: its own project, secrets, image tag (`<project>-app:e2e`) and volumes, `web` over HTTP on `127.0.0.1:$E2E_PORT` and Caddy on `$E2E_HTTPS_PORT`. It seeds (`e2e/seed.py`) and takes a backup, then writes `e2e/.stack/<project>.json` (gitignored) for the config. It refuses `nurse-roster`.
  - `seed.py`: the solver's four-nurse sample as ER, next month solved for real in-process and approved, a request window for the month after open from today, and a two-cell swap that the app's own `swaps.judging` finds sound. The bootstrap `admin` takes the seed's password with no change due.
  - Projects: `phone-360` and `phone-320` (a Pixel 7's touch screen and user agent at those widths) run everything but `deploy`, which restarts `web` and runs last.
  - Each check puts back what it changed (the request and the swap are withdrawn), and clears what a failed run left, so the suite runs again on the same stack.

Seams, test first:
- `ops/tests/test_spa.py` (4): `no-cache` on the page and routes; `no-cache` on the fixed-name files; `immutable` on hashed assets (this one found the bug); the worker's and the manifest's media types.
- `src/sw.test.ts` (3): the worker run against a stand-in scope. It listens for `install` and `activate` only, takes over at once, and removes every cache.
- `src/stale-build.test.ts` (4): reloads once, not again within seconds, again minutes on, and without a session store.
- `app.test.tsx`, "on a phone" (3): the menu opens the same pages, Change password and Log out; choosing a page closes it, the one open too; Escape closes it and returns focus. The page-already-open case was found by Playwright, not foreseen.
- `e2e/tests` (10 checks, at both widths, plus `deploy`):
  - `layout`: the login page; every nurse page through the menu, Notifications and the password page, none scrolling sideways and each control 44 px; the grid scrolling in its region with the nurse's row header at the same x after scrolling to the last day; a manager's and the System Admin's pages within the width; no Users row's buttons overlapping its name.
  - `request`: made and withdrawn on My month, its outcome wholly in view in the wrapped table.
  - `swap`: proposed on one phone, accepted on another, withdrawn, its cells' "Becomes" column wholly in view.
  - `pwa`:
    - the manifest as Chrome parsed it (`Page.getAppManifest`, no errors), each icon's real size, and the registration's scope, script and `updateViaCache`;
    - with the page controlled, every response under `/api` and `/metrics` not from the worker and not from the disk cache, with each file fetched twice: My roster's sheet, the CSV and Excel exports, the unit's sheet, `/api/ops/health` and a backup, the exports and the backup `no-store`;
    - through Caddy, the same headers and `/metrics` 404.
  - `deploy`: `stack.sh redeploy` changes `index.html` and `sw.js` in `web` and restarts it. The reload shows the new marker, and a new version of the worker activates by the browser's own check on that navigation (CDP `ServiceWorker` events). Nothing asks it to update.
- No raised timeouts, no fake timers, no fixed sleeps. Playwright waits for what must appear. One read is not a wait: `request.spec` takes the count of a waiting request after the window's sentence from the same answer has rendered.

The checklist the session gave, answered one by one:
- **Every nurse screen and the login at 360 px and 320 px:**
  - **My roster, My month (requests and leave are cards on it; `/my-leave` redirects there), Swaps, Notifications and the bell, Change password, the login page, Home, and the catalogue pages a nurse reads:** yes. None scrolls sideways at either width, in Playwright and by eye.
  - **Grid sideways in its own region, nurse column fixed:** yes. After the region scrolls to the last day, the row header's x is unchanged.
  - **Thumb-usable:** 44 px on touch, asserted for the menu and its rows, the bell, the month links, the request form and Withdraw, the swap composer, Accept and Withdraw, the password form, and a notification's link.
  - **The Users page at 320 px:** fixed, and asserted (no button's box overlaps its row's name).
  - **Manager and admin pages:** a unit manager's and the System Admin's every page keep within 320 px (Playwright). The CNO's and the Deputy CNO's were not walked.
- **Installable PWA, manifest and icons, a worker for installability only:** yes, as Chromium reads them (below). There is no offline data and no push.
- **The worker caches nothing under `/api`, no export, print sheet or backup, nor `/metrics`:** yes, by having no `fetch` handler.
  - The unit test holds it to that.
  - "Not from the worker" cannot fail while there is no handler. The check that `no-store` is honoured is "not from the disk cache" on each file's second fetch.
- **A new deploy picked up:**
  - In Playwright: a changed page and a new worker after a restart.
  - By hand, a real image rebuilt under an open page, twice:
    - a plain reload showed the new header text and a new entry hash;
    - a tab still on the old build signed in, asked for the Health page's old chunk, reloaded once (`navigation: reload`) and showed the new page.
- **Served through Caddy and the dev Vite server, scope and headers:** above. Caddy is checked by Playwright's request API, Vite by `curl`.
- **Playwright:** new, where it runs and how ticket 24 reuses it: above, and in ticket 24's comment.
- **Dark mode, 200% zoom, safe-area insets:**
  - **Dark mode:** the app is light only (the `dark` variant is class-based and never set). Under a dark preference in the built-in browser the Users page (with its native select) stayed light; no other page was looked at under it. `color-scheme: light` asks the browser to keep its own controls and scrollbars light with the page; that effect was not observed separately. Switching is ticket 24's.
  - **200% zoom:** a 640 px window at 200% is a 320 CSS px viewport, which the `phone-320` project is. No separate zoom was driven.
  - **Safe-area insets:** none to handle. The viewport has no `viewport-fit=cover`, so the browser keeps the page inside the safe area. Not seen on a notched device.

**Driven in the built-in browser,** on `nr-t23` (the production compose file with `e2e/compose.e2e.yaml`; `web` on `localhost:18023` over HTTP without `DJANGO_DEBUG`, Caddy on `127.0.0.1:18423`):
- **At 320 and 360 px** (the pane's touch emulation matches `pointer: coarse`):
  - Amal's home, the menu open, My roster's grid, My month with her requests, Swaps with the composer and her withdrawn swaps, Notifications.
  - As the System Admin, after the forced change, the Users page: names in view, the buttons at the region's far edge, the page 320 px wide.
- **Signing in over plain HTTP on localhost without `DJANGO_DEBUG` works** (`Secure` cookies are accepted on localhost). Earlier tickets ran `web` under debug for the built-in browser; this stack did not need to.
- **The service worker could not be seen there.** The built-in browser refuses every registration ("An unknown error occurred when fetching the script") and never requests `/sw.js`, which `fetch` reads fine at 200 with `no-cache`. The app runs the same without it. The worker, its control of the page, its scope and the manifest as Chrome reads them were checked in Playwright's Chromium (Chrome for Testing 156).
- **A deploy picked up**, twice with a real image rebuild (above). The temporary edits (a header's and a heading's words) were put back with `git checkout` and never committed; the stack was removed afterwards.

What was NOT checked:
- **A real iPhone or Android phone, and a real home-screen install.** No install prompt was raised and no app was added to a home screen; what Chrome needs for one was checked (a manifest it parses whole, the icons, an active worker controlling the page). iOS Safari's standalone mode, status bar and Apple's icon were not seen.
- **`Page.getInstallabilityErrors`:** headless, it answered `[]` even with no manifest at all, so it proves nothing and is not used.
- **Any browser but Chromium** (Firefox, Safari), and a screen reader on a phone.
- **Offline:** the worker keeps nothing, so offline is the browser's own page. It was not looked at.
- **Landscape, a tablet, and printing from a phone.**
- **The CNO's and the Deputy CNO's pages at 320 px** (ticket 24 has every page at 320 px).
- **The manager's pages as made for a phone:** only that none breaks the width.
- **A service worker behind Caddy's self-signed certificate:** Chromium refuses to register one there whatever `ignoreHTTPSErrors` says (tried). With Let's Encrypt (`DOMAIN`) it registers as on localhost; that is part of the install checklist's "Caddy in a browser at the hospital's own address".

**Decisions taken here:**
- **Worth your review: the service worker handles no request** (no `fetch` listener), rather than a network-only handler or an offline page. "Must not cache" holds by construction and costs no request any latency. Offline, the phone shows its own offline page, not ours.
- **Worth your review: the browser checks run against `web` over HTTP on localhost,** not through Caddy. A browser lets a worker register there and refuses one behind Caddy's self-signed certificate. `web` runs without `DJANGO_DEBUG`, as in production. Caddy is checked separately for headers and `/metrics`.
- **Worth your review: below 640 px the header is a Menu button,** with the bell beside it, rather than the links wrapping onto four lines as they did.
- **Worth your review: 44 px controls on every touch screen, for every role,** by `pointer-coarse:` on the shared Button, Input and Select. A manager on a tablet gets them too; a mouse never does.
- **Worth your review: every file with a fixed name is `no-cache`,** the icons included, and the hashed assets now `immutable` (the regex fixed). A deploy is what the next load fetches; a 304 costs a round trip.
- **Worth your review: a tab from before a deploy reloads once** when a page's code is gone, and not again within 10 s.
- **Worth your review: light only for now,** said to the browser (`color-scheme: light`, white `theme-color`), until dark mode can be chosen.
- **Worth your review: no `viewport-fit=cover`,** so no safe-area handling is needed. An installed app's content stays inside the notch's safe area, on the white background.
- **Worth your review: `e2e/` at the repo root with its own `package.json`,** Playwright 1.64.1. Its seed gives the bootstrap System Admin the seed's password with no change due, on a scratch stack only. `stack.sh redeploy` stands in for a deploy by editing the built files inside `web` and restarting it, not by building a second image.
- **Worth your review: the Users page's actions are sticky only from 640 px,** and below that scroll with the row.
- **Worth your review: the icon,** a month's grid on the app's near-black with one day in the Day shift's blue, until there is a visual design.
- **Small tables wrap on a phone** (`WRAP_ON_PHONE`) rather than scroll: a nurse's requests and a swap's cells. The roster grid, the leave table and the managers' tables still scroll, as before.

`docs/ARCHITECTURE.md` section 4 (the frontend: phone-first nurse pages, the PWA, the headers, how it is served) and section 10 (`e2e/`) moved, as did `README.md` (how to run the browser checks; `e2e/` in the layout). The glossary did not move: no new domain term.

**Review.** The `code-review` skill's two axes against `49a5c1f`.
- **Spec found, fixed:**
  - The Users fix and the System Admin's pages were untested at 320 px: the seed now signs in `admin`, and Playwright walks them and asserts no overlap.
  - Request and swap ran at 360 px only: now at both widths.
  - Caddy was not exercised: headers and `/metrics` are now checked through it.
  - Backups and `/api/ops/health` were not in the cache check: now fetched twice each, from a backup `stack.sh up` takes.
  - The deploy check called `update()` itself: now it relies on the browser's own check.
  - An open tab across a deploy would fail on a page's old chunk: now it reloads once.
  - How the files are served through Caddy and Vite was not written down: now in the architecture.
- **Spec found, kept:**
  - "Not from the worker" cannot fail; said in the test's comment, with the disk-cache check carrying the proof.
  - `Page.getInstallabilityErrors` is not used (above).
  - The touch sizes and `color-scheme` beyond the nurse's pages, and the regex fix, are recorded above.
- **Standards found, fixed:**
  - "account" and "login" against the glossary in a comment and a test name.
  - Two copies of the icon's SVG, now one (`favicon.svg` is the source).
  - The wrap classes twice, now `WRAP_ON_PHONE`.
  - Log out twice, now one component.
  - `/assets/` twice, now `SPA_ASSETS`.
  - The seeded names in two places: the seed now prints them.
  - The phone device built twice.
  - The usage string three times.
  - Why each file is fetched twice, now said.
- **Standards left as judgement calls:** `pointer-coarse:h-11` spelled in each of the copied shadcn components rather than shared (ADR 0008 treats them as our code). The one-read count in `request.spec` is explained.

`better-interface` and its domain skills, held by hand on the phone pages:
- **Accessibility:**
  - The Menu button is a disclosure (`aria-expanded`, `aria-controls`). The opened list is a `nav` named "Main menu" that follows the button in reading and Tab order. Escape returns focus to the button. The active page keeps `aria-current`.
  - Targets are 44 px on touch (WCAG 2.5.5's enhanced size).
  - The Users table is now a named scroll region.
  - Reflow at 320 CSS px holds (WCAG 1.4.10).
- **Layout:**
  - The month heading moves above its links on a phone. It takes no focus, so the links' order is unchanged.
  - The nurse column narrows; tables that must stay whole wrap; wider ones scroll in their regions with the scrollbar as the cue (the project's pattern, kept).
- **Writing:** "Menu" and the existing words. No new copy, beyond the manifest's name and the description "Your unit's roster, your month, requests and swaps."
- **UI:** an X replaces the menu icon while it is open. No new colour, type or motion.

`interface-review` is yours to invoke.

**Things later tickets should know:**
- **Browser journeys (24):** the harness, the seed, the origin and what was left (comment left there).
- **Never add a `fetch` listener to `sw.js`** without reading this comment: `src/sw.test.ts` will fail first.
- **The dev stack was not touched.** When this branch reaches `main` it needs **no rebuild**:
  - Nothing changed in `deploy/compose.yaml`, `compose.dev.yaml`, the `Caddyfile` or the `Dockerfile`.
  - `.dockerignore` gained `e2e` (it only keeps the checks out of the build context).
  - The backend change is `config/settings.py` and `config/urls.py`, which the dev `web` reloads itself.
  - Vite serves the new `frontend/public` files at once.
  - **No new dependency in `frontend/` or the backend;** Playwright is `e2e/`'s alone.
  - The first visit after it registers the worker on `localhost:5173`. It handles no request, so it does not get in Vite's way.


**Reviewed by the user (2026-11-07):** all eleven points marked **Worth your review** are kept as built: a service worker with no `fetch` listener; browser checks against `web` over HTTP on localhost; the Menu button below 640 px; 44 px controls on every touch screen for every role; `no-cache` on every fixed-name file and `immutable` hashed assets; one reload of a tab from before a deploy; light only for now; no `viewport-fit=cover`; `e2e/` at the repo root with its own `package.json`; the Users page's actions sticky only from 640 px; the icon.
