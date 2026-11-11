# Developing a feature locally, with agents

How a feature goes from an idea to `main` in this repository, as it has gone since ticket 26: you decide, agents build, and
nothing reaches `main` that has not passed every suite on a clean copy. It is written for you at the keyboard of the
Claude desktop app's Code tab, with Matt Pocock's engineering skills installed. Every command runs from
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
  pull requests with it, wait on their checks and fast-forward `main`.
- **The Claude desktop app** (Code tab), with:
  - the engineering skills in `~/.claude/skills/`: `grill-with-docs`, `to-spec`, `to-tickets`, `implement`,
    `implement-spec`, `code-review`, `tdd`, and the rest `setup-matt-pocock-skills` set up. `docs/agents/` holds what that
    setup wrote for this repo: the tracker is markdown under `.scratch/`, the labels are the five defaults.
  - the design-review skills `better-interface`, `better-writing`, `better-accessibility` and the others in
    `skills-lock.json`, which a ticket session holds its screens against by hand.
- **`deploy/.env`**, from `deploy/.env.example`, with the four required values filled. It is git-ignored and yours; ticket
  sessions may read `INITIAL_ADMIN_PASSWORD` from it, nothing else.

## 2. The dev stack, and what it is for

Your development stack is compose project `nurse-roster`, the installation itself, from `deploy/compose.yaml` alone (since
2026-11-07; the hot-reload overlay `compose.dev.yaml` was removed on 2026-11-11):

```bash
cd deploy && docker compose up -d --build
```

Open <https://localhost> (Caddy's self-signed certificate, so the browser warns once). `web` runs gunicorn from the
`nurse-roster-app:dev` image built from the checkout; nothing is mounted from the source and no port but Caddy's 80 and 443 is
published, so there is no hot reload and no PostgreSQL on localhost.

**The stack holds your data and your sessions.** It is where you do your own manual pass after a ticket lands. Ticket
sessions never touch it: no restart, no migration, no login, no data, no backup or restore against it. They build and test
on scratch compose projects of their own, and the main session (section 4.8) refreshes `nurse-roster` after a merge.

