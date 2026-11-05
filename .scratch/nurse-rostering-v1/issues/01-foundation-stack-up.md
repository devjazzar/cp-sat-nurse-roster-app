# 01: Foundation: the stack comes up and the solver is reachable

**What to build:** A hospital's IT runs one `docker compose up` and gets the whole stack: Caddy in front, the web application, the worker, the isolated solver and PostgreSQL. The solver answers over the internal network only, with the shared token, and its full HTTP contract (solve, poll, cancel, validate, precheck, health) is proven by tests against the real solver on the four-nurse sample. The repository is initialised, the solver package is vendored from its original project with its own suite green, the backend and frontend skeletons exist, and CI runs every suite and builds the single image.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [x] Git repository initialised on `main` with a `.gitignore`; no remote required
- [x] The solver package, its tests and fixture are copied in (not a submodule) and its pytest suite passes unchanged on Python 3.14 with OR-Tools 9.15
- [x] The solver HTTP service exposes solve (job id, 409 while a job runs), job status (state, elapsed, best cost, improvements, best grid so far, full result when done), cancel (keeps the best found), validate, precheck and health; every call requires the shared token; worker threads default to the CPU count
- [x] Contract tests over HTTP against the real service on the four-nurse sample cover start, poll to completion, cancel, validate, precheck, token rejection and the 409
- [x] Django 6.1 + Django Ninja skeleton with settings from environment, a health endpoint, Procrastinate installed and a worker command that starts; pytest-django wired with one passing test
- [x] Vite 8 + React 19 + TypeScript + Tailwind 4 + shadcn/ui on Base UI skeleton with one page and one passing Vitest test; orval generates the client from the OpenAPI document
- [x] One multi-stage Dockerfile builds one image; compose defines caddy, web, worker, solver, db with the agreed networks and volumes; a dev compose file gives hot reload; `.env.example` lists every variable
- [ ] Caddy serves automatic HTTPS with a domain and a self-signed certificate without one
- [x] From a clean checkout, `docker compose up -d` brings all five services up; health answers through Caddy and reports the solver reachable; the solver is not reachable from the host
- [ ] A CI workflow runs the solver, backend and frontend suites and builds the image
- [x] The root README says how to run the tests and the stack

## Comments

Implemented on 2026-11-05. Two criteria stay unticked because they cannot be proven from this machine:

- **Caddy with a domain:** the self-signed path is verified end to end. With `DOMAIN` set, Caddy places a real order with Let's Encrypt, which refused the test name `nurses.example.com`. No certificate has actually been issued; that needs a real domain whose DNS points at a server.
- **CI:** the workflow passes actionlint and its commands were run locally, but the repository has no remote, so it has never run on GitHub.

Things a later ticket should know:

- **Change to the vendored package:** `test_deeply_nested_json_is_an_input_error` failed on Python 3.14, whose JSON parser no longer overflows on deep nesting. The test is unchanged. `parse_json` in `nurse_roster/problem.py` now measures the depth itself, and the service uses it too.
- **"Clean checkout" means with a filled-in `.env`:** compose refuses to start without the four required secrets, on purpose.
- **Job states:** `running`, `finished`, `cancelled`, `failed`. `finished` means the search ended and a result exists; the result's `ok` says whether it holds a usable roster (an infeasible month is `finished` with `ok: false`). The worker maps these to the Solve states.
- **`/validate` body:** `{"solve_input", "roster"}`, with the roster in the shape of a result's `roster`.
- **Cancel and 409 tests:** the exact four-nurse sample proves optimal in about 0.6 s, too fast to catch running, so those tests use the same four nurses with looser headcounts and the soft rules on. Ticket 11's cancellation test will need the same (`long_search` in `solver/service_tests/conftest.py`).
- **Not built here:** `INITIAL_ADMIN_PASSWORD` is required by compose but nothing reads it until ticket 02. TanStack Router and the rest of the ADR 0008 toolkit arrive with the tickets that need them.
- **Open risk:** without a `DOMAIN`, on-demand certificates are issued for any name a client sends, so a client sending many names adds files to `caddy_data`. This is low risk on a hospital network, but worth revisiting for a server exposed to the internet with no domain.

**Reviewed by the user (2026-11-05).** The user chose to stay with no GitHub remote for now, so CI remains unproven on GitHub and its criterion stays unticked. The on-demand certificate risk stands, and the README's install notes now warn of it. Proving Let's Encrypt moved to the first real install (ticket 22).
