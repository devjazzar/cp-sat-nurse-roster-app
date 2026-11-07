# Developing a feature locally, with agents

How a feature goes from an idea to `main` in this repository, the way tickets 01–25 went: you decide, agents build, and
nothing reaches `main` that has not passed every suite on a clean copy. It is written for you at the keyboard of the
Claude desktop app's Code tab, with Matt Pocock's engineering skills and the Codex plugin installed. Every command runs from
the repository root unless it says otherwise.

What is law: [docs/ARCHITECTURE.md](../ARCHITECTURE.md) (the agreed design), [GLOSSARY.md](../../GLOSSARY.md) (the words)
and [docs/adr/](../adr/) (the reasons). Where a ticket, a spec or this guide disagrees with them, they win. The agents are
told so in [CLAUDE.md](../../CLAUDE.md) and [docs/agents/](../agents/); you are told so here.

## 1. What you need once

- **Docker Desktop**, with Compose v2.24 or later, running (`open -a Docker` starts it).
- **uv 0.13 and Python 3.14, Node 26**: the versions pinned in the README. `uv sync --all-packages --python 3.14` once
  from the root installs every Python package; `cd frontend && npm ci` and `cd e2e && npm ci && npx playwright install
  chromium` install the two Node trees.
- **The `gh` CLI**, signed in to the GitHub account that owns the repository (`gh auth status`): the ticket sessions open
  pull requests with it and the main session reads their checks.
- **The Claude desktop app** (Code tab), with:
  - the engineering skills in `~/.claude/skills/`: `grill-with-docs`, `to-spec`, `to-tickets`, `implement`,
    `implement-spec`, `code-review`, `tdd`, and the rest `setup-matt-pocock-skills` set up. `docs/agents/` holds what that
    setup wrote for this repo: the tracker is markdown under `.scratch/`, the labels are the five defaults.
  - the **Codex plugin** (`/codex:adversarial-review`, `/codex:review`, `/codex:rescue`), signed in.
  - the design-review skills `better-interface`, `better-writing`, `better-accessibility` and the others in
    `skills-lock.json`, which a ticket session holds its screens against by hand.
- **`deploy/.env`**, from `deploy/.env.example`, with the four required values filled. It is git-ignored and yours; ticket
  sessions may read `INITIAL_ADMIN_PASSWORD` from it, nothing else.

## 2. The dev stack, and what it is for

Your development stack is compose project `nurse-roster`, from `deploy/compose.yaml` with the dev overlay:

```bash
cd deploy && docker compose -f compose.yaml -f compose.dev.yaml up -d --build
```

Open <http://localhost:5173> (Vite, hot reload, `/api` passed on to Django) or <http://127.0.0.1:8000> (Django serving
the API). PostgreSQL is on `127.0.0.1:5432` (`DEV_POSTGRES_PORT` in `.env` moves it), which is what the backend's test suite
expects when you run it by hand. Caddy is left out.

**The stack holds your data and your sessions.** It is where you do your own manual pass after a ticket lands. Ticket
sessions never touch it: no restart, no migration, no login, no data, no backup or restore against it. They build and test
on scratch compose projects of their own, and the main session (section 4.8) refreshes `nurse-roster` after a merge.

What a change needs, because the dev overlay mounts only `backend/` and the solver's two packages into the containers:

| What changed | What the stack needs |
|---|---|
| `backend/` Python | nothing: `web` and `solver` reload themselves. `worker` does not: `docker compose -f compose.yaml -f compose.dev.yaml restart worker` |
| a migration | `restart web worker` (`web` migrates as it starts) |
| `frontend/` | nothing: Vite serves it |
| `deploy/compose.yaml`, `compose.dev.yaml`, the `Dockerfile`, a dependency in `pyproject.toml` or `uv.lock`, `solver/` packaging | a rebuild: `docker compose -f compose.yaml -f compose.dev.yaml up -d --build --no-deps web worker solver` |
| `db`'s options in `compose.yaml` | `up -d db` (recreates the container; the data is in the volume) |

A ticket session's final report says which of these its branch needs; believe the diff, not the report (ticket 21's session
said "restart" when the close imported solver code baked into the image).

## 3. The pieces a feature leaves behind

