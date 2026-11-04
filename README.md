# Nurse rostering

A hospital's monthly nurse rosters: unit managers generate them with a CP-SAT solver, the Deputy
CNO approves them, nurses see them, make requests and propose swaps. One installation serves one
hospital, as one `docker compose` stack on one server.

The agreed design is [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), the vocabulary is
[GLOSSARY.md](GLOSSARY.md), the reasons are in [docs/adr](docs/adr/) and the work is cut into
tickets under `.scratch/nurse-rostering-v1/issues/`.

## Run the stack

You need Docker with Compose. From a checkout:

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

The answer reports `"solver": {"reachable": true, ...}`. Without a `DOMAIN` the certificate is
self-signed, so a browser warns once. With a `DOMAIN` whose DNS points at the server, and ports 80
and 443 open to the internet, Caddy obtains a Let's Encrypt certificate by itself.

The solver publishes no port and sits on an internal network only `web` and `worker` can reach.

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

**The frontend**:

```bash
cd frontend && npm ci && npm test
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
| `deploy/` | Compose files, Caddyfile, `.env.example` |
| `Dockerfile` | One multi-stage build, one image, three containers |