**Whatever changed, the stack needs a rebuild**, because the image bakes in the backend, the solver, the built SPA and the
compose commands: `cd deploy && docker compose up -d --build`. It rebuilds the image from the checkout, recreates `web`,
`worker` and `solver`, keeps the volumes, and `web` runs any new migration as it starts. A `restart` serves the image's old
code (tickets 23 to 25 were "refreshed" that way and kept ticket 22's build). Then check:

```bash
curl -sk https://localhost/api/health
```

It answers `{"status": "ok", "database": true, "solver": {"reachable": true}}`; for a ticket with a migration,
`docker compose exec -T web python manage.py showmigrations <app>` shows it applied. A ticket session's report says what its
branch changed; believe the diff, not the report.

## 3. The pieces a feature leaves behind

| Where | What |
|---|---|
| `.scratch/<release>/specs/<feature>.md` | The spec `/to-spec` writes: problem, solution, user stories, implementation and testing decisions, out of scope. `Status: ready-for-agent` at the top |
| `.scratch/<release>/issues/NN-<slug>.md` | One ticket a file, numbered on from the last ticket in the repo, with `**Blocked by:**`, `**Status:**` and the checklist of criteria. Everything that happens to a ticket is appended under `## Comments`: notes from other tickets, the session's write-up, your review |
| `.scratch/<release>/spec.md` | The release's index: each feature, its spec, its tickets, the order to build in |
| `GLOSSARY.md`, `docs/adr/NNNN-*.md` | What `/grill-with-docs` adds as terms and decisions settle |
| `docs/ARCHITECTURE.md` | Updated by the ticket whose work moved the design |
| commits on `main` | The ticket's commits, fast-forwarded by the ticket session, then one `[skip ci]` commit recording your review |

`.scratch/nurse-rostering-v1/` is v1: its spec and tickets 01–25 (ticket 25's spec is in `.scratch/manager-own-pages-and-ended-sessions/`).
`.scratch/nurse-rostering-v2/` is v2: eleven features, each with a spec under `specs/`, tickets 26–61 under `issues/` (57 a
performance ticket from ticket 39's review, with no spec), and `spec.md` as the index. A new feature joins the current
release: its spec under `specs/`, its tickets numbered on from the last. (The grilling sessions wrote to `.scratch/<feature>/`
on their branches, and the main session moved and renumbered them at the merge; tell a `/to-spec` session the release's
paths and the next free number, and it writes there directly.)

## 4. The workflow, step by step

The shape: **grill → spec → tickets → one session per ticket in its own worktree → CI green on its pull request → it
fast-forwards `main` → the main session checks and refreshes → your review recorded**. Each step is one skill or one habit.

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

### 4.4 Start a ticket session: the brief, then the prompt you paste

One ticket at a time, each in a session of its own, in its own worktree, cut from `main`. In your main session:

```
/implement Ticket NN. Opus 5.5 at medium.
```

(or "start ticket NN"; name the model and effort you want, Opus 5.5 at medium so far). The start is two parts, because
`implement` and `implement-spec` are skills only you can invoke: a session cannot load them from a brief.

1. **The main session starts the ticket session**, nested under it: it fast-forwards its checkout to `origin/main`, then
   `start_session` with `use_worktree: true`, `source_branch: main`, the model and effort you named, and the **full brief**
   of appendix A. The brief tells the session to read everything it names, answer in three lines or fewer, and write no
   code until your command arrives.
2. **The main session gives you a paste-ready prompt** in a fenced block (and keeps a copy in its scratchpad):

   ```
   /implement-spec Ticket: NN, .scratch/<release>/issues/NN-<slug>.md. Spec: .scratch/<release>/specs/<feature>.md. Follow the brief you were started with. Use the advisor when needed.
   ```

   You paste it into the ticket session. From there the session works alone, merges its own pull request into `main`
   (section 4.7) and reports to the main session.

Send the start from the desktop app, not over Remote Control: the app refuses to start a session from a turn that came in
remotely. Remote Control may be turned on for the ticket session afterwards, so you can follow it from the phone.

Two things the brief always carries, because they went wrong once each:

- **The ticket session never touches the dev stack or the main checkout.** It commits on its branch, pushes it to `origin`
  and opens a draft pull request, which is where CI runs (section 4.6); it merges `origin/main` into its branch when `main`
  moves, never rebases and never force-pushes; and only once both workflows are green does it fast-forward `main` on
  `origin` to its head. The main session refreshes its checkout and the dev stack afterwards.
- **It must say plainly what it changed that the dev stack's rebuild picks up** (a migration, the compose file, the
  `Dockerfile`, a dependency) and what it did **not** verify.

### 4.5 Inside the ticket session

What the brief asks the session to do, so you know what to expect in its report:

1. **State the ticket's title**, read the ticket and every comment, the spec, the architecture, glossary and ADRs, and the
   previous ticket's comment, which is the latest model of a write-up.
2. **`tdd` at the agreed seams**: red → green, one slice at a time, tests through public interfaces only. Typecheck and single
   test files as it goes.
3. **The full suites once at the end**, locally, under the heavy-run lock: backend `pytest` on a throwaway PostgreSQL 18
   container of its own; the solver's `pytest` if it touched `solver/`; frontend `npm test` and `npm run build`.
   `makemigrations --check` clean. If the API changed, `frontend/openapi.json` and the generated client regenerated and
   matching the export (section 5.4). The browser checks it runs locally are the single Playwright files it changed, on its
   scratch stack; **the whole of `e2e/ci.sh`, and the six parallel frontend runs, run on GitHub** (section 4.6), not on your
   machine.
4. **`code-review` against the base commit** it was cut from: two axes, standards and spec, in parallel subagents. It fixes
   what they find or says why not. No Codex review (your call, 2026-11-09).
5. **Drive the real thing** on a scratch compose project of its own (`e2e/stack.sh up nr-tNN`, or `deploy/tests/operations.sh
   nr-tNN` for the operations scripts): every criterion that a browser or a container can show, in the built-in browser or
   through Playwright. Remove only what it created (`stack.sh down`).
6. **Hold the screens** against `better-interface`, `better-writing` and `better-accessibility` by hand.
7. **The ticket comment** (appendix B): what was built, what was driven and how, what was NOT checked, the decisions it took,
   **Worth your review**, and what later tickets should know. It ticks only the criteria it actually met.
8. **Commit and push; both workflows green** on the pull request's head (section 4.6).
9. **Merge into `main`** (section 4.7), delete its branch on `origin`.
10. **Report to the main session**: the pull request, the head that reached `main`, whether the suites passed, what the dev
    stack's rebuild picks up, and the **Worth your review** points, in the first 400 characters.

If something only you can answer blocks it, it sends one short question to the main session and stops. Answer it there.

### 4.6 Verify: CI on GitHub, on the pull request, before the merge

The session's own runs are not proof. The proof is GitHub Actions on the pull request's head, a clean checkout on a machine
that is not yours: two workflows, both on every pull request and on `main`.

| Workflow | Jobs | What it proves | Time |
|---|---|---|---|
| **CI** (`.github/workflows/ci.yml`) | `solver`, `backend`, `frontend`, `image` | the solver's suite; the backend's on a PostgreSQL 18 service with `makemigrations --check`; the frontend's OpenAPI document and generated client matching the backend's export, the typecheck and build, the suite once and then **six times at once** (one worker each); the image builds | about 6 min, the four jobs in parallel |
| **Browser checks** (`.github/workflows/browser-checks.yml`) | `browser-checks` | `e2e/ci.sh`: the image, a seeded stack and an empty one, every Playwright project, `deploy/tests/operations.sh`, everything removed | about 15 min |

Together they cost about 30 runner minutes a push; a private repository on GitHub's Free plan has 2,000 a month.

The ticket session waits with `gh pr checks <number> --watch`. Both workflows green on its head is the gate to the merge. A
new push to the branch cancels the run still going and starts another. `gh run view <id> --log-failed` reads a red job's
log; the browser checks upload Playwright's traces of what failed as an artifact. A red job is fixed on the branch, in the
code at fault: ticket 24's parallel failure was a real ordering bug in the grid, found only by six runs sharing a machine,
and fixed in the component, not the test; that is what the six-runs step is for.

**When GitHub is not an option** (down, or the minutes are spent), nothing is merged until it is, or until you say the
local scripts will do: they run the same on a `git archive` of the head, never on the worktree or the checkout:
`scripts/verify-backend.sh <head> /tmp/verify-tNN 55461`, `scripts/verify-frontend.sh /tmp/verify-tNN`, then
`cd /tmp/verify-tNN && E2E_CI_PREFIX=nr-verify-tNN e2e/ci.sh`. About 12, 3 and 12 minutes, in the background, in that order,
under the heavy-run lock; afterwards `docker ps -a | grep nr-verify-tNN` and `docker volume ls | grep nr-verify-tNN` print
nothing.

### 4.7 The merge: the ticket session fast-forwards `main`

From its worktree, once both workflows are green on its head:

```bash
git fetch origin && git merge-base --is-ancestor origin/main HEAD && git push origin HEAD:refs/heads/main
```

```bash
git push origin --delete <branch>
```

The push is a fast-forward or nothing: `origin` refuses it if `main` has moved since. Then the session merges `origin/main`
into its branch (never a rebase), pushes the branch, and waits for both workflows to be green on the new head before trying
again. One exception saves a run: when everything `main` gained since the green head is `[skip ci]` commits that touch only
markdown (a review recorded on a ticket, a doc), the merge of them needs no new run. Never a merge commit on `main` made by
GitHub's button, never a force-push. Pushing `main` with the pull request's head on it marks the pull request **merged** by
itself, draft or not, and runs both workflows once more on `main`.

### 4.8 The main session: check, refresh the dev stack

When the ticket session reports:

1. Read the full report (`list_events` on its session) and confirm the merge: `gh pr view <number> --json state` says
   `MERGED`, and `gh run list --branch main --limit 4` shows the run on `main` going or green.
2. **Read the diff against the ticket and the spec** yourself (`gh pr diff <number>`): the API change, the guard, the
   wording. The reviews ran in the session; this is the one pair of eyes outside it. A fault found now is fixed forward: one
   message to the ticket session, a new branch or commit through a pull request again, never a rewrite of `main`.
3. Bring the main checkout level: `git fetch origin && git merge --ff-only refs/remotes/origin/main` (the full ref: a tag of
   the same name would win over a bare branch name). The main checkout never holds a commit that is not pushed, so this
   always fast-forwards.
4. Refresh the dev stack (section 2): `cd deploy && docker compose up -d --build`, then `curl -sk
   https://localhost/api/health`, and `showmigrations <app>` for a ticket with a migration. Your own manual pass of what the
   ticket built happens here, on your data, in your browser.
5. Tell you the ticket is on `main`.

### 4.9 Bring the review points to yourself, and record the answers

Everything the ticket comment marks **Worth your review** comes to you as a numbered list, each with a one-line
recommendation (keep, change, follow-up ticket). Answer by number; "keep all" is an answer. Then the main session:

- appends to the ticket: `**Reviewed by the user (YYYY-MM-DD):** all N points marked **Worth your review** are kept as built:
  <each in a few words>` (or what changed, and which point became a ticket);
- commits that on `main` with `[skip ci]` and pushes at once: `Record the user's review of ticket NN: all points kept
  [skip ci]`.

A point you want changed is a small follow-up the main session does itself, or a new ticket when it is work of its own.
A finding the session left for you ("not fixed, beyond small and clearly a bug") goes back to 4.1: grill it, then ticket it.

### 4.10 Clean up

When a ticket's branch is on `main` and its review is recorded, the worktree and the local branch have nothing left to say:

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
| **backend** `cd backend && uv run --no-sync pytest -q` | real PostgreSQL 18, real queue, the solver scripted or real in-process | `POSTGRES_HOST/PORT/PASSWORD` pointing at a throwaway PostgreSQL 18 (never the dev stack's, which publishes no port) | 8 min |
| **solver** `cd solver && uv run --no-sync pytest -q` | the vendored suite, and contract tests against the real service over HTTP | nothing | 2–3 min |
| **frontend** `cd frontend && npm test` | Vitest over the real routes and the generated client, `fetch` stubbed per test | `npm ci` | 1 min; 2 min for six at once |
| **operations** `deploy/tests/operations.sh <project>` | a production-composed stack of its own: health, `/metrics`, JSON logs, the push key pair, the worker alone with a way out, the clock off, backup, retention, restore, the password reset, the push counts | Docker | 5 min |
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
- **"Restart" when it needed a rebuild.** Section 2: the dev stack serves the image, so every change needs
  `docker compose up -d --build`.
- **A background command without a notification.** In a session, `run_in_background` on the Bash call, not `nohup … &`:
  the former wakes the session when it ends, the latter never does.
- **`start_session` refused over Remote Control.** Send the `/implement` request from the desktop app.
- **A user-only skill in a brief.** A session started with a brief cannot load `implement` or `implement-spec`; a ticket 35
  session started that way was stopped. Hence the two-part start of section 4.4: the brief, then the prompt you paste.
- **A session's effort applies from its next turn.** `set_session_effort` on a running session changes nothing until it
  starts a turn; check with `get_session`.
- **Trailing greps.** A verification line that ends in `grep -c <leftovers>` exits 1 when there are none; read the lines
  above the exit code before calling a run failed.
- **The ticket session's own suite passed and the clean copy's did not.** The worktree had state the archive does not: a
  stale `node_modules`, a `.stack/` file, a test depending on another's leftovers. The clean copy is the truth.
- **Test secrets.** No session searches notes, transcripts or other files for a password. The journeys make their own
  secrets and keep them in a git-ignored `e2e/.stack/<project>.journey.json`, mode 0600.

## Appendix A: the brief a ticket session gets

The main session writes it and starts the session with it (section 4.4); this is what it must contain. `<base>` is
`main`'s head the worktree is cut from.

```
You are the ticket session for ticket NN, `.scratch/<release>/issues/NN-<slug>.md`: <its title>.

## First, now
Read everything under "What to read", then answer in three lines or fewer: the title, the blockers met, anything that
stops you. Write no code. The user will paste `/implement-spec Ticket: NN, ...`, a skill only they can invoke; when it
arrives, follow it with the house rules below. Where the skill and this brief disagree, this brief wins.

## Where to work
- You are in your own git worktree on your own branch, cut from `main` at `<base>`. This branch is the integration branch:
  commit here, one ticket only.
- Push your branch to `origin` after your first commit and open a **draft pull request** against `main` on
  `devjazzar/cp-sat-nurse-roster-app` (`gh pr create --draft --fill`); keep pushing as you go. GitHub Actions runs on it:
  the three suites, the image, six frontend runs at once, and the browser checks (`e2e/ci.sh`). Do not run `e2e/ci.sh` on
  this machine; run the Playwright files you changed on your scratch stack.
- If `main` moves, merge `origin/main` into your branch. Never rebase, never force-push.
- Never touch the main checkout (`<main checkout path>`) or its `main`.

## The merge, then the report
1. Commit the ticket comment, push, and `gh pr checks <number> --watch` until both workflows are green on your head.
2. `git fetch origin && git merge-base --is-ancestor origin/main HEAD && git push origin HEAD:refs/heads/main`: a
   fast-forward of `main` on `origin` to your green head. If it is refused, `main` moved: merge `origin/main` in, push, wait
   for green on the new head, and try again (no new run is needed when all `main` gained is `[skip ci]` markdown commits).
3. `git push origin --delete <branch>`. The pull request turns merged by itself.
4. Report (below). Do not refresh the dev stack; the main session does.

## Second opinions
The `advisor` tool where one is needed. Give it the code and the question, not your conclusion.

## What to read
1. The ticket and every comment. 2. The spec, `.scratch/<release>/specs/<feature>.md`: it is decided, build it as written.
3. `docs/ARCHITECTURE.md`, `GLOSSARY.md`, `docs/adr/`. 4. The previous ticket's comment, the latest model of a write-up.
5. `docs/guides/local-development.md`, appendices A and B.

## What the ticket asks, to answer one by one in your ticket comment
<the criteria, grouped, with the decisions already taken; what earlier tickets' comments and reviews left for this one;
mark what the spec leaves open as **Worth your review**>

## Test seams (agreed with the user)
<the seams from the spec, by name>

## How to work
- `tdd` at those seams. Typecheck and single test files regularly; the full suites once at the end, locally: backend
  `pytest` on a throwaway PostgreSQL 18 container of your own; the solver's if you touch `solver/`; frontend `npm test` and
  `npm run build`. `makemigrations --check` clean. If the API changes, regenerate `frontend/openapi.json` and the client and
  confirm they match the export. The whole browser suite and the six parallel frontend runs are GitHub's, on your pull request.
- Frontend tests follow ticket 11's comment: no raised timeouts, no fake timers with `start`, no wait that proves something
  did not happen. CI runs six `npm test` at once: a test that passes alone and fails there has found a real bug.
- When done: `code-review` against `<base>`. Fix what it finds or say why not. No Codex review.
- Hold the screens against `better-interface`, `better-writing`, `better-accessibility` by hand.
- Drive the real thing on your own scratch compose project (`e2e/stack.sh up nr-tNN`). Remove only what you created.
- One heavy local run at a time across all sessions (the user's rule, 2026-11-09): the full backend `pytest`, the full
  solver suite, the full frontend `npm test`, and bringing up or driving a scratch compose stack (Playwright included) need
  the lock; typechecks and single test files do not, and GitHub's checks are not limited. Take it in the background,
  `until mkdir "$HOME/.cache/nurse-roster-heavy.lock" 2>/dev/null; do sleep 30; done; echo "ticket-NN $(date)" > "$HOME/.cache/nurse-roster-heavy.lock/owner"`,
  and release it the moment that work ends, success or failure, with your stack down: `rm -rf "$HOME/.cache/nurse-roster-heavy.lock"`.
  Never hold it while waiting on GitHub, never remove another session's, and ask the session that started you about one
  older than two hours.

## Ticket comment
Appendix B, in the style of ticket NN-1's: what was driven and how; what was NOT checked; the decisions you took;
**Worth your review**; what later tickets should know. Tick only the criteria you met.

## Scope
Ticket NN only. Start nothing else. Where a later ticket owns something, leave a comment on it.

## Credentials and the stacks
- The dev stack, project `nurse-roster`, is the user's and holds their data. Do not touch it at all.
- You may read `INITIAL_ADMIN_PASSWORD` from `deploy/.env` in the main checkout. Do not search session notes, transcripts
  or other files for passwords.
- Never `down -v` on any project but your own scratch one.

## Final report
Lead with the pull request's number and the head that reached `main`. First 400 characters: what was delivered, that both
GitHub workflows were green on that head and it is on `main`, whether the local suites passed, what the dev stack's rebuild
picks up (a migration, `deploy/compose.yaml`, the `Dockerfile`, the solver, a dependency), and the **Worth your review**
points in a line each. Detail in the ticket comment. If something only the user can answer blocks you, send ONE short
question to the session that started you.
```

The prompt the user pastes into it, which the main session hands over in a fenced block:

```
/implement-spec Ticket: NN, .scratch/<release>/issues/NN-<slug>.md. Spec: .scratch/<release>/specs/<feature>.md. Follow the brief you were started with. Use the advisor when needed.
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

1. You say `/implement Ticket NN` (with a model and effort): `git fetch origin && git merge --ff-only
   refs/remotes/origin/main`, then `start_session` (`use_worktree: true`, `source_branch: main`, the model and effort, the
   brief of appendix A), then the paste-ready `/implement-spec` prompt to you in a fenced block.
2. The ticket session reports once its pull request is green and on `main`. Read the full report (`list_events`); confirm
   `gh pr view <number> --json state` is `MERGED` and the run on `main` (`gh run list --branch main --limit 4`); read the
   diff against the spec (`gh pr diff <number>`).
3. `git fetch origin && git merge --ff-only refs/remotes/origin/main` in the main checkout; `cd deploy && docker compose up -d
   --build`; `curl -sk https://localhost/api/health`.
4. Tell you the ticket is on `main`, and bring the **Worth your review** points, numbered, each with a recommendation.
5. Append `**Reviewed by the user (date):** …` to the ticket; commit on `main` with `[skip ci]` and push at once.
6. Every few tickets: remove the worktrees and local branches that are on `main`.
