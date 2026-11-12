# 71: Gunicorn runs threaded workers

**What to build:** Each web worker serves several requests at once, so one hash, one import or one slow request holds a quarter of one worker and not a third of the pool. Gunicorn runs `--worker-class gthread --threads 4 --workers 3`, with `--timeout` at gunicorn's default, which under `gthread` is only how long a worker's main loop may go silent: a 500-row import is never killed at 300 seconds. Caddy's idle time on its connections to `web` is shorter than gunicorn's keep-alive, so Caddy never reuses a connection gunicorn has just closed. Spec: `.scratch/nurse-rostering-v2/specs/hardening.md` (Caddy and gunicorn, Keep-alive).

**Blocked by:** 70 Caddy holds the body (the Caddyfile's `reverse_proxy` block and the same checks in `operations.sh`)

**Status:** ready-for-agent

- [ ] The web command runs `gthread`, 3 workers of 4 threads, with `--timeout` at its default; the comment above it, which sized 300 s for the import, is rewritten
- [ ] Caddy's idle keep-alive to `web` is shorter than gunicorn's `--keep-alive`; the ticket comment says how it was checked
- [ ] A search of the application for mutable module-level state a thread could race on, with what it found and what was done about it, in the ticket comment
- [ ] `docs/ARCHITECTURE.md`: section 2 (web's command) and ADR 0009's connection count in the architecture (web at most 12, beside the worker's 9)
- [ ] `deploy/INSTALL.md`: the 500-row import is still timed at the first real install, with no limit to stay under
- [ ] `docs/security/2026-11-11-security-audit.md`: lead 3's worker half marked fixed, with this ticket's commits
- [ ] Tests at the agreed seams: `deploy/tests/operations.sh` (gunicorn running threaded); the browser checks pass on the threaded server; both workflows

## Comments

**From ticket 69 (2026-11-11).** gunicorn's access line now takes `remote` from `X-Client-IP`, the header Caddy always sets,
else the peer (`solver/solver_service/logs.py`). `audit.log.client_ip` keeps no state, so threads change nothing there.

**From ticket 70 (2026-11-11).**
- `deploy/Caddyfile`'s `reverse_proxy web:8000` block now holds `header_up X-Client-IP {client_ip}` and `request_buffers 2MiB`.
  Caddy's idle time to `web` goes in a `transport http { keepalive … }` there (check its name with `caddy adapt` on
  `caddy:2.11`, as ticket 70 did).
- `deploy/tests/compose.one-worker.yaml` replaces web's whole `command` for `operations.sh`'s held-body check:
  `--workers 1 --threads 1`, no `--worker-class`, no `--timeout`. Once compose.yaml says `gthread`, mirror it there
  (`--worker-class gthread --threads 1`) so the check still runs one request at a time on the same kind of worker. The check
  also counts gunicorn processes in `web` (master plus one), which stays true under `gthread`.
- That check now asserts a withheld login never reaches `web` at all, read from web's access lines (`/api/auth/login`).
  Django reads no chunked body, so under sync workers a chunked login passed on is answered at once. Under `gthread` with
  keep-alive, gunicorn may try to read the rest of such a body before the connection's next request; Caddy no longer passes
  one on, which is why `request_buffers` is larger than the 2 MB cap.
- Caddy's minimum body rate runs from the body's start: 1 minute, plus a tenth of a millisecond for each byte received. A
  2 MB body therefore has at most 260 s to arrive. Once it is in, nothing bounds the request: confirmations of 140 rows took
  99 s (HTTP/1.1) and 94 s (HTTP/2) through Caddy on a scratch stack with `web` held to one CPU (`docker update --cpus 1`),
  and both finished. That is the setup for timing the 500-row import without the 300-second limit.

**Implemented on 2026-11-12,** on branch `claude/ticket-71-gunicorn-threaded-4064f2` (`256943e`, `1327ea6`, `d631db4`, then
this comment), from `main` at `3579d76`, with `main`'s `a93f88f` (tickets 45, 46 and 58) merged in. Draft pull request
[devjazzar/cp-sat-nurse-roster-app#18](https://github.com/devjazzar/cp-sat-nurse-roster-app/pull/18).
- `deploy/tests/operations.sh nr-t71`, under the heavy-run lock, on `1327ea6`: all checks passed, the five new ones among them.
  `d631db4` changed only how those checks fail and their names (the review, below); GitHub ran it again.
- Backend `pytest` on a throwaway PostgreSQL 18, on `d631db4`: 3331 passed. `makemigrations --check`: no changes. Only a docstring changed in `backend/`. No solver, frontend
  or Playwright file changed, so neither suite ran locally. No migration, no API change.
- GitHub's two workflows: green on `d631db4` (backend after one rerun, below), and the head that reaches `main`, this
  comment's commit after the merge, was green again before the fast-forward.
- **A flake, not this ticket's:** the first backend run on `d631db4` failed
  `ops/tests/test_logs.py::test_the_queues_command_line_logs_what_it_would_print`. Django printed the system-check warning
  `fields.W161` for `ops.TechnicalSettings.close_time` (`default=time(0, 30)`). Django's check combines a `TimeField`'s
  default with today and warns when it falls within 10 s of now, so it fires for any run between 00:29:50 and 00:30:10 UTC.
  The test ran at 00:30:1x. Once a day, any session's run at that minute fails. The rerun passed.

**What the dev stack needs:** `deploy/compose.yaml` (web's command) and `deploy/Caddyfile` changed, so `docker compose up -d
--build` recreates `web`, and `docker compose restart caddy` is needed for the Caddyfile (a Caddyfile-only change does not
recreate it, ticket 62's finding). No migration, no new dependency.

**What was built, criterion by criterion.**
- **The command.** `gunicorn config.wsgi -c config/gunicorn.py --bind 0.0.0.0:8000 --worker-class gthread --workers 3
  --threads 4 --keep-alive 10`, with no `--timeout`, so gunicorn's 30 s. The comment above it, which sized 300 s for the
  import, now says what the threads change, what the timeout means under `gthread`, the connection count and the keep-alive
  pair. `tests/compose.one-worker.yaml` mirrors it at `--worker-class gthread --workers 1 --threads 1 --keep-alive 10`
  (ticket 70's ask).
- **Keep-alive.** In the Caddyfile's `reverse_proxy web:8000`: `transport http { keepalive 2s }`, beside `header_up` and
  `request_buffers`. `caddy adapt` on `caddy:2.11` (v2.11.9) gives `"transport": {"keep_alive": {"idle_timeout": 2000000000},
  "protocol": "http"}`; `caddy validate`: "Valid configuration". How it was checked:
  - **From gunicorn's source** (26.2.0's `workers/gthread.py`, read in the image). After an answer, a connection goes back to
    the poller with `timeout = now + keepalive`. `murder_keepalived` closes it once that has passed, run each turn of the
    main loop, which wakes at least once a second. So gunicorn closes an idle connection no sooner than 10 s after it
    finished writing, and up to about 11 s.
  - **In `operations.sh`, from the running stack.**
    - gunicorn's own parser reads PID 1's command line, with `config/gunicorn.py` and any `GUNICORN_CMD_ARGS`, and gives
      `gthread 3 4 30 10` (class, workers, threads, timeout, keep-alive).
    - Caddy's adapted configuration is walked for every `reverse_proxy`, and each `idle_timeout` must be under 10 s.
    - Five POSTs (`{}` to the login, which web refuses with 422) went through Caddy after gaps of 0.5, 1.5, 2.5, 9.5 and
      10.5 s. All five answered 422, none 502.
  - **What that does not prove:** the 502 itself was not reproduced. Go's transport notices a peer's close on an idle
    connection as soon as the FIN arrives, so the race is a window of microseconds, which no test here can hit on demand.
    The driven POSTs catch Caddy's `keepalive` going missing (its default is longer than 10 s), not the race.
- **The search for mutable module-level state** (backend and solver, outside tests and migrations), what it found and what
  was done:
  - **Searched:**
    - `global` and `nonlocal`;
    - `lru_cache`, `cache` and `cached_property`;
    - `threading` and `contextvars`;
    - every module-level assignment of a list, dict, set or `defaultdict`, and every module-level object built by a call;
    - class-body mutable attributes (an AST scan);
    - mutable default arguments;
    - `setlocale`, `os.environ` writes, `os.chdir` and `socket.setdefaulttimeout`.
  - **Found, and safe as it stands:**
    - **Lookup tables, never written after import:** `covers/steps.py`, `notifications/kinds.py`, `rosters/drafts.py`'s
      `FROZEN`, `hospital/rules.py`'s `DEFAULT_RULES` (copied with `deepcopy` before use) and the rest.
    - **Defaults merged with `|` into new dicts:** `closes/chain.py`'s `NO_HISTORY` and `NEW_YEAR`,
      `solves/comparison.py`'s `_CARRIED_BEFORE` and `_SHIFT_FIELDS`, `units/rules.py`'s `_HEADCOUNT`, and the solver's
      version-2 upgrade defaults. They share their empty lists with what they make, but nothing appends to those lists in
      place (grepped).
    - **Auth objects** (`SignedIn`, `SignedInForAFile`): they keep only their roles and read the request.
    - **The public health answer:** `ops.public_health.HeldAnswer` is the one value a request changes, and it already takes a
      lock (ticket 68).
    - **Pydantic fields** with `[]` defaults: copied for each instance.
    - **`notifications.pushing.push_service`**, a module-level `requests.Session`: only the worker's push job uses it, never
      `web`, so threads in `web` change nothing (Findings, below).
    - **The clocks:** `ops.public_health.clock` and `notifications.pushes.clock` are module-level clocks only the tests move.
      The browser checks' clock is read from its file each time.
    - **The import's hash pool** (`accounts.provisioning.new_passwords`): a `ThreadPoolExecutor` inside the request, four
      threads that hash and touch no database, as before.
  - **Done:** nothing needed changing. Database races existed already across three processes and are each handled where
    they are (row locks, the queue's locks). Threads add only memory shared within a process, and the search found none
    that a request writes, apart from the locked health answer.
- **`docs/ARCHITECTURE.md`.** Section 2 gains a paragraph on web's command: the threads, what the timeout means, the
  keep-alive pair, at most 12 database connections beside the worker's 9 against 100 (each thread opens at most one, closed
  at the request's end, as `CONN_MAX_AGE` is unset), and no mutable module state but the locked health answer. Section 8's
  import paragraph no longer says the row limit keeps it inside 300 s. ADR 0009's consequence on connections gains a dated
  line (12 for web, 21 in all; the decision unchanged).
- **`deploy/INSTALL.md`.** "The 500-row nurse import, timed": nothing cuts the request short, so there is no limit to stay
  under, only how long the CNO waits. The backup, import, time and restore steps stay; "raise `--timeout`" is gone.
  `nurses/importing.py`'s docstring says the same.
- **The audit.** Lead 3: "Fixed: at Caddy in ticket 70 (`174e1bf`), at the workers in ticket 71 (`256943e`)", in its row,
  the paragraph above the table and the user's decisions. Lead 1's row notes that the hash now holds one of twelve threads.
- **Tests.** `operations.sh`:
  - a new section after the log checks: the running settings, "Using worker: gthread" logged once, master plus three
    workers, Caddy's idle time under the keep-alive, and the spaced POSTs;
  - the held-body checks now run on one `gthread` worker of one thread, and passed (master plus one, no withheld login
    reaching `web`);
  - a last check: with `web` held to one CPU, a confirmation of 100 nurses took 69.3 s here, past gunicorn's 30 s, and ended
    with 201 and 100 passwords, with no `WORKER TIMEOUT` in web's log. The browser checks ran on the threaded server on
    GitHub (`e2e/compose.e2e.yaml` keeps compose.yaml's command for `web`).

**What was driven, and how.** The scratch stack of `operations.sh nr-t71` (Caddy on 18471), curl and gunicorn's own parser,
under the lock. Red first, cheaply: gunicorn's parser on `main`'s command gives `sync 3 1 300 30 2`, which the new check
refuses. The stack was removed by the script, and nothing of it is left (no container, no volume).

**What was found, and fixed:** nothing in the application. **Findings for you, not fixed:**
- The daily W161 flake (above): a test that asserts an empty stderr from `manage.py` fails within 10 s of 00:30 UTC.
  Silencing `fields.W161` for that field, or a callable default, would end it. It belongs to whoever owns `ops`' settings
  model, not to this ticket.
- `notifications.pushing.push_service` is one `requests.Session` shared by the worker's four concurrent jobs. That was already
  so before this ticket, and only the push job uses it. `requests` does not promise a `Session` is thread-safe, though
  plain requests with no cookies, as here, are the usual safe case. If a push ever misbehaves under load, one session per
  send is the change.

**What was NOT checked.**
- The 502 race itself (above).
- A 500-row import: 100 rows on one CPU, past the timeout, is what was shown. The first real install still times 500.
- A long request under HTTP/3 (ticket 70's open point stands).
- Throughput or latency under threads: nothing was measured beyond the checks above.

**Decisions taken here.**
- **Keep-alive 10 s at gunicorn, 2 s at Caddy.**
  - gunicorn's default of 2 s left no room under it. Its 10 s is only a backstop, since Caddy lets go first.
  - An idle connection in a `gthread` worker holds no thread, only a socket (at most 996 a worker).
  - Caddy's 2 s keeps few connections open. It also lets a stopping `web` finish quickly: in a graceful stop, gunicorn
    waits on its open connections until they close or the 30 s grace runs out, and compose kills `web` after 10 s.
  - The 8 s between the two leave room for a long answer Caddy is still reading off the socket after gunicorn finished
    writing it.
- **The timeout is checked as gunicorn's own default** (`Config().timeout`), not as the literal 30.
- **The long confirmation runs last in `operations.sh`,** so `web` can stay at one CPU, at 100 rows: about 0.7 s a row here.
  That is enough margin past 30 s on a faster CPU while adding about a minute to the run.

**Worth your review.**
- **The keep-alive values,** 10 s and 2 s (Decisions). Any pair with Caddy's under gunicorn's meets the spec. A shorter Caddy
  idle means more new connections to `web`, which are cheap on the internal network. A longer gunicorn keep-alive slows a
  graceful stop only if Caddy holds the connection.
- **The module-level search found nothing to change.** The one shared object it named, the push `Session`, is the worker's
  and predates this ticket (Findings).
- **The long-confirmation check depends on timing.** A machine fast enough to hash 100 passwords on one CPU in under
  30 s would fail it, with a message that says the check showed nothing. At the measured 0.5–0.7 s a hash that is about
  twice as fast as anything seen.
- **Settings now in more than one place.** The command's settings are written in compose.yaml, the one-worker override,
  `operations.sh`'s assertions and the docs, as ticket 70's were.

**Review.** `code-review` against `3579d76`, both axes in fresh sub-agents.
- **Standards:** no hard violation. Fixed in `d631db4`:
  - a refused POST in the spaced loop would have ended the script under `set -e` with no `FAILED` line (now `|| true`);
  - the process count fails loudly;
  - the keep-alive is asserted to be 10;
  - the confirmation's status is checked before its duration, and the old sheet removed first;
  - `running`, `idle` and `timeout` renamed `gunicorn_settings`, `caddy_idle` and `gunicorn_timeout`;
  - the docstring rewrapped to the file's width.

  Kept:
  - the CSV heredoc beside ticket 70's: two small copies, each readable where it stands;
  - the settings as literals rather than moved into `config/gunicorn.py`: the spec and the ticket name the command line,
    and the test reads the effective values either way.
- **Spec:** nothing missing. Fixed:
  - audit lead 1 still said "three sync workers" and now notes the twelve threads;
  - the Caddyfile's margin is worded as room, not a guarantee.

  Kept: ADR 0009's dated consequence line, since the ADR's own count would otherwise contradict the architecture.

**Things later tickets should know.**
- **72 (HSTS and the content security policy):**
  - The Caddyfile's `reverse_proxy web:8000` block now holds `header_up`, `request_buffers` and `transport http {
    keepalive 2s }`. The site's order is unchanged: the CSP `header`, `request_body`, `@metrics`, `reverse_proxy`.
  - `operations.sh` gained a section between the log checks and ticket 70's, and a last check after the 1 MiB import that
    leaves `web` at one CPU. A check added after it runs on that CPU, or should go before it.
  - The install guide's import bullet was rewritten; nothing else there moved.
- **Anyone adding module-level state:** web now runs four threads a process. Anything a request writes outside the request
  needs a lock, as `ops.public_health` does.
