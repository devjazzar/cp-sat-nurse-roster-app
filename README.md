# Nurse rostering

A hospital's monthly nurse rosters: unit managers generate them with a CP-SAT solver, the Deputy
CNO approves them, nurses see them, make requests and propose swaps. One installation serves one
hospital, as one `docker compose` stack on one server.

The agreed design is [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), the vocabulary is
[GLOSSARY.md](GLOSSARY.md), the reasons are in [docs/adr](docs/adr/) and the work is cut into
tickets under `.scratch/nurse-rostering-v1/issues/`.

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

```bash
cd deploy
docker compose -f compose.yaml -f compose.dev.yaml up --build
```

Open <http://localhost:5173>. Vite serves the SPA with hot reload and passes `/api` on to Django.
Django and the solver service reload on a change. The worker does not: restart it after changing a
task. Set `DEV_POSTGRES_PORT` in `.env` if something else holds port 5432.

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

**The backend** needs PostgreSQL 18. The test settings expect the one the development stack
publishes; `POSTGRES_HOST`, `POSTGRES_PORT` and `POSTGRES_PASSWORD` point them elsewhere. Its
password there is `POSTGRES_PASSWORD` from `.env`.

```bash
cd backend && uv run --no-sync pytest -q
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

**The browser checks** (Playwright, at phone sizes: the nurse's pages, a request, a swap, the PWA's manifest and service
worker, a deploy picked up) against a stack of their own, built from the checkout, seeded, and removed afterwards.
`E2E_PORT` (default 18080) and `E2E_HTTPS_PORT` (default 18443) choose its ports. Never give it the installation's own name.

```bash
cd e2e && npm ci && npx playwright install chromium
```

```bash
e2e/stack.sh up nr-e2e
```

```bash
cd e2e && E2E_STACK=nr-e2e npx playwright test
```

```bash
e2e/stack.sh down nr-e2e
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
| `e2e/` | The Playwright checks, the stack they run against (`stack.sh`) and its seed |
| `Dockerfile` | One multi-stage build, one image, three containers |
