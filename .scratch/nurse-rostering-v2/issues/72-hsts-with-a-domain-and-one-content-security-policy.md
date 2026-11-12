# 72: HSTS with a domain, and one content security policy

**What to build:** Every response through Caddy carries one `Content-Security-Policy`, replacing any `web` sent and extending ticket 62's `frame-ancestors 'none'` line: `default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'`, widened only where the browser checks prove the built SPA needs it. With `DOMAIN` set, every response carries `Strict-Transport-Security: max-age=31536000`, without `includeSubDomains` or `preload`; a self-signed installation never sends it. Caddy's own error pages (the 502 while a restore runs) carry neither, which is accepted. Spec: `.scratch/nurse-rostering-v2/specs/hardening.md` (Headers).

**Blocked by:** 62 Audit follow-ups (its `frame-ancestors` line); 71 Gunicorn runs threaded workers (the Caddyfile, `operations.sh` and the install guide), after 70

**Status:** ready-for-agent

- [x] One `Content-Security-Policy` header on a page, a static file and an API answer, set deferred so it replaces any the application sent, never two
- [x] The Playwright support file listens for content security policy violations on every page and fails the test that sees one; every existing journey, the push journey and the print page among them, passes with none
- [x] Each widening of the policy, if any, is named in the ticket comment with what needed it
- [x] HSTS in the Caddyfile snippet the `DOMAIN` mode imports, whose comment changes; no HSTS without `DOMAIN`
- [x] `deploy/INSTALL.md` says what HSTS means if the hospital later stops using its name, and the first real install's checks include it
- [x] `docs/ARCHITECTURE.md` section 8's Security names both headers
- [x] `docs/security/2026-11-11-security-audit.md`: the HSTS and CSP hardening note marked fixed, with this ticket's commits
- [x] Tests at the agreed seams: the Playwright browser checks; `deploy/tests/operations.sh` (the policy on a page and an API answer, no HSTS without `DOMAIN`, the header in the adapted configuration's `DOMAIN` snippet); both workflows

## Comments

**From ticket 69 (2026-11-11).** `deploy/Caddyfile` now has a global options block first, and the site's `reverse_proxy` has a
body. Ticket 62's `header Content-Security-Policy` line is unchanged, above `@metrics`; the compose-level check of ticket 69
sits right after `operations.sh`'s framing check.

**From ticket 70's review (2026-11-11):** the user chose to add a line here to `deploy/INSTALL.md`'s install checklist: at the first install with a `DOMAIN`, confirm a nurse import (or another request) that takes longer than a minute from a browser, which likely speaks HTTP/3 to Caddy, and see it complete. Ticket 70 drove HTTP/1.1 and HTTP/2 only (99 s and 94 s confirmations, both completed).

**Implemented on 2026-11-12,** on branch `claude/ticket-72-hsts-and-csp-a1e371` (`068adf9`, `d0e6663`, `c38014a`, `f1223be`,
then this comment), from `main` at `d759f0d`, with `main`'s `5b54f97` (ticket 52) merged in (`e841bde`). Draft pull request
[devjazzar/cp-sat-nurse-roster-app#24](https://github.com/devjazzar/cp-sat-nurse-roster-app/pull/24).
- **GitHub's two workflows.**
  - On `068adf9`: red, by design of the new listener. 123 reports of one violation, zod's eval probe (below), and the journey
    stopped at its first test. `operations.sh` passed there, the new checks among them.
  - On `c38014a`: green. Browser checks 75 passed, none failed, no violation reported. CI's backend, solver, frontend and
    image jobs passed too.
  - The head that reaches `main` was green again before the fast-forward.
- **Locally, under the lock, on the scratch stack `nr-t72`** (seeded, Caddy over HTTP on 18272 and HTTPS on 18672):
  - the desktop and phone-360 projects on `c38014a`: 33 passed, 1 failed. The failure was `cover.spec.ts`, from this
    stack's own leftovers: the first run, which the zod probe failed, left a leave for ICU Nurse 01. Its "Remove leave of
    ICU Nurse 01" button then matches `getByLabel('Nurse')` beside the form's select. GitHub's fresh stack passed it.
  - the frontend's new `src/lib/zod.test.ts`, and both typechecks (`tsc -b`, the checks' `tsc --noEmit`).
- **Not run locally:** the full frontend `npm test` and `npm run build`. My run waited on the heavy-run lock, which ticket 50
  held from 10:01, so they are GitHub's frontend job's (green on `c38014a`). `backend/` and `solver/` are untouched, so their
  suites are GitHub's too. No migration, no API change.

**What the dev stack needs:** `deploy/Caddyfile` changed, so `docker compose restart caddy` (ticket 62's finding: a
Caddyfile-only change does not recreate it). The frontend changed (`vite.config.ts`, `src/lib/zod.ts`), so
`docker compose up -d --build` rebuilds the image. No migration, no new dependency. `deploy/compose.yaml` is unchanged.

**What was built, criterion by criterion.**
- **One policy, deferred.** `deploy/Caddyfile`: `header >Content-Security-Policy "default-src 'self'; script-src 'self';
  style-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'"`,
  where ticket 62's line was. `caddy adapt` on `caddy:2.11` gives a `headers` handler with `"deferred": true` and `set`, so it
  replaces any `web` sent.
