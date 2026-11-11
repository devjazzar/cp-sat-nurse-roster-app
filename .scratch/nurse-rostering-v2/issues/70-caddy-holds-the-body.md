# 70: Caddy holds the body

**What to build:** No web worker waits on a client's body. Caddy refuses a request body over 2 MB with 413, reads the whole body before it opens the request to `web`, and drops a body that stalls for a minute or arrives slower than 10 kB/s on average. There is no whole-request read deadline, so a long confirmation or download is never cut off once its body is in. A 1 MB nurse import still goes through. The image stays `caddy:2.11`. Spec: `.scratch/nurse-rostering-v2/specs/hardening.md` (Caddy and gunicorn, Q17's correction in the Caddyfile bullet); ADR 0001, ADR 0015.

**Blocked by:** 69 The client address Caddy works out, and the hospital's proxies (the same global options block)

**Status:** ready-for-agent

- [x] The site has a request body cap of 2 MB and `reverse_proxy` request buffers of 2 MB
- [x] The server's stalled-body timeout stays at its 1-minute default and gains a minimum rate of 10 kB/s; no `read_body` (a deadline on the whole request) is set, and the Caddyfile's comment says why
- [x] The other timeouts stay at Caddy's defaults: no write timeout; the minimum rate's syntax confirmed by `caddy adapt` on the running image
- [x] A 1 MB import file previews and confirms through Caddy
- [x] `docs/ARCHITECTURE.md` section 2 says what Caddy limits
- [x] `docs/security/2026-11-11-security-audit.md`: lead 3 marked fixed at Caddy, with this ticket's commits
- [ ] Tests at the agreed seams: `deploy/tests/operations.sh` checks the running Caddy is 2.11.8 or later, a body over 2 MB is 413, with the test stack's `web` overridden to one worker of one thread for this check (with three, one held request would never show), a login whose body is withheld does not stop `/api/health` answering through Caddy (one connection), and the adapted configuration has the minimum rate and no `read_timeout`; both workflows

## Comments

**From ticket 69 (2026-11-11).** `deploy/Caddyfile` now opens with a global options block, `{ servers { trusted_proxies
static {$TRUSTED_PROXIES}; trusted_proxies_strict; client_ip_headers X-Forwarded-For } }`: `read_body_idle` and the minimum
body rate go in that same `servers` block. `reverse_proxy web:8000` now has a body (`header_up X-Client-IP {client_ip}`), so
`request_buffers` goes beside it. Confirm with `caddy adapt` and `caddy validate` on `caddy:2.11` with `TRUSTED_PROXIES` empty.

**Implemented on 2026-11-11,** on branch `claude/ticket-70-caddy-holds-body-6c1852` (`174e1bf`, `115969f`, `0ada95d`, then
this comment), from `main` at `472f71f`, with `main`'s `e8b1308` ([skip ci], the v2 index) merged in. Draft pull request
[devjazzar/cp-sat-nurse-roster-app#14](https://github.com/devjazzar/cp-sat-nurse-roster-app/pull/14).
- `deploy/tests/operations.sh nr-t70`, under the heavy-run lock, on `0ada95d`: all checks passed, the six new ones and the
  import among them.
- No backend, frontend, solver or Playwright file changed, so their suites were not run locally; no migration, no API change.
- GitHub's two workflows on the pull request: the last criterion below is ticked once both are green on the head that reaches
  `main`.

**What the dev stack needs:** `deploy/Caddyfile` changed and nothing else the stack runs, so `docker compose restart caddy`
(a Caddyfile-only change does not recreate it, ticket 62's finding). `docker compose up -d --build` then changes nothing more.
`deploy/tests/compose.one-worker.yaml` is the test's alone.

**What was built, criterion by criterion.**
- **The cap and the buffers.** The site has `request_body { max_size 2MB }` (2,000,000 bytes) before `reverse_proxy`, and
  `reverse_proxy web:8000` has `request_buffers 2MiB` (2,097,152) beside `header_up X-Client-IP {client_ip}`. Why the buffers
  are larger than the cap, not equal: Decisions.
- **The body timeouts.** In the global `servers` block, `timeouts { read_body_idle 1m 10000 }`: the stalled-body minute, Caddy's
  default written out to give it the rate, and 10,000 bytes a second. No `read_body`; the Caddyfile's comment says why (Go
  cancels the request when that deadline fires, after the body or not). Adapted: `read_idle_timeout` 60 s, `read_min_rate`
  10000.
- **The other timeouts.** None set, so Caddy's: headers 1 minute, idle 5 minutes, a stalled write 1 minute (read in v2.11.9's
  `app.go`), no write timeout. `caddy adapt` and `caddy validate` on `caddy:2.11` (v2.11.9), `TRUSTED_PROXIES` empty, with
  `DOMAIN` unset and set: "Valid configuration" both times, the same server options both times.