| Where | What |
|---|---|
| `.scratch/<release>/specs/<feature>.md` | The spec `/to-spec` writes: problem, solution, user stories, implementation and testing decisions, out of scope. `Status: ready-for-agent` at the top |
| `.scratch/<release>/issues/NN-<slug>.md` | One ticket a file, numbered on from the last ticket in the repo, with `**Blocked by:**`, `**Status:**` and the checklist of criteria. Everything that happens to a ticket is appended under `## Comments`: notes from other tickets, the session's write-up, your review |
| `.scratch/<release>/spec.md` | The release's index: each feature, its spec, its tickets, the order to build in |
| `GLOSSARY.md`, `docs/adr/NNNN-*.md` | What `/grill-with-docs` adds as terms and decisions settle |
| `docs/ARCHITECTURE.md` | Updated by the ticket whose work moved the design |
| commits on `main` | The ticket's commits, fast-forwarded, then one commit recording your review |

`.scratch/nurse-rostering-v1/` is v1: its spec and tickets 01–25. `.scratch/nurse-rostering-v2/` is v2: seven features,
each with a spec under `specs/`, tickets 26–46 under `issues/`, and `spec.md` as the index. A new feature joins the current
release: its spec under `specs/`, its tickets numbered on from the last. (The grilling sessions wrote to `.scratch/<feature>/`
on their branches, and the main session moved and renumbered them at the merge; tell a `/to-spec` session the release's
paths and the next free number, and it writes there directly.)

## 4. The workflow, step by step

The shape: **grill → spec → tickets → one session per ticket in its own worktree → verify on a clean copy → fast-forward
`main` → your review recorded**. Each step is one skill or one habit.

### 4.1 Grill the idea: `/grill-with-docs`

In your main session, with the idea in one paragraph:

```
/grill-with-docs <the idea, or a finding to act on>
```

It runs `grilling` and `domain-modeling` together: rounds of numbered questions, each with a recommended answer, worded so
"yes" accepts the recommendation. Answer by number ("1 yes, 2 the other one, 3–5 yes"); "all yes" is a valid answer. The
agent looks up facts itself (what the code does today, what an ADR says); only decisions come to you. As terms and decisions
settle, it writes glossary entries and ADRs, and asks before changing an agreed decision.

It ends when the frontier is empty: every branch of the design visited, nothing assumed. Ticket 25 came out of one such
grilling of ticket 24's two findings, eight questions in two rounds.

### 4.2 Write the spec: `/to-spec`

```
/to-spec <feature name>
```

No interview: it synthesises the grilling. It first **proposes the test seams** and waits for your yes: the public
boundaries the feature will be tested at, existing ones preferred, the fewer the better (ticket 25: the API's `Me`, the
frontend's app-level Vitest suite, and ticket 24's Playwright checks). Then it writes the spec under the release's `specs/`,
marked `ready-for-agent`, and commits it.

Read the user stories: a story you did not ask for is a decision the agent took for you. Keep it or strike it now; after
this, the spec is law for the sessions.

### 4.3 Cut the tickets: `/to-tickets`

```
/to-tickets .scratch/<release>/specs/<feature>.md
```

Vertical slices, each a complete path through schema, API, UI and tests, each demoable alone, each sized for one fresh
context window, with `**Blocked by:**` edges. It shows you the breakdown and asks about granularity and edges; iterate until
you approve, then it writes the files and commits. A feature of one slice is still a ticket: ticket 25 was written straight
from its grilling, with the spec linked from its comment.

### 4.4 Start a ticket session: `/implement`

One ticket at a time, each in a session of its own, in its own worktree, cut from `main`:

```
/implement Ticket NN in a new session with remote control active. Use Fable as advisor if needed.
```

The main session (the one you are in) starts the ticket session with a **brief** (appendix A) and turns Remote Control on,
so you can follow it from the phone. Send that request from the desktop app, not over Remote Control: the app refuses to
start a session from a turn that came in remotely.

Two things the brief always carries, because they went wrong once each:

- **The ticket session never touches `main` or the dev stack.** It commits on its branch, pushes it to `origin` and opens a
  draft pull request, which is where CI runs (section 4.6); it rebases on `main` if `main` moved, and reports its pull
  request and head. The main session does the merge.