- **The listener.** `e2e/support.ts` exports `test`, Playwright's with an automatic fixture:
  - `addInitScript` adds a `securitypolicyviolation` listener on every page and frame of a context, before its first script,
    and reports each event through `exposeBinding`.
  - At the test's end, the test fails with a list of violations, one line each: the directive, what was refused (`eval`,
    `inline` or a URL), the source file and line, and the page.
  - It watches the test's own context, and any made with `browser.newContext` during the test (`newBrowser`, `another`, and
    `cover.spec.ts`'s own), by wrapping that call for the test's length.
  - Every spec imports `test` from `support.ts` now. `playwright.config.ts` refuses to start if a spec imports it from
    `@playwright/test`, naming the file, so a new spec cannot run unwatched.
- **The pages carry the policy.** The browser checks used to reach `web` directly, where Caddy's header never was, so a
  listener there would have passed on pages with no policy at all. `e2e/compose.e2e.yaml` now has Caddy answer also on
  `http://:8080` (`CADDY_SITE: "https://, http://:8080"`), published on `E2E_PORT`, with the site's own handling: headers,
  body limits, the proxy to `web`. `web` is no longer published, nor on the `public` network.
  - The checks' origin is still `http://localhost:<port>`, a secure context, so the service worker still registers.
  - `e2e/tests/desktop/policy.spec.ts` holds the listener to it:
    - `/login`, `/favicon.svg` and `/api/health` at the checks' origin each carry exactly the one policy, the same as Caddy's
      HTTPS port sends, and so does a page navigation;
    - an inline script and an inline style injected into a page, and into a second browser made by `newBrowser`, are each
      refused (the script did not run) and reported.
- **Widenings: none.** The policy is the spec's, as written. One violation was found, and it was removed in the app rather
  than allowed:
  - **zod 4's eval probe.** When the first object schema is built, zod runs `new Function("")` once, in a try, to decide
    whether to compile its fast parser. The policy refuses it, the browser reports `script-src refused eval` (from the
    `schemas` chunk, on every page), and zod falls back to its ordinary parser.
  - Allowing it would take `'unsafe-eval'`. Instead `frontend/src/lib/zod.ts` sets `config({ jitless: true })` and
    re-exports `zod/v4`, and `vite.config.ts` aliases the bare `zod` to it. Every `import { z } from "zod"` (35 files, and any
    a later ticket adds) therefore runs it before building a schema, whatever the chunks.
  - Zod's own source says why the setting exists ("strict CSPs report the caught `new Function` as a
    `securitypolicyviolation`"). Parsing is what zod already did after the refusal.
  - A first try, a side-effect import at the top of `main.tsx`, did not work: Vite put it in the entry chunk, which runs
    after the `schemas` chunk it imports. The browser checks caught that too.
