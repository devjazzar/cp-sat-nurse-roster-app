# 01: Foundation: the stack comes up and the solver is reachable

**What to build:** A hospital's IT runs one `docker compose up` and gets the whole stack: Caddy in front, the web application, the worker, the isolated solver and PostgreSQL. The solver answers over the internal network only, with the shared token, and its full HTTP contract (solve, poll, cancel, validate, precheck, health) is proven by tests against the real solver on the four-nurse sample. The repository is initialised, the solver package is vendored from its original project with its own suite green, the backend and frontend skeletons exist, and CI runs every suite and builds the single image.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] Git repository initialised on `main` with a `.gitignore`; no remote required
- [ ] The solver package, its tests and fixture are copied in (not a submodule) and its pytest suite passes unchanged on Python 3.14 with OR-Tools 9.15
- [ ] The solver HTTP service exposes solve (job id, 409 while a job runs), job status (state, elapsed, best cost, improvements, best grid so far, full result when done), cancel (keeps the best found), validate, precheck and health; every call requires the shared token; worker threads default to the CPU count
- [ ] Contract tests over HTTP against the real service on the four-nurse sample cover start, poll to completion, cancel, validate, precheck, token rejection and the 409
- [ ] Django 6.1 + Django Ninja skeleton with settings from environment, a health endpoint, Procrastinate installed and a worker command that starts; pytest-django wired with one passing test
- [ ] Vite 8 + React 19 + TypeScript + Tailwind 4 + shadcn/ui on Base UI skeleton with one page and one passing Vitest test; orval generates the client from the OpenAPI document
- [ ] One multi-stage Dockerfile builds one image; compose defines caddy, web, worker, solver, db with the agreed networks and volumes; a dev compose file gives hot reload; `.env.example` lists every variable
- [ ] Caddy serves automatic HTTPS with a domain and a self-signed certificate without one
- [ ] From a clean checkout, `docker compose up -d` brings all five services up; health answers through Caddy and reports the solver reachable; the solver is not reachable from the host
- [ ] A CI workflow runs the solver, backend and frontend suites and builds the image
- [ ] The root README says how to run the tests and the stack
