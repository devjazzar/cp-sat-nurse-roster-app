#!/usr/bin/env bash
# Verify a commit's backend and solver on a clean copy, the way the main session checks a ticket branch before it reaches
# main (docs/guides/local-development.md, "Verify on a clean copy"). Nothing of the working tree is used: the commit is
# exported with `git archive` into <dir>, and the backend's tests run against a throwaway PostgreSQL 18 container of their
# own, removed at the end. The dev stack is never touched.
#
#   scripts/verify-backend.sh <commit> <dir> [port]
#
# <dir> is created (and emptied first); scripts/verify-frontend.sh takes the same <dir> afterwards. [port] is the localhost
# port the throwaway database is published on (default 55432): give each copy running at the same time its own.
#
# It prints one line per check and exits non-zero if any failed:
#   openapi-same | OPENAPI-DIFFERS     frontend/openapi.json matches the backend's export
#   No changes detected                 makemigrations --check is clean
#   N passed ...                        the backend's suite, then the solver's
set -uo pipefail
if [[ $# -lt 2 ]]; then echo "usage: $0 <commit> <dir> [port]" >&2; exit 2; fi
commit=$1; dir=$2; port=${3:-55432}
repo=$(cd "$(dirname "$0")/.." && pwd)
name=verify-$(basename "$dir")-$port
fake="SECRET_KEY=x SOLVER_TOKEN=x"
failed=0

rm -rf "$dir" && mkdir -p "$dir"
git -C "$repo" archive "$commit" | tar -x -C "$dir"
echo "exported $(git -C "$repo" rev-parse --short "$commit") to $dir"

docker run -d --rm --name "$name" -p "127.0.0.1:$port:5432" \
  -e POSTGRES_USER=nurse_roster -e POSTGRES_DB=nurse_roster -e POSTGRES_PASSWORD=verify postgres:18 >/dev/null
trap 'docker stop "$name" >/dev/null 2>&1 || true' EXIT

(cd "$dir" && uv sync --all-packages --python 3.14 -q) || { echo "uv sync failed"; exit 1; }

cd "$dir/backend"
env $fake POSTGRES_PASSWORD=x uv run --no-sync python manage.py export_openapi_schema \
  --api config.api.api --indent 2 --output "$dir/export.json" >/dev/null 2>&1
if diff -q "$dir/export.json" "$dir/frontend/openapi.json" >/dev/null; then echo openapi-same; else echo OPENAPI-DIFFERS; failed=1; fi

migrations=$(env $fake POSTGRES_PASSWORD=x uv run --no-sync python manage.py makemigrations --check --dry-run 2>&1 | tail -1)
echo "$migrations"; [[ $migrations == "No changes detected" ]] || failed=1

for _ in $(seq 30); do docker exec "$name" pg_isready -U nurse_roster -d nurse_roster >/dev/null 2>&1 && break; sleep 1; done
env $fake POSTGRES_HOST=127.0.0.1 POSTGRES_PORT=$port POSTGRES_PASSWORD=verify \
  uv run --no-sync pytest -q -p no:cacheprovider 2>&1 | tail -1; [[ ${PIPESTATUS[0]} == 0 ]] || failed=1

cd "$dir/solver"
uv run --no-sync pytest -q -p no:cacheprovider 2>&1 | tail -1; [[ ${PIPESTATUS[0]} == 0 ]] || failed=1

[[ $failed == 0 ]] && echo "backend and solver: every check passed" || echo "backend and solver: FAILED, see above"
exit $failed
