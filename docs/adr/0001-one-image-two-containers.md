---
status: accepted
date: 2026-11-04
---
# One application image, run as web, worker and an isolated solver container

The product ships one application image per release. A `docker compose` file starts it three
times, with different commands: `web` (the Django app and its API), `worker` (the queue worker
that drives solves and scheduled jobs) and `solver` (an HTTP wrapper around the CP-SAT
package). The solver container publishes no port, holds no database credentials or secrets
beyond a shared token, and sits on a private network only `web` and `worker` can reach, so the
solver layer is unreachable from the internet by construction. PostgreSQL and Caddy run from
their stock images.

## Considered options

- One container with a process supervisor (web, solver and proxy in one). Literally one image,
  but against Docker convention; the solver could not be restarted or resource-limited on its own.
- Two images (web, solver). Cleaner at the Docker level, but two build pipelines and two
  artefacts to version for one product.

## Consequences

- Installation is `docker compose up -d` with an `.env` file; there is nothing else to install.
- The solver is a pure function reachable only over the internal network; it never reads the
  database. Every durable fact about a solve lives in the application database, written by
  the worker.