- **HSTS.** `(self-signed-off)`, the snippet the `DOMAIN` mode imports, now holds
  `header >Strict-Transport-Security "max-age=31536000"`. Its comment says what it does, why there is no `includeSubDomains`
  or `preload`, and why self-signed never sends it. The Caddyfile's header comment says the snippet "adds only HSTS".
- **`deploy/INSTALL.md`.**
  - After "set `DOMAIN`", a paragraph on what HSTS means: a year from each browser's latest visit, that one name, no way past
    a bad certificate. If the hospital stops using the name: keep a valid certificate on it for a year (a redirect will do),
    or first send `max-age=0` and keep it answering until the users' browsers have each opened the app once more.
  - "At the first real install" gains "The headers at the hospital's name" (curl or developer tools: HSTS once, one policy;
    the hospital's own browsers' Console with no refusal), and ticket 70's line, below. The checklist gains one line for each.
- **`docs/ARCHITECTURE.md` section 8, Security:** both headers, their values, where they are set, the listener, zod
  `jitless`, and Caddy's error pages carrying neither. Ticket 62's framing sentence now points at the policy's
  `frame-ancestors`.
- **The audit:** a decision line "The HSTS and content security policy note ... fixed on 2026-11-12 in ticket 72, `068adf9`
  and `c38014a`", and the same in section 4's paragraph listing the hardening notes.
- **`operations.sh`:**
  - ticket 62's framing loop is now ticket 72's: on `/`, `/unit-roster`, `/favicon.svg`, `/api/health` and Caddy's `/metrics`
    404, exactly one `Content-Security-Policy`, the whole policy, `X-Frame-Options: DENY` from `web`, and no
    `Strict-Transport-Security`;
  - then the adapted configuration, read from the running Caddy (no `DOMAIN`): exactly one `headers` handler, the policy,
    deferred;
  - and adapted again inside the same container with `CADDY_SITE=roster.hospital.example` and
    `CADDY_TLS_SNIPPET=self-signed-off`, as a `DOMAIN` installation's would be: exactly the policy and HSTS
    `max-age=31536000`, both deferred.
  - Both are near the top, well before ticket 71's last check. The JSON walk over handlers is now one shell function,
    `handlers <kind>`, which ticket 71's `reverse_proxy` check uses too.
- **From ticket 70's review:** the install checklist and "At the first real install" now say: at the first install with a
  `DOMAIN`, confirm a nurse import longer than a minute from a browser, likely over HTTP/3 (UDP 443), see it complete with
  the passwords shown, and read `h3` in the Network tab's Protocol column.

