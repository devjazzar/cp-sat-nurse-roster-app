# Nurse rostering

A hospital's monthly nurse rosters: unit managers generate them with a CP-SAT solver, the Deputy
CNO approves them, nurses see them, make requests and propose swaps. One installation serves one
hospital, as one `docker compose` stack on one server.

The agreed design is [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), the vocabulary is
[GLOSSARY.md](GLOSSARY.md), the reasons are in [docs/adr](docs/adr/) and the work is cut into
tickets under `.scratch/nurse-rostering-v1/issues/` (01–25, done) and `.scratch/nurse-rostering-v2/issues/` (26–61, the
eleven features of v2 and ticket 57; `.scratch/nurse-rostering-v2/spec.md` is their index and says which are built).

## Run the stack

The install guide for a hospital's server, with backups, restore, the System Admin's password reset, logs and metrics, is
[deploy/INSTALL.md](deploy/INSTALL.md). In short, you need Docker with Compose. From a checkout:

```bash
cd deploy
cp .env.example .env
```

Fill in the required values in `.env`, then:

```bash
docker compose up -d
```

The first start builds the image, which takes a few minutes. Five services come up: `caddy`,
`web`, `worker`, `solver` and `db`. Check them through Caddy:

```bash
curl -k https://localhost/api/health
```

The answer is `{"status": "ok", "database": true, "solver": {"reachable": true}}`. Without a `DOMAIN` the certificate is
self-signed, so a browser warns once. With a `DOMAIN` whose DNS points at the server, and ports 80
and 443 open to the internet, Caddy obtains a Let's Encrypt certificate by itself.

**On a server exposed to the internet, set a `DOMAIN`.** Without one, Caddy issues a certificate for
any name a client sends, and each one adds files to `caddy_data`.

The solver publishes no port and sits on an internal network only `web` and `worker` can reach.

Open `https://<server>/` and log in as `admin` with `INITIAL_ADMIN_PASSWORD` from `.env`. The first
start created that account; you must choose a new password at first login, and from then on the
variable is ignored.

## Develop

How a feature goes from an idea to `main` here, with the agent skills, the ticket sessions in worktrees and the checks on a
clean copy, is [docs/guides/local-development.md](docs/guides/local-development.md). The development stack is the
installation itself, run from the checkout exactly as above (`deploy/compose.yaml` alone, Caddy on 443, gunicorn), with no
hot reload. After a change reaches the checkout, rebuild it:

```bash
cd deploy && docker compose up -d --build
```

A `restart` serves the image's old code; when `deploy/Caddyfile` changed, also `docker compose restart caddy`. Then `curl -sk https://localhost/api/health` answers as above.

## Run the tests

The Python tools are pinned at uv 0.13 and Python 3.14, the frontend at Node 26.

```bash
uv sync --all-packages --python 3.14
```

**The solver**: the vendored suite and the service's contract tests, which start the real service
and speak to it over HTTP. Takes a few minutes.

```bash
cd solver && uv run --no-sync pytest -q
```

**The backend** needs a PostgreSQL 18 of its own, never the development stack's database (which
publishes no port). Start a throwaway one and point `POSTGRES_HOST`, `POSTGRES_PORT` and
`POSTGRES_PASSWORD` at it:

```bash
docker run -d --rm --name nr-test-db -p 127.0.0.1:55432:5432 -e POSTGRES_USER=nurse_roster -e POSTGRES_DB=nurse_roster -e POSTGRES_PASSWORD=test postgres:18
```

```bash
cd backend && POSTGRES_HOST=127.0.0.1 POSTGRES_PORT=55432 POSTGRES_PASSWORD=test uv run --no-sync pytest -q
```

**The deploy scripts** (`restore.sh`, `reset-admin-password.sh`, backups, JSON logs, `/metrics`) on a stack of their own,
built from the checkout and removed afterwards. Takes several minutes; never give it the installation's own project name.

```bash
deploy/tests/operations.sh nr-operations-test
```

**The frontend**:

```bash
cd frontend && npm ci && npm test
```

**The browser checks** (Playwright) against stacks of their own, built from the checkout and removed afterwards. Never give
one the installation's own name. `E2E_PORT` (default 18080) and `E2E_HTTPS_PORT` (default 18443) choose a stack's ports, so
two stacks need two of each.

- A **seeded** stack (`stack.sh up <project>`): every role's pages on a desktop and at 375, 360 and 320 px, a request and a
  swap on a phone, the month close, the Backups card, a 64-nurse unit's windowed grid, re-plan and swap check, the PWA's
  manifest and service worker, and a deploy picked up. Seeding solves four months for real: about two minutes.
- An **empty** stack (`stack.sh up <project> --empty`): the journey from the System Admin's first login to a swap in force, on
  a phone and on a desktop, then races, expiry by date (the checks' clock) and a solver that cannot be reached. Each journey
  empties its database first (`stack.sh reset`), so the set runs again on the same stack.

```bash
cd e2e && npm ci && npx playwright install chromium
```

```bash
E2E_PORT=18080 E2E_HTTPS_PORT=18443 e2e/stack.sh up nr-e2e
```

```bash
E2E_PORT=18081 E2E_HTTPS_PORT=18444 e2e/stack.sh up nr-e2e-journey --empty
```

```bash
cd e2e && E2E_STACK=nr-e2e E2E_JOURNEY_STACK=nr-e2e-journey npx playwright test
```

```bash
e2e/stack.sh down nr-e2e && e2e/stack.sh down nr-e2e-journey
```

Either variable alone runs only its own stack's projects. `stack.sh` also moves a stack's clock (`clock <project> <days>`),
runs a periodic job now in its worker (`fire <project> <module.tasks.job>`) and finds a sound swap (`swap`); the checks use
them, and its header says how.

**CI** is GitHub Actions, on every pull request and on `main`: `.github/workflows/ci.yml` (the solver's, the backend's and
the frontend's suites, the frontend's six times at once, the OpenAPI document and client matching, the image build) and
`.github/workflows/browser-checks.yml`, which runs `e2e/ci.sh`: the image, both stacks, every Playwright project, then the
deploy scripts' test, and everything removed. The same script runs from a checkout, about 11 minutes here; it fails if
anything fails.

```bash
e2e/ci.sh
```

## Change the API

The frontend's client is generated from the backend's OpenAPI document, and both are committed. CI
regenerates them and fails if anything differs, so an incompatible API change breaks the build.

```bash
cd backend && SECRET_KEY=x POSTGRES_PASSWORD=x SOLVER_TOKEN=x uv run --no-sync python manage.py export_openapi_schema --api config.api.api --indent 2 --output ../frontend/openapi.json
```

```bash
cd frontend && npm run generate:api
```

## Layout

| Path | What |
|---|---|
| `backend/` | Django, Django Ninja, the Procrastinate worker |
| `solver/` | The vendored `nurse_roster` package and its tests, frozen in from its original repository (ADR 0002), and `solver_service`, the HTTP service around it |
| `frontend/` | Vite, React, shadcn/ui on Base UI |
| `deploy/` | Compose files, Caddyfile, `.env.example`, the install guide and its scripts, the compose-level test |
| `e2e/` | The Playwright checks, the stacks they run against (`stack.sh`), their seed, and what CI runs (`ci.sh`) |
| `scripts/` | `verify-backend.sh` and `verify-frontend.sh`: a commit's suites on a clean copy, as a ticket branch is checked before it reaches `main` |
| `docs/guides/` | How to develop a feature here with agents |
| `.github/workflows/` | CI: `browser-checks.yml` runs `e2e/ci.sh` |
| `Dockerfile` | One multi-stage build, one image, three containers |
