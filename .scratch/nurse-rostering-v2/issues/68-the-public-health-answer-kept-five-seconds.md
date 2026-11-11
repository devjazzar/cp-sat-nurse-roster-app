# 68: The public health answer kept five seconds

**What to build:** `GET /api/health`, which anyone may call, keeps its answer for five seconds in each web process, so a client polling it cannot make the application call the solver on every request. The compose health check reads it as before. The System Admin's health page is not cached. Spec: `.scratch/nurse-rostering-v2/specs/hardening.md` (The public health answer).

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [x] Within five seconds a second public health request does not call the solver or the database again and gives the same answer; after five seconds it does
- [x] The System Admin's `/api/ops/health` and `/metrics` are not cached
- [x] The web service's compose health check still turns healthy at start; with the database gone, the public answer says so within five seconds of its kept copy running out
- [x] `docs/ARCHITECTURE.md` section 8's Observability says the public answer is kept five seconds
- [x] `docs/security/2026-11-11-security-audit.md`: the health hardening note marked fixed, with this ticket's commits
- [x] Tests at the agreed seams: the backend API suite; the usual full suites and both workflows

## Comments

**Implemented on 2026-11-11,** on branch `claude/ticket-68-health-kept-50e15c` (`7e5f7ed`, `eee09a3`, `77f79f4`, then this
comment), from `main` at `5230b55`. Draft pull request
[devjazzar/cp-sat-nurse-roster-app#7](https://github.com/devjazzar/cp-sat-nurse-roster-app/pull/7).

The suites ran locally under the heavy-run lock, the backend on a throwaway PostgreSQL 18 container of my own:
- the backend, on `eee09a3`: 3131 passed. After the review's renames (`77f79f4`) I reran the files they touch
  (`ops/tests/test_health.py`, `test_metrics.py`, `test_installation.py`, `accounts/tests/test_authorization.py`): 853 passed;
- the frontend: no frontend file changed, so `npm test`, the build and the six parallel runs were left to GitHub's workflow;
- `makemigrations --check`: "No changes detected";
- the OpenAPI document was exported again and is unchanged: the route's docstring, response and schema are as they were;
- no Playwright file changed, and `deploy/tests/operations.sh` did not change either. Both GitHub workflows, the browser
  checks and `operations.sh` among them, passed on the pull request.

**What the dev stack needs:** a **rebuild** (`docker compose up -d --build`) for the backend change. There is no migration,
no new dependency, and no change to compose, the Caddyfile, the `Dockerfile` or the solver.

**What was built, criterion by criterion.**
- **Within five seconds, the same answer and nothing asked again; after five, asked again.**
  - `ops.public_health.HeldAnswer` holds the answer `GET /api/health` worked out until five seconds (`HELD_SECONDS`) have
    passed on `ops.public_health.clock`, which is `time.monotonic` and which the tests move.
  - `ops.api.health` answers from one `HeldAnswer` per process (`ops.api.public_health`). The route, its response and its
    docstring ("Always 200 while this process is alive") are unchanged.
  - Tests (`ops/tests/test_health.py`, `TestThePublicAnswerIsHeldFiveSeconds`), with a counting fake of the solver and a
    moved clock, no sleeping:
    - after the first answer, the solver goes down and the clock moves 4.9 s. The second answer is still `ok`, with no
      database query (`django_assert_num_queries(0)`) and still one solver call;
    - at 5.1 s it is `degraded`, after a second solver call;
    - a `degraded` answer is held too, and turns `ok` after five seconds.
  - Each test starts with nothing held: an autouse fixture in `backend/conftest.py` (`no_public_health_answer_held`).
- **`/api/ops/health` and `/metrics` are not held.** They still call `ops.status` directly. One test each makes two requests
  around a solver going down, with the clock not moved, and sees both answers and two solver calls.
- **The compose health check still turns healthy at start; with the database gone, the public answer says so within five
  seconds of its held copy running out.** The health check is unchanged: it needs a 200, and the route always gives one.
  Driven on a real stack (below).
- **Architecture section 8's Observability** says the public answer is held five seconds in each web process, and that the
  health page and `/metrics` ask afresh.
- **The audit record:** a line under "What the user decided for the leads" marks `REPORT.md` section 5's health note fixed,
  with `7e5f7ed` and `77f79f4`. `REPORT.md` is the audit's own report, kept as written, so it is not edited.
- **Beside the criteria:** `deploy/INSTALL.md`'s first check says the answer may take five seconds to change after a
  service stops or comes back, and that the health page is always current.

**What was driven, and how.** I used my own scratch stack, `e2e/stack.sh up nr-t68 --empty` (ports 18680 and 18681), on 11
November 2026, with a scratch Python client polling web's `/api/health` on 18680 every 0.1 s and printing each change.
- **At start:** web turned `healthy` under compose's own check, and `/api/health` through Caddy was `ok`.
- **A client polling:** 132 requests in 15 seconds made 9 calls to the solver's `/health`, counted in the solver's access log,
  three every five seconds: one for each of the three web processes. Without the hold that would have been 132.
- **The database stopped** (`docker stop nr-t68-db-1`) about 3.5 s into a 25-second poll:
  - the first `degraded`, with `database: false`, came at 5.9 s;
  - one more `ok` came at 6.7 s, from a process whose held copy had not run out yet;
  - from 6.9 s to the end every answer was `degraded`. That is within five seconds of the stop for every process;
  - web stayed `healthy` throughout, as before this ticket: the check reads the status, not the body.
- **The database started again:** for about five seconds the answers alternated between `ok` and `degraded` as each
  process's held copy ran out. After 5.0 s every answer was `ok`, through Caddy too.

The stack is down, its volumes and `e2e/.stack/nr-t68.*` are gone, and my PostgreSQL container is removed.

**What was found, and fixed:** nothing beyond the review's points (below).

**What was NOT checked.**
- Threads. Gunicorn is still sync workers until ticket 71, so no run had two threads in one process. The lock is read, not
  driven, and no backend test starts threads: the agreed seam is the API suite's clock.
- A database that hangs rather than refuses. The drive stopped the container, so connections were refused at once. A hang
  would hold every health answer of that process for as long as the connect takes (see Worth your review).
- The frontend's suites locally: GitHub's, since nothing of the frontend changed.

**Decisions taken here.**
- **Held in each process's memory**, as the brief says: there is no shared cache service in the stack. Each of the three
  processes holds its own copy, so for up to five seconds after a change, two requests can get different answers.
- **The five seconds start when the answer has been worked out,** not when it was asked for. So a slow solver call does not
  eat into the hold.
- **One lock, held while the answer is worked out.** When the hold runs out under a burst, one thread calls the solver and
  the database, and the others wait for its answer instead of each calling. That is what keeps one process at one solver
  call per five seconds once ticket 71 makes it threaded.
- **A `degraded` answer is held as well as an `ok` one.** Holding only `ok` would let a client poll the solver on every
  request exactly while it is down, which is when that hurts most.
- **The clock is a module-level name** (`ops.public_health.clock`) that the tests replace, so `time.monotonic` itself is not
  patched under httpx and Django.

**Worth your review.**
- **A recovery shows up to five seconds late,** and an outage too. A script that stops a service and reads `/api/health`
  at once still sees the old answer. `INSTALL.md` now says so. The health page is always current.
- **Waiting threads wait for the one that works the answer out.** The solver's timeout is 2 s for each step of the call
  (connecting, reading), and the database's `SELECT 1` has no timeout of its own. Under ticket 71's threads, a database that
  hangs rather than refuses would hold all four threads' health answers for as long as it hangs. The other routes would
  hang on the same database anyway. A `connect_timeout` for web's connection would bound it, but that is outside this ticket.
- **The answer is held in each process, not shared.** Three processes make up to three solver calls per five seconds, not
  one.

**Review:** `code-review` against `5230b55`, two axes in fresh subagents.
- **Standards:** no hard violations, and the lock was found correct.
  - Fixed (`77f79f4`):
    - the class was `Kept`, which is a glossary word (a preference the roster gives the nurse). It is now `HeldAnswer`,
      and the code says "held" throughout. The ticket's and the docs' prose keeps "kept", the spec's word;
    - it was generic over its answer and took a `seconds` argument nobody passed. Both are gone;
    - the docstring said waiting threads wait "at most the solver's 2-second timeout". It now says what they may wait for
      (Worth your review).
  - Kept:
    - the new counting `Solver` fake beside the file's two older fixtures, which the two existing tests still use
      unchanged;
    - the moved clock as the tests' handle on time, which the brief agreed as the seam.
- **Spec:** every criterion met.
  - Noted: the database half of the third criterion has no backend test, only the drive above. A test would need to take
    the test database away from Django.
  - Noted: the `INSTALL.md` sentence is beyond the ticket. It was kept because the install check reads this answer.
  - Fixed: the audit line now names the review commit too.

**Things later tickets should know.**
- **Ticket 71 (threaded gunicorn):** `ops.public_health.HeldAnswer` is the module-level mutable state the spec asks that
  ticket to confirm. It is guarded by one `threading.Lock`, held while the answer is worked out, so threads in one process
  share one answer and make one call between them. Waiting threads queue on that lock (Worth your review). A process
  forked from a preloading master would start with an unheld lock and nothing held. Gunicorn does not preload here today.
- A test that reads `/api/health` twice and expects the second answer to differ must move `ops.public_health.clock` past
  five seconds. Every test starts with nothing held.

**From the main session (2026-11-11):** PR 7 merged into `main` as `4f198f6` by the ticket session, both workflows green on
that head. Dev stack rebuilt (`up -d --build`); `/api/health` answers ok.

**Reviewed by the user (2026-11-11):** all four points kept as built.
- A change in the database or the solver may show up to five seconds late in the public answer.
- When the held answer runs out, the other threads of the process wait for the one call; a hanging database holds them.
- Each web process holds its own copy: up to three solver calls every five seconds.
- The sentence added to `deploy/INSTALL.md` stays.