- **A 1 MB import.** A file of exactly 1 MiB (`MAX_BYTES`: three nurses and blank lines, which the import skips) previews with
  a token and confirms with 201 and three rows through Caddy, in `operations.sh`.
- **`docs/ARCHITECTURE.md` section 2:** a paragraph after the networks on what Caddy limits, and what it does not.
- **The audit:** lead 3 marked "Fixed at Caddy in ticket 70 (`174e1bf`); the worker half is ticket 71's", in its row, the
  paragraph above the table and the user's decisions.
- **Tests.** `operations.sh`, after the log checks (it recreates `web`, whose logs those read): the running Caddy is 2.11.8 or
  later; the adapted servers have the minimum rate and the minute, and no `read_timeout`, `write_timeout`,
  `read_header_timeout` or `idle_timeout`; 2,000,001 bytes is 413 and 2,000,000 reaches `web` (Django's 400); then, with `web`
  at one worker of one thread (`tests/compose.one-worker.yaml`, the process count checked), a login declaring 64 bytes and
  sending none, and a chunked login of 2,000,000 bytes without its last chunk, each on one connection: `/api/health`
  answers 200 through Caddy within 10 seconds, and `web` logs no `/api/auth/login` meanwhile. `web` is then put back on its
  own command and answers through Caddy before the backup checks.

**What was driven, and how.** A scratch stack (`e2e/stack.sh up nr-t70 --empty`, Caddy on 18171), through Caddy with curl and
a Python client:
- **Red first,** on `main`'s Caddyfile: the adapted-configuration check failed, 2,000,001 bytes answered 400 (it reached
  Django), and with the declared-but-withheld login `/api/health` answered nothing in 10 seconds. The chunked case passed on
  `main` too: Django reads no chunked body, so it answers such a login at once.
- **A stalled body** (headers, then nothing): Caddy answered 499 and closed at 60.0 s.
- **A slow body,** 5 kB/s of a declared 1.5 MB: closed at 119.8 s after 597,500 bytes, which is the 60 s plus 597,500 ÷ 10,000
  the source predicts.