- **It must say plainly what the dev stack needs** (section 2's table) and what it did **not** verify.

When the ticket is the whole spec, or the spec's tickets are many and small, `/implement-spec` is the alternative: one
session runs every ticket through fresh subagents, each in a worktree, merging onto one integration branch, with one
`code-review` at the end. Use it when you do not want to review each ticket; use `/implement` when you do. Tickets 01–25 all
went through `/implement`, one session each.

### 4.5 Inside the ticket session

What the brief asks the session to do, so you know what to expect in its report:

1. **State the ticket's title**, read the ticket and every comment, the spec, the architecture, glossary and ADRs, and the
   previous ticket's comment, which is the latest model of a write-up.
2. **`tdd` at the agreed seams**: red → green, one slice at a time, tests through public interfaces only. Typecheck and single
   test files as it goes.
3. **The full suites once at the end**, locally: backend `pytest` on a throwaway PostgreSQL 18 container of its own; the
   solver's `pytest` if it touched `solver/`; frontend `npm test` and `npm run build`. `makemigrations --check` clean. If the
   API changed, `frontend/openapi.json` and the generated client regenerated and matching the export (section 5.4). The
   browser checks it runs locally are the single Playwright files it changed, on its scratch stack; **the whole of
   `e2e/ci.sh`, and the six parallel frontend runs, run on GitHub** (section 4.6), not on your machine.
4. **`/code-review` against the base commit** it was cut from: two axes, standards and spec, in parallel subagents. It fixes
   what they find or says why not.
5. **`/codex:adversarial-review --base <base commit>`**: a second model challenging the approach, the assumptions and the
   design, not just the defects. Review-only: the session reads Codex's verdict, fixes what it accepts, and says in the
   ticket comment what it kept and why.
6. **Drive the real thing** on a scratch compose project of its own (`e2e/stack.sh up nr-tNN`, or `deploy/tests/operations.sh
   nr-tNN` for the operations scripts): every criterion that a browser or a container can show, in the built-in browser or
   through Playwright. Remove only what it created (`stack.sh down`).
7. **Hold the screens** against `better-interface`, `better-writing` and `better-accessibility` by hand.
8. **The ticket comment** (appendix B): what was built, what was driven and how, what was NOT checked, the decisions it took,
   **Worth your review**, and what later tickets should know. It ticks only the criteria it actually met.
9. **Commit, and report**: branch, head, whether the suites pass, what the dev stack needs, in the first 400 characters.

If something only you can answer blocks it, it sends one short question to the main session and stops. Answer it there.

### 4.6 Verify: CI on GitHub, on the pull request

The session's report is a report, not proof. The proof is GitHub Actions on the pull request's head, a clean checkout on a
machine that is not yours: two workflows, both on every pull request and on `main`.

| Workflow | Jobs | What it proves | Time |
|---|---|---|---|
| **CI** (`.github/workflows/ci.yml`) | `solver`, `backend`, `frontend`, `image` | the solver's suite; the backend's on a PostgreSQL 18 service with `makemigrations --check`; the frontend's OpenAPI document and generated client matching the backend's export, the typecheck and build, the suite once and then **six times at once**; the image builds | about 10 min, in parallel |
| **Browser checks** (`.github/workflows/browser-checks.yml`) | `browser-checks` | `e2e/ci.sh`: the image, a seeded stack and an empty one, every Playwright project, `deploy/tests/operations.sh`, everything removed | about 15 min |

In the main session, once the ticket session reports:

```bash
gh pr checks <number> --watch
```

Both workflows green on the head the session reported is the verification. A new push to the branch cancels the run still
going and starts another, so a report whose head moved since is checked again. `gh run view <id> --log-failed` reads a red
job's log; the browser checks upload Playwright's traces of what failed as an artifact.

Then **read the diff against the ticket and the spec** yourself (`gh pr diff <number>`, or `git diff main...refs/heads/
<branch> -- <the files that matter>` after `git fetch`): the API change, the guard, the wording. The reviews ran in the
session; this is the one pair of eyes outside it.

When something fails, send the session **one** message naming the job, the test, the exact failure and what else passed,
and tell it to commit the fix on its branch, push, and report the new head once the checks are green. Ticket 24's parallel
failure was a real ordering bug in the grid, found only by six runs sharing a machine, and fixed in the component, not the
test; that is what the six-runs step is for.

**When GitHub is not an option** (down, or the minutes are spent), the local scripts do the same on a `git archive` of the
head, never on the worktree or the checkout: `scripts/verify-backend.sh <head> /tmp/verify-tNN 55461`,
`scripts/verify-frontend.sh /tmp/verify-tNN`, then `cd /tmp/verify-tNN && E2E_CI_PREFIX=nr-verify-tNN e2e/ci.sh`. About
12, 3 and 12 minutes, in the background, in that order; afterwards `docker ps -a | grep nr-verify-tNN` and `docker volume ls
| grep nr-verify-tNN` print nothing.

### 4.7 Fast-forward `main`, and push it

```bash
git fetch origin && git merge --ff-only refs/remotes/origin/<branch>
```

```bash
git push origin main
```

Always the full ref: a tag of the same name would win over a bare branch name. `--ff-only` refuses if `main` moved; then the
session rebases and pushes, you verify again. Never merge with a merge commit. Pushing `main` with the pull request's head on
it marks the pull request **merged** on GitHub by itself (no button pressed), deletes its branch there (the repository is set
to), and runs both workflows once more on `main`.

### 4.8 Refresh the dev stack

Section 2's table, by the diff. Then `curl -s http://127.0.0.1:8000/api/health` answers `{"status": "ok", ...}`, and your
own manual pass of what the ticket built happens here, on your data, in your browser.

### 4.9 Bring the review points to yourself, and record the answers

Everything the ticket comment marks **Worth your review** comes to you as a numbered list, each with a one-line
recommendation (keep, change, follow-up ticket). Answer by number; "keep all" is an answer. Then the main session:

- appends to the ticket: `**Reviewed by the user (YYYY-MM-DD):** all N points marked **Worth your review** are kept as built:
  <each in a few words>` (or what changed, and which point became a ticket);
- commits that on `main`: `Record the user's review of ticket NN: all points kept`.

A point you want changed is a small follow-up the main session does itself, or a new ticket when it is work of its own.
A finding the session left for you ("not fixed, beyond small and clearly a bug") goes back to 4.1: grill it, then ticket it.

### 4.10 Clean up

When a ticket's branch is on `main` and its review is recorded, the worktree and the branch have nothing left to say:

```bash
git worktree list && git branch
```

```bash
git worktree remove --force .claude/worktrees/<name> && git branch -d claude/<branch>
```

`branch -d` (not `-D`) refuses a branch that is not on `main`, which is the check you want. Do this in batches, once a few
tickets are in; the ticket sessions stay in the sidebar and can be archived.

## 5. Tests: where they live and the rules they follow

### 5.1 The suites

| Suite | Runs where | What it needs | Time |
|---|---|---|---|
| **backend** `cd backend && uv run --no-sync pytest -q` | real PostgreSQL 18, real queue, the solver scripted or real in-process | `POSTGRES_HOST/PORT/PASSWORD` pointing at a database (the dev stack's by default) | 8 min |
| **solver** `cd solver && uv run --no-sync pytest -q` | the vendored suite, and contract tests against the real service over HTTP | nothing | 2–3 min |
| **frontend** `cd frontend && npm test` | Vitest over the real routes and the generated client, `fetch` stubbed per test | `npm ci` | 1 min; 2 min for six at once |
| **operations** `deploy/tests/operations.sh <project>` | a production-composed stack of its own: health, `/metrics`, JSON logs, the clock off, backup, retention, restore, the password reset | Docker | 5 min |
| **browser** `e2e/` (Playwright) | a seeded stack and an empty one, built from the checkout, their own ports | Docker, `npx playwright install chromium` | 7 min for all 68 |
| **everything the browser-checks workflow runs** `e2e/ci.sh` | the image, both stacks, every Playwright project, then `operations.sh`, everything removed | fixed ports 18180–18183 and 18543–18545; on GitHub for every pull request, locally only when GitHub is not an option | 11–12 min here, about 15 on GitHub |

A ticket session runs the backend suite on a throwaway container (`docker run -d --rm -p 127.0.0.1:<port>:5432 -e
POSTGRES_USER=nurse_roster -e POSTGRES_DB=nurse_roster -e POSTGRES_PASSWORD=<x> postgres:18`, then `POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=<port>`), never on the dev stack's database.

### 5.2 Rules the suites follow

These are the rules the sessions are briefed with; they come from what failed. The full statements are in the ticket
comments named.

- **Seams first.** No test at a seam the spec did not agree. A test reads like a specification of behaviour through a public
  interface; it survives a refactor. Expected values come from an independent source (a worked example, the spec, the
  solver's own fixture), never recomputed the way the code computes them.
- **Frontend tests, from ticket 11's comment ("from ticket 10b"):** add to `frontend/src/app.test.tsx` through `start` and
  `hold`; no raised timeout to wait for a change, let a handler's answer change and `findBy` see it; no `vi.useFakeTimers()`
  with `start`; before acting on a page you have just gone to, wait for something on it, not for the address; no wait that
  proves something did *not* happen.
- **Six parallel runs must pass.** A test that passes alone and fails under load has found an ordering bug or a
  timing assumption. Fix the cause (ticket 24: the component), or the assertion's wait, never by a longer timeout.
- **Backend tests wait on nothing that ticks.** A stop is asked for once the row shows a roster; the queue's order is forced
  on real connections, not raced.
- **Playwright checks drive the real stack**: real solver, real worker, the hourly jobs fired now by `stack.sh fire`, the
  date moved by `stack.sh clock`. Races are ordered, not raced (the loser's page is loaded, the winner acts and is awaited,
  then the loser acts). Nothing in a check reads a password from anywhere but the stack's own env file or a dialog that showed
  it once.
- **Scratch projects only.** `stack.sh` and `operations.sh` refuse the installation's project name. Never `down -v` on a
  project you did not create. Every scratch project has its own ports; two seeded stacks need two `E2E_PORT`s and two
  `E2E_HTTPS_PORT`s.

### 5.3 Migrations

`cd backend && uv run --no-sync python manage.py makemigrations --check --dry-run` must say `No changes detected`. A ticket
that adds a model adds its migration; `web` runs them at start, on the dev stack and in production alike.

### 5.4 An API change

The frontend's client is generated from the backend's OpenAPI document, and both are committed. After any change to a
schema or an endpoint:

```bash
cd backend && SECRET_KEY=x POSTGRES_PASSWORD=x SOLVER_TOKEN=x uv run --no-sync python manage.py export_openapi_schema --api config.api.api --indent 2 --output ../frontend/openapi.json
```

```bash
cd frontend && npm run generate:api
```

`git diff -- frontend/openapi.json frontend/src/api/generated` is then what the API change is; `verify-backend.sh` and CI
fail if the committed document does not match the export.

## 6. What bit us, so it bites nobody twice

- **zsh modifiers in refs.** `$B:e2e/...` is zsh's `:e` modifier on `$B`, not a path; write `"${B}:e2e/..."`. A compose
  command line kept in a variable word-splits; keep it in a shell function.
- **"Restart" when it needed a rebuild.** Section 2's table. The image bakes in the solver package, the `Dockerfile` and the
  compose commands.
- **A background command without a notification.** In a session, `run_in_background` on the Bash call, not `nohup … &`:
  the former wakes the session when it ends, the latter never does.
- **`start_session` refused over Remote Control.** Send the `/implement` request from the desktop app.
- **A session's effort applies from its next turn.** `set_session_effort` on a running session changes nothing until it
  starts a turn; check with `get_session`.
- **Trailing greps.** A verification line that ends in `grep -c <leftovers>` exits 1 when there are none; read the lines
  above the exit code before calling a run failed.
- **The ticket session's own suite passed and the clean copy's did not.** The worktree had state the archive does not: a
  stale `node_modules`, a `.stack/` file, a test depending on another's leftovers. The clean copy is the truth.
- **Test secrets.** No session searches notes, transcripts or other files for a password. The journeys make their own
  secrets and keep them in a git-ignored `e2e/.stack/<project>.journey.json`, mode 0600.

## Appendix A: the brief a ticket session gets

The main session writes it; this is what it must contain. `<base>` is `main`'s head the worktree is cut from.

```
Use the `implement` skill on ticket NN, `.scratch/<release>/issues/NN-<slug>.md`, and state its title first.

## Where to work
- You are in your own git worktree on your own branch, cut from `main` at `<base>`. Commit there.
- Do not commit to `main` or merge into it. Push your branch to `origin` after your first commit and open a **draft pull
  request** against `main` (`gh pr create --draft --fill`); keep pushing as you go. GitHub Actions runs on it: the three
  suites, the image, six frontend runs at once, and the browser checks (`e2e/ci.sh`). Do not run `e2e/ci.sh` on this
  machine; run the Playwright files you changed on your scratch stack.
- If `main` moves, rebase on it and push before your final report so your branch can be fast-forwarded.
- Before your final report: `gh pr checks --watch` until both workflows are green on your head, then mark the pull request
  ready (`gh pr ready`). The session that started you checks the diff and brings your branch into `main`.

## Second opinions
The user asked for Fable as advisor where one is needed: the `advisor` tool, or an Agent with `model: "fable"`.
Give it the code and the question, not your conclusion.

## What to read
1. The ticket and every comment. 2. The spec, `.scratch/<release>/specs/<feature>.md`: it is decided, build it as written.
3. `docs/ARCHITECTURE.md`, `GLOSSARY.md`, `docs/adr/`. 4. The previous ticket's comment, the latest model of a write-up.

## What the ticket asks, to answer one by one in your ticket comment
<the criteria, grouped, with the decisions already taken; mark what the spec leaves open as **Worth your review**>

## Test seams (agreed with the user)
<the seams from the spec, by name>

## How to work
- `tdd` at those seams. Typecheck and single test files regularly; the full suites once at the end, locally: backend
  `pytest` on a throwaway PostgreSQL 18 container of your own; the solver's if you touch `solver/`; frontend `npm test` and
  `npm run build`. `makemigrations --check` clean. If the API changes, regenerate `frontend/openapi.json` and the client and
  confirm they match the export. The whole browser suite and the six parallel frontend runs are GitHub's, on your pull request.
- Frontend tests follow ticket 11's comment: no raised timeouts, no fake timers with `start`, no wait that proves something
  did not happen. CI runs six `npm test` at once: a test that passes alone and fails there has found a real bug.
- When done: `code-review` against `<base>`, then `/codex:adversarial-review --base <base>`. Fix what they find or say why not.
- Hold the screens against `better-interface`, `better-writing`, `better-accessibility` by hand.
- Drive the real thing on your own scratch compose project. Remove only what you created.

## Ticket comment
The style of ticket NN-1's: what was driven and how; what was NOT checked; the decisions you took; **Worth your review**;
what later tickets should know. Tick only the criteria you met.

## Scope
Ticket NN only. Start nothing else. Where a later ticket owns something, leave a comment on it.

## Credentials and the stacks
- The dev stack, project `nurse-roster`, is the user's and holds their data. Do not touch it at all.
- You may read `INITIAL_ADMIN_PASSWORD` from `deploy/.env` in the main checkout. Do not search session notes, transcripts
  or other files for passwords.
- Never `down -v` on any project but your own scratch one.

## Final report
Lead with the pull request's number, the branch and the head. First 400 characters: what was delivered, whether the local
suites pass and both GitHub workflows are green on that head. Say plainly if you changed `deploy/compose.yaml`, the
`Dockerfile`, the solver or a dependency (the dev stack then needs a rebuild). Detail in the ticket comment. If something only
the user can answer blocks you, send ONE short question to the session that started you.
```

## Appendix B: the ticket comment

Appended under `## Comments`, in this order, each a bold lead-in. Ticket 24's is the fullest example.

1. **Implemented on <date>,** on branch `<branch>` (`<commits>`), from `main` at `<base>`: the suites and their counts, the
   Playwright runs, `makemigrations --check`, the OpenAPI match.
2. **What the dev stack needs:** restart, rebuild or nothing, by what changed.
3. **What was built,** criterion by criterion.
4. **What was driven, and how:** which stack, which browser, which role, what was seen.
5. **What was found, and fixed** (small and clearly a bug, with a test), and **Findings for you, not fixed.**
6. **What was NOT checked.**
7. **Decisions taken here,** and **Worth your review** for each the spec left open, with the reason.
8. **Review:** what `code-review`'s two axes and the adversarial review found, fixed, or kept and why.
9. **Things later tickets should know.**

## Appendix C: the main session's routine, in one place

For when a new main session has to pick the routine up:

1. Read the ticket session's full report (`list_events` on its session).
2. `gh pr checks <number> --watch`: both workflows green on the head it reported. Read the diff against the spec meanwhile
   (`gh pr diff <number>`).
3. Anything red: one message back to the session; check again on its new head.
4. `git fetch origin && git merge --ff-only refs/remotes/origin/<branch>`, then `git push origin main` (the pull request
   turns merged by itself); refresh the dev stack by section 2's table; `curl` the health answer.
5. The **Worth your review** points to the user, numbered, each with a recommendation.
6. Append `**Reviewed by the user (date):** …` to the ticket; commit on `main` and push.
7. Every few tickets: remove the worktrees and local branches that are on `main` (GitHub deletes the pushed branch at the
   merge).
