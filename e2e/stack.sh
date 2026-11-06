#!/usr/bin/env bash
# A stack of its own for the browser checks, built from this checkout: its own compose project, secrets, volumes, image tag and
# ports. It never touches another project, and refuses the installation's own name.
#
#   e2e/stack.sh up <project>        build, start, seed (e2e/seed.py), take a backup; writes e2e/.stack/<project>.json for playwright.config.ts
#   e2e/stack.sh rebuild <project>   build the image again from this checkout and restart on it, keeping the data
#   e2e/stack.sh redeploy <project>  a new deploy, as far as a browser can tell: a new marker in index.html and a changed
#                                    service worker, then `web` restarted
#   e2e/stack.sh down <project>      remove the containers, volumes, image and e2e/.stack/<project>.*
#
# E2E_PORT (default 18080) is web over HTTP on 127.0.0.1, the checks' origin; E2E_HTTPS_PORT (default 18443) is Caddy.
# Needs Docker with Compose v2.24 or later, openssl and python3.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
usage="usage: $0 up|rebuild|redeploy|down <project>"
command=${1:?$usage}
project=${2:?$usage}
[[ $project != nurse-roster ]] || { echo "Refused: nurse-roster is the installation's own project." >&2; exit 2; }
[[ $project =~ ^[a-z0-9][a-z0-9_-]*$ ]] || { echo "Refused: a compose project name is lower case letters, digits, - and _." >&2; exit 2; }
state="$here/.stack"
env_file="$state/$project.env"
mkdir -p "$state"

compose() {
  COMPOSE_PROJECT_NAME=$project COMPOSE_FILE="$here/../deploy/compose.yaml:$here/compose.e2e.yaml" COMPOSE_ENV_FILES=$env_file \
    docker compose "$@"
}

case $command in
  up)
    [[ ! -e $env_file ]] || { echo "$project is already up (or was not taken down): $0 down $project" >&2; exit 2; }
    port=${E2E_PORT:-18080}
    cat > "$env_file" <<EOF
SECRET_KEY=$(openssl rand -hex 32)
POSTGRES_PASSWORD=$(openssl rand -hex 16)
SOLVER_TOKEN=$(openssl rand -hex 16)
INITIAL_ADMIN_PASSWORD=$(openssl rand -hex 12)
APP_IMAGE=$project-app
APP_VERSION=e2e
E2E_PORT=$port
E2E_HTTPS_PORT=${E2E_HTTPS_PORT:-18443}
EOF
    password=$(openssl rand -hex 12)
    echo "# Building and starting $project…"
    compose up -d --build --wait --quiet-pull
    compose cp "$here/../solver/service_tests/fixtures/four_nurses.json" web:/tmp/four_nurses.json >/dev/null
    echo "# Seeding (one month solved for real, about half a minute)…"
    seed=$(compose exec -T -e SEED_PASSWORD="$password" web python manage.py shell < "$here/seed.py" | sed -n 's/^E2E_SEED //p')
    [[ -n $seed ]] || { echo "The seed printed nothing." >&2; exit 1; }
    # A backup at once, for the checks that it is never served from a cache, rather than within the worker's first five minutes.
    compose exec -T worker python manage.py backup >/dev/null
    python3 - "$state/$project.json" "$port" "${E2E_HTTPS_PORT:-18443}" "$password" "$seed" <<'EOF'
import json, sys
path, port, https_port, password, seed = sys.argv[1:]
json.dump({"baseURL": f"http://localhost:{port}", "caddyURL": f"https://localhost:{https_port}", "password": password,
           **json.loads(seed)}, open(path, "w"), indent=2)
EOF
    chmod 600 "$env_file" "$state/$project.json"
    echo "# Up: e2e/.stack/$project.json. Run the checks with E2E_STACK=$project npx playwright test"
    ;;
  rebuild)
    [[ -e $env_file ]] || { echo "Nothing of $project here: $0 up $project" >&2; exit 2; }
    compose up -d --build --wait --quiet-pull
    ;;
  redeploy)
    marker="$(date +%s)-$RANDOM"
    compose exec -T web sh -c "sed -i 's|<head>|<head><meta name=\"e2e-deploy\" content=\"$marker\">|' /app/spa/index.html \
      && printf '\n// e2e deploy %s\n' $marker >> /app/spa/sw.js"
    compose restart web >/dev/null
    compose up -d --wait web >/dev/null
    echo "$marker"
    ;;
  down)
    [[ -e $env_file ]] || { echo "Nothing of $project here." >&2; exit 2; }
    compose down -v --remove-orphans
    docker image rm "$project-app:e2e" >/dev/null 2>&1 || true
    rm -f "$env_file" "$state/$project.json"
    ;;
  *)
    echo "$usage" >&2; exit 2 ;;
esac