**What was driven, and how.**
- A throwaway `caddy:2.11` (`docker run --rm`, the checkout's Caddyfile read-only) to adapt the Caddyfile in both modes, and
  first to see that `CADDY_SITE="https://, http://:8080"` adapts: two servers, `:443` and `:8080`, each with the same headers,
  body limit, `/metrics` refusal and `reverse_proxy`.
- The stack `nr-t72` via `e2e/stack.sh up`, `rebuild` twice, then `down`: no container and no volume of it is left. Chromium
  by Playwright, through Caddy's HTTP port, as every role the desktop and phone-360 projects sign in as.

**What was found, and fixed:** zod's eval probe (above). **Findings for you, not fixed:** `cover.spec.ts` is not re-runnable
on a stack where a run failed after recording its leave. `getByLabel("Nurse")` also matches the leave list's "Remove leave of
ICU Nurse 01" button. `{ exact: true }` there would end it; it belongs to the cover checks' owner.

**What was NOT checked.**
- **HSTS on a live answer.** Only in the adapted configuration: no stack here has a `DOMAIN`, and a certificate for a real
  name cannot be had while building. The first real install checks it.
- **The push journey.** There is none in the browser checks: tickets 41 and 42 added no Playwright check, as a Chrome launched
  by Playwright receives no push. What the checks do cover: the service worker registers and controls pages under the policy
  (`pwa.spec.ts`), and every page of every role opens with no violation, Settings among them. Turning pushes on
  (`pushManager.subscribe`) was not driven; the policy does not govern the browser's own call to its push service. The
  print pages are covered (`narrow.spec.ts`, the print pages at 360 and 320 px, no violation).
- **Violations inside the service worker's own scope:** the listener is on documents only. The worker has no `fetch` listener
  and imports nothing.
- **Other browsers:** Chromium only. The install checklist asks for the hospital's own.
- **Caddy's own error pages** (the 502 while `web` restarts) carry neither header, as the spec accepts; not driven.
- **The full frontend suite locally** (above).

**Decisions taken here.**
- **The checks' origin is Caddy over plain HTTP,** not `web` sending a copy of the policy. With a copy in Django, the checks
  would hold `web`'s policy, not Caddy's, and two copies could drift. The plain-HTTP address exists only in
  `e2e/compose.e2e.yaml`; `deploy/` gains nothing.
- **zod `jitless` through a Vite alias,** not `'unsafe-eval'` and not a change to 35 imports (above).
- **The listener reports at the test's end, every violation at once,** rather than throwing at the first. One failure then
  shows the whole list, and a page's own assertion failures are not masked.
- **`policy.spec.ts`** is a check, not a journey (the spec says "No new journey"). Without it, nothing shows the listener
  sees anything, or that the pages carry the policy at all.

**Worth your review.**
- **No widening, and the zod alias that made none necessary.** The alternative is `script-src 'self' 'unsafe-eval'`, the one
  widening the built SPA would have needed. `jitless` costs zod's compiled fast path for object parsing, nothing that the
  refusal had not already cost.
- **How the listener reports:** at the test's end, one line per violation (directive, refused, source, page). It also changes
  how specs are written: `test` comes from `support.ts`, and the config refuses `@playwright/test`'s.
- **The INSTALL.md words on HSTS,** in particular the advice for retiring the name: keep a valid certificate a year, or send
  `max-age=0` first.
- **The browser checks now pass through Caddy:** its 2 MB body cap, its headers, and `/metrics` refused at the checks'
  origin. The pwa check that fetches `/metrics` from the page now gets Caddy's 404 and still counts it as not cached.

**The code review** (`code-review` against `d759f0d`, Standards and Spec, before this comment):
- Standards, the JSON walker in `operations.sh` duplicated ticket 71's: fixed, one `handlers <kind>` (`f1223be`).
- Standards, the policy string in four places (Caddyfile, `operations.sh`, `policy.spec.ts`, ARCHITECTURE): kept. The two
  tests are independent oracles of the written policy; reading it from the Caddyfile would test the Caddyfile against itself.
- Standards, `export { expect }` from `support.ts` unused: removed (`f1223be`).
- Standards, `(self-signed-off)` named for what it is not: kept. `compose.yaml` derives the name from `DOMAIN`, and the
  comments now say what it holds.
- Standards, `src/lib/zod.ts` as a re-exporting middle man: kept. It must sit in the import path (above).
- Standards, the config's import guard would be a lint rule: kept, as `e2e/` has no ESLint.
- Spec, the ticket comment to name the zod probe and say no widening: done, here.
- Spec, the audit citing only `068adf9`: fixed, it names `c38014a` too (`f1223be`).
- Spec, `policy.spec.ts` beyond "No new journey": kept, and put to you above (Decisions).
- Spec, the `max-age=0` advice beyond "what the header means": kept, as the way out the meaning implies.
- Spec, the alias, the compose overlay's network and the import guard: kept, recorded above.

**Things later tickets should know.**
- Import `test` from `e2e/support.ts` in any new spec; `playwright.config.ts` refuses one that does not.
- A test that opens a page with `browser.newPage()` (not `newContext`) is not watched. None does today.
- Anything new the SPA loads from elsewhere, an inline `style=""` in HTML (React's `style` prop is fine) or a library that
  injects `<style>` will fail the browser checks with the directive named. Widen `deploy/Caddyfile`'s policy only for a real
  need, and name it in the ticket comment.
- The checks' origin is Caddy: a request over 2 MB is refused there as at a hospital, and `web` is not reachable from the host
  in an e2e stack (`docker compose exec` still is).