- **An adequate body,** 20 kB/s of 1.5 MB: all of it in after 75.9 s (past the minute) and passed on (Django's 400).
- **A long confirmation is not cut off:** with `web` held to one CPU (`docker update --cpus 1`), nurse imports of 140 rows
  confirmed with 201 in 99.4 s over HTTP/1.1 and 94.2 s over HTTP/2 (80 rows: 56.8 s and 60.1 s). Caddy clears the body's
  deadline once the body is in, on both paths.
- **Buffers equal to the cap:** with `request_buffers 2MB`, the chunked login of exactly 2,000,000 bytes reached `web` (two
  lines in its log) while its last chunk was withheld; with `2MiB` it did not. The new `operations.sh` assertion failed on
  `2MB` and passed on `2MiB`.
- The stack was removed (`e2e/stack.sh down nr-t70`); nothing of it is left.

**What was NOT checked.**
- HTTP/3: no client of mine spoke it (Worth your review).
- A 413 for a chunked body over the cap (no `Content-Length`): by the source, `MaxBytesReader` stops it at 2,000,000 bytes,
  but it was not driven.
- The 1 MiB import in a browser: `operations.sh` sends it with curl through Caddy. The browser checks reach `web` directly,
  not through Caddy (`e2e/compose.e2e.yaml`), so no Playwright test fits.
- The stalled and slow drops are not in `operations.sh`: each takes one to two minutes. The adapted configuration is checked
  instead.

**Decisions taken here.**
- **`request_buffers 2MiB`, not 2 MB.** In v2.11.9's `bufferedBody`, a body that fills the buffers exactly is passed on with
  the rest still to come from the client. With buffers equal to the cap, a chunked body of exactly the cap whose end never
  comes reaches `web` (driven above). With buffers larger than the cap, Caddy keeps reading and the cap or the rate ends it.
- **10 kB/s is 10,000 bytes a second,** not 10,240.
- **The cap is 2 MB, 2,000,000 bytes** (`2MB` in Caddy is decimal), above 1 MiB plus multipart and below Django's 2.5 MiB.
- **The one-worker override replaces web's whole command,** without `prepare` (it ran at the first start) and without
  `--timeout`. It is applied for that check alone, through a function, so `restore.sh` and the exit trap keep the test's
  own `COMPOSE_FILE`.
- **A request carrying `Incremental: ?1` is refused** by Caddy now that `request_buffers` is set (`refuseIncremental`, v2.11.9
  `incremental.go`). Only a client asking to stream its body sends that header. Nothing in `frontend/src` or `e2e/tests`
  does.
- **The held check reads web's access lines** as well as the health answer, so the chunked case can fail.

**Worth your review.**
- **How the 10 kB/s minimum works in Caddy's terms.** It is not a rate per window. The deadline is the body's start, plus
  1 minute, plus a tenth of a millisecond for each byte received. A body must keep its average above 10 kB/s after a
  minute's grace. A client that sent fast and then stalled may stall for longer than a minute, up to its credit. Any body
  the 2 MB cap allows has at most 260 s to arrive.
- **HTTP/3, not driven.** Caddy answers with `Alt-Svc: h3`, so a browser on an installation with a real certificate will
  likely move to HTTP/3 after its first answer. A long confirmation from a browser would then take the one path not driven
  here. The idle reader's `DrainDeadline` and `ClearBetweenReads` are set for HTTP/1 and HTTP/2 only. I had no HTTP/3 client
  (the macOS curl and `curlimages/curl` lack it). Worth one confirmation over a minute from a browser on the first
  installation with a domain, or a check with an HTTP/3 curl.
- **The buffers are 2 MiB, not the spec's 2 MB** (Decisions): the one place the build departs from the spec's numbers.
- **The test's one-worker override** is a third compose file applied to `web` for that check and then removed. The
  alternatives were a second stack (slower) or the whole test stack at one worker (every other check would run on it).
- **The health check waits a fixed 2 seconds** after the login is withheld, for a passed-on request to reach the one
  worker, before it asks `/api/health`. A positive assertion follows, but the 2 seconds are a guess at "long enough".

**Review.** `code-review` against `472f71f`, both axes in fresh sub-agents.
- Standards: no hard violation. Judgement calls fixed in `0ada95d`:
  - the override call moved from a variable to a function (section 6's rule);
  - `cno` renamed `cno_password`, and `at` renamed `at_cap`;
  - the chunk sizes are now named;
  - the adapt output is captured once;
  - the header comment rewrapped.

  Kept: the numbers in the Caddyfile, the test and the docs. Each says what it holds, and one variable shared across them
  would hide the literal the test asserts. Also kept: the fixed `sleep 2`, now commented.
- Spec: no defect. The buffers' departure is recorded above. Fixed in `0ada95d`:
  - the 2,000,000-byte body now must reach `web` (400), not merely not be 413;
  - the adapt check fails with no servers;
  - it also refuses `read_header_timeout` and `idle_timeout`.

  The one-thread half of "one worker of one thread" is the command's `--threads 1`. Under sync workers there is no other.

**Things later tickets should know.**
- **71:** a comment there: the override file to mirror for `gthread`, where Caddy's keep-alive to `web` goes, and how a long
  import was timed through Caddy.
- **72:** the site block's order is now the CSP `header`, `request_body`, `@metrics`, `reverse_proxy`. Server-wide options
  stay in the global `servers` block, beside `timeouts`.
- **65:** `operations.sh` gained a section after the log checks and one at the end (the import). Neither touches the restore's
  checks.
