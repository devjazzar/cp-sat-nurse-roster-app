#!/usr/bin/env bash
# The compose-level test of ticket 22, on a stack of its own built from this checkout: its own project, secrets, volumes, image
# tag and HTTPS port. It never touches another project, and refuses the installation's own name.
#
#   deploy/tests/operations.sh <project> [--keep]
#
# It checks, in order: the public health answer through Caddy; /metrics refused through Caddy and answered inside; no answer
# through Caddy framed (ticket 62); no address a client claims in the audit log (ticket 69); JSON lines
# from web, worker and solver, and the push key pair made at the first start; the worker alone on a network with a way out
# (ticket 42); the browser checks' clock off (ticket 24); a backup taken by the worker's job; the retention jobs; a restore by deploy/restore.sh, which
# takes back what was written after the backup; deploy/reset-admin-password.sh lifting a lock from wrong passwords; the System
# Admin's health answer and /metrics counting pushes sent and failed. Then it
# removes everything it made, unless --keep (the stack stays up, and the line to remove it is printed).
# TEST_HTTPS_PORT (default 18443) is where Caddy answers on 127.0.0.1. Needs docker, curl, openssl and python3.
set -euo pipefail
cd "$(dirname "$0")/.."

project=${1:?usage: $0 <project> [--keep]}
keep=${2:-}
[[ $project != nurse-roster ]] || { echo "Refused: nurse-roster is the installation's own project." >&2; exit 2; }
port=${TEST_HTTPS_PORT:-18443}
base="https://localhost:$port"

work=$(mktemp -d)
admin_password=$(openssl rand -hex 12)
cat > "$work/env" <<EOF
SECRET_KEY=$(openssl rand -hex 32)
POSTGRES_PASSWORD=$(openssl rand -hex 16)
SOLVER_TOKEN=$(openssl rand -hex 16)
INITIAL_ADMIN_PASSWORD=$admin_password
APP_IMAGE=$project-app
APP_VERSION=test
TEST_HTTPS_PORT=$port
EOF
export COMPOSE_PROJECT_NAME=$project COMPOSE_FILE=compose.yaml:tests/compose.test.yaml COMPOSE_ENV_FILES=$work/env

compose() { docker compose "$@"; }
sql() { compose exec -T db psql --username nurse_roster --dbname nurse_roster --tuples-only --no-align --no-psqlrc -c "$1"; }
pass() { echo "ok - $*"; }
fail() { echo "FAILED - $*" >&2; exit 1; }
# Waits up to $1 seconds for a command to succeed: for a job to run or a service to answer, never to show a thing did not happen.
wait_for() {
  local seconds=$1; shift
  for _ in $(seq "$seconds"); do "$@" >/dev/null 2>&1 && return 0; sleep 1; done
  return 1
}
finish() {
  status=$?
  if [[ $keep == --keep ]]; then
    echo "Kept. Remove with: COMPOSE_PROJECT_NAME=$project COMPOSE_FILE=$COMPOSE_FILE COMPOSE_ENV_FILES=$work/env docker compose down -v && docker image rm $project-app:test"
  else
    compose down -v --remove-orphans >/dev/null 2>&1 || true
    docker image rm "$project-app:test" >/dev/null 2>&1 || true
    rm -rf "$work"
  fi
  exit $status
}
trap finish EXIT

echo "# Building and starting $project…"
compose up -d --build --wait --quiet-pull

# ---- health, metrics and logs ----------------------------------------------------------------------------------------------
wait_for 60 curl -sfk "$base/api/health" || fail "Caddy does not answer on $base"
health=$(curl -sk "$base/api/health")
python3 -c 'import json, sys; assert json.loads(sys.argv[1]) == {"status": "ok", "database": True, "solver": {"reachable": True}}, sys.argv[1]' "$health" \
  && pass "the public health answer says only reachability: $health"

code=$(curl -sk -o /dev/null -w '%{http_code}' "$base/metrics")
[[ $code == 404 ]] && pass "/metrics through Caddy: $code" || fail "/metrics through Caddy answered $code"
code=$(curl -sk -o /dev/null -w '%{http_code}' "$base/metrics/")
[[ $code == 404 ]] && pass "/metrics/ through Caddy: $code" || fail "/metrics/ through Caddy answered $code"
compose exec -T caddy wget -qO- http://web:8000/metrics | grep -qx 'nurse_roster_database_up 1' \
  && pass "/metrics on the internal network, from Caddy's container straight to web:8000" || fail "/metrics inside"

# Ticket 62: nothing through Caddy may be framed. Caddy says so on every answer, its own /metrics refusal included, and web
# says it again in its own words.
for path in / /unit-roster /api/health /metrics; do
  headers=$(curl -sk -o /dev/null -D - "$base$path" | tr -d '\r')
  grep -qix "content-security-policy: frame-ancestors 'none'" <<<"$headers" \
    || fail "$path through Caddy has no frame-ancestors 'none': $headers"
  [[ $path == /metrics ]] || grep -qix 'x-frame-options: DENY' <<<"$headers" || fail "$path through Caddy has no X-Frame-Options: DENY"
done
pass "/, /unit-roster, /api/health and /metrics through Caddy may not be framed"

# Ticket 69: the audit log's address is the one Caddy worked out, whatever a client claims. With TRUSTED_PROXIES empty, as
# here, Caddy believes no X-Forwarded-For and replaces any X-Client-IP; gunicorn drops X_Client_IP, the same WSGI key.
claims="$work/claims"
# Logs the System Admin in through Caddy with the extra headers given, and prints the address its audit entry records.
recorded_login() {
  rm -f "$claims"
  curl -sk -c "$claims" -b "$claims" "$base/api/auth/session" >/dev/null
  local code
  code=$(curl -sk -o /dev/null -w '%{http_code}' -c "$claims" -b "$claims" -H "Origin: $base" -H 'Content-Type: application/json' \
    -H "X-CSRFToken: $(awk '$6 == "csrftoken" {print $7}' "$claims")" "$@" \
    -d "{\"username\": \"admin\", \"password\": \"$admin_password\"}" "$base/api/auth/login")
  [[ $code == 200 ]] || fail "the System Admin's login through Caddy answered $code"
  sql "SELECT coalesce(host(ip), 'none') FROM audit_auditentry WHERE action = 'auth.login' ORDER BY id DESC LIMIT 1"
}
peer=$(recorded_login)
claimed=$(recorded_login -H 'X-Forwarded-For: 203.0.113.7' -H 'X-Client-IP: 203.0.113.8' -H 'X_Client_IP: 203.0.113.9')
[[ $peer != none && $claimed == "$peer" ]] \
  && pass "a client's X-Forwarded-For, X-Client-IP and X_Client_IP do not reach the audit log, which has the address Caddy saw: $peer" \
  || fail "the audit log recorded $peer for a login that claimed nothing and $claimed for one that claimed addresses"

for service in web worker solver; do
  lines=$(compose logs --no-log-prefix --no-color "$service" | python3 -c '
import json, sys
lines = [line for line in sys.stdin if line.strip()]
for line in lines:
    json.loads(line)
print(len(lines))') || fail "$service logged a line that is not JSON"
  [[ $lines -gt 0 ]] && pass "$service: $lines lines, each one JSON" || fail "$service logged nothing"
done

made=$(compose logs --no-log-prefix --no-color web | python3 -c '
import json, sys
print(sum(1 for line in sys.stdin if line.strip() and (json.loads(line).get("logger"), json.loads(line).get("message"))
          == ("ops.prepare", "Made the installation\u0027s push key pair.")))')
[[ $made == 1 ]] && pass "prepare logged the push key pair it made at the first start, once" || fail "web logged the push key pair $made times"
[[ $(sql "SELECT count(*) FROM notifications_pushkeypair") == 1 ]] && pass "and the database holds one pair" || fail "no one push key pair"

# ---- only the worker has a way out -------------------------------------------------------------------------------------------
# What the compose file promises of this running stack (ADR 0012): the worker is on a network that is not internal, for the
# push services, and web, the database and the solver are on none. Whether the hospital's firewall lets the worker out is the
# install checklist's. Read from the containers themselves and from Docker's own word on each network.
ways_out() {
  local container network found=""
  container=$(compose ps -q "$1")
  [[ -n $container ]] || { echo "no container"; return; }
  for network in $(docker inspect -f '{{range $name, $_ := .NetworkSettings.Networks}}{{$name}} {{end}}' "$container"); do
    [[ $(docker network inspect -f '{{.Internal}}' "$network") == false ]] && found="$found$network "
  done
  echo "${found% }"
}
out=$(ways_out worker)
[[ $out == "${project}_egress" ]] && pass "the worker is on one network that is not internal: $out" || fail "the worker's ways out: '$out'"
for service in web db solver; do
  out=$(ways_out "$service")
  [[ -z $out ]] && pass "$service is on no network with a way out" || fail "$service is on a network that is not internal: $out"
done

# ---- the browser checks' clock is off --------------------------------------------------------------------------------------
# e2e/compose.e2e.yaml alone passes E2E_CLOCK_FILE, which moves the hospital's date (nurses.membership.today, ticket 24). No
# service of an installation's compose file is given it, so no .env can switch it on; and it has no URL of its own, so there is
# nothing for Caddy to pass. Here: the variable in no service of compose.yaml as an installation runs it, nor in this stack's
# web and worker, whose setting is off and whose date is the real one.
COMPOSE_FILE=compose.yaml compose config --format json | python3 -c '
import json, sys
config = json.load(sys.stdin)
given = [name for name, service in config["services"].items() if "E2E_CLOCK_FILE" in (service.get("environment") or {})]
sys.exit(f"E2E_CLOCK_FILE is passed to {given}" if given else 0)' \
  && pass "deploy/compose.yaml passes the browser checks' clock to no service" || fail "the browser checks' clock in deploy/compose.yaml"
for service in web worker; do
  clock=$(compose exec -T "$service" python manage.py shell -c "
from django.conf import settings
from django.utils import timezone
from nurses import membership
print(settings.E2E_CLOCK_FILE, membership.today() == timezone.localdate())" 2>/dev/null | tail -1)
  [[ $clock == "None True" ]] && pass "$service: the clock is off and the hospital's date is the real one" || fail "$service's clock: $clock"
done

# ---- a backup by the job -----------------------------------------------------------------------------------------------------
backups() { compose exec -T worker sh -c 'ls /backups | grep -E "^nurse-roster-[0-9]{8}T[0-9]{6}Z\.dump$" || true'; }
compose exec -T worker python manage.py queue defer --ignore-already-enqueued ops.tasks.backup '{"timestamp": 0}' >/dev/null
has_backup() { [[ -n $(backups) ]]; }
wait_for 120 has_backup || fail "the backup job wrote no backup"
backup=$(backups | tail -n 1)
job=$(sql "SELECT status || ' ' || lock FROM procrastinate_jobs WHERE task_name = 'ops.tasks.backup' AND status <> 'todo' ORDER BY id DESC LIMIT 1")
[[ $job == "succeeded backup" ]] && pass "the job took $backup under the lock 'backup'" || fail "the backup job: '$job'"
mode=$(compose exec -T worker stat -c '%a %U' "/backups/$backup")
[[ $mode == "600 app" ]] && pass "the backup is the app user's alone: $mode" || fail "the backup's mode: $mode"
compose exec -T worker cat "/backups/$backup" | compose exec -T db pg_restore --list >/dev/null \
  && pass "pg_restore reads it" || fail "pg_restore cannot read $backup"

# ---- the retention jobs ------------------------------------------------------------------------------------------------------
sql "INSERT INTO notifications_pushattempt (at, outcome) VALUES (now() - interval '8 days', 'unreachable'), (now() - interval '6 days', 'sent')" >/dev/null
for task in ops.tasks.remove_ended_jobs notifications.tasks.remove_old_notifications notifications.tasks.remove_old_push_attempts accounts.tasks.clear_expired_sessions; do
  compose exec -T worker python manage.py queue defer --ignore-already-enqueued "$task" '{"timestamp": 0}' >/dev/null
  done_ok() { [[ $(sql "SELECT count(*) FROM procrastinate_jobs WHERE task_name = '$task' AND status = 'succeeded'") -ge 1 ]]; }
  wait_for 60 done_ok && pass "$task succeeded" || fail "$task did not succeed: $(sql "SELECT status FROM procrastinate_jobs WHERE task_name = '$task'")"
done
[[ $(sql "SELECT string_agg(outcome, ' ') FROM notifications_pushattempt") == sent ]] \
  && pass "a push attempt eight days old is gone and one six days old is kept" || fail "push attempts kept: $(sql "SELECT at, outcome FROM notifications_pushattempt")"

# ---- a restore ---------------------------------------------------------------------------------------------------------------
sql "CREATE TABLE written_after_the_backup (id int)" >/dev/null
# A file that is no backup, named relative to another directory: refused by pg_restore, so nothing changes.
echo "not a backup" > "$work/not-a-backup.dump"
deploy=$PWD
if (cd "$work" && "$deploy/restore.sh" --yes not-a-backup.dump); then fail "a file that is no backup was restored"; fi
[[ -n $(sql "SELECT to_regclass('written_after_the_backup')") ]] && pass "a failed restore leaves the database as it was" \
  || fail "a failed restore changed the database"
[[ $(sql "SELECT datname FROM pg_database WHERE datname LIKE 'nurse_roster%' ORDER BY 1" | tr '\n' ' ') == "nurse_roster " ]] \
  && pass "and leaves no database behind" || fail "databases left: $(sql "SELECT datname FROM pg_database")"
wait_for 60 curl -sfk "$base/api/health" && pass "the application answers again after the failed restore" || fail "no answer"

before=$(backups | wc -l | tr -d ' ')
./restore.sh --yes "$backup"
[[ -z $(sql "SELECT to_regclass('written_after_the_backup')") ]] && pass "the restore took back what was written after the backup" \
  || fail "the table written after the backup is still there"
[[ $(sql "SELECT count(*) FROM accounts_user WHERE username = 'admin'") == 1 ]] && pass "what the backup held is there" \
  || fail "the System Admin is missing after the restore"
after=$(backups | wc -l | tr -d ' ')
[[ $after -eq $((before + 1)) ]] && pass "the database as it stood was backed up first ($before backups, then $after)" \
  || fail "no backup before the restore ($before, then $after)"
wait_for 60 curl -sfk "$base/api/health" && pass "the application answers again after the restore" || fail "no answer after the restore"
[[ $(sql "SELECT datname FROM pg_database WHERE datname LIKE 'nurse_roster%' ORDER BY 1" | tr '\n' ' ') == "nurse_roster " ]] \
  && pass "no database is left over" || fail "databases left: $(sql "SELECT datname FROM pg_database")"
# The backup job that was running as that backup was taken comes back as running, under a worker long gone.
last=$(sql "SELECT coalesce(max(id), 0) FROM procrastinate_jobs")
compose exec -T worker python manage.py queue defer --ignore-already-enqueued solves.tasks.recover_lost_jobs '{"timestamp": 1}' >/dev/null
recovered() { [[ -n $(sql "SELECT 1 FROM procrastinate_jobs WHERE id > $last AND task_name = 'solves.tasks.recover_lost_jobs' AND status = 'succeeded'") ]]; }
wait_for 60 recovered && pass "recover_lost_jobs succeeds after the restore" || fail "recover_lost_jobs after the restore: $(sql "SELECT status FROM procrastinate_jobs WHERE id > $last")"
no_backup_stuck() { [[ -z $(sql "SELECT 1 FROM procrastinate_jobs WHERE task_name = 'ops.tasks.backup' AND status IN ('todo', 'doing')") ]]; }
wait_for 60 no_backup_stuck && pass "no backup job is left running or waiting behind the restored one" \
  || fail "backup jobs: $(sql "SELECT id || ' ' || status FROM procrastinate_jobs WHERE task_name = 'ops.tasks.backup'")"

# ---- the admin reset lifts a lock --------------------------------------------------------------------------------------------
jar="$work/cookies"
log_in() {
  rm -f "$jar"
  curl -sk -c "$jar" -b "$jar" "$base/api/auth/session" >/dev/null
  local token
  token=$(awk '$6 == "csrftoken" {print $7}' "$jar")
  curl -sk -o /dev/null -w '%{http_code}' -c "$jar" -b "$jar" -H "X-CSRFToken: $token" -H "Origin: $base" \
    -H 'Content-Type: application/json' -d "{\"username\": \"admin\", \"password\": \"$1\"}" "$base/api/auth/login"
}
[[ $(log_in "$admin_password") == 200 ]] && pass "the System Admin logs in" || fail "the System Admin cannot log in"
for _ in 1 2 3 4 5; do log_in not-the-password >/dev/null; done
[[ $(log_in "$admin_password") == 423 ]] && pass "five wrong passwords lock the account, the right one included" || fail "no lock"
printed=$(./reset-admin-password.sh)
new_password=$(sed -n 's/^New password for admin: //p' <<<"$printed")
[[ -n $new_password ]] || fail "the reset printed no password: $printed"
[[ $(log_in "$new_password") == 200 ]] && pass "the reset script lifted the lock and its password logs in" || fail "still refused"
[[ $(log_in "$admin_password") == 401 ]] && pass "the old password no longer does" || fail "the old password still works"

# ---- the health answer and /metrics count pushes ----------------------------------------------------------------------------
# The System Admin's health answer is closed until a forced password is changed, so the reset's is changed first. Then three
# sends are scripted as rows, as the worker writes one a send: the stack's worker may reach no push service on purpose.
[[ $(log_in "$new_password") == 200 ]] || fail "the System Admin cannot log in to read the health answer"
token=$(awk '$6 == "csrftoken" {print $7}' "$jar")
code=$(curl -sk -o /dev/null -w '%{http_code}' -c "$jar" -b "$jar" -H "X-CSRFToken: $token" -H "Origin: $base" \
  -H 'Content-Type: application/json' -d "{\"current_password\": \"$new_password\", \"new_password\": \"$(openssl rand -hex 12)\"}" \
  "$base/api/auth/change-password")
[[ $code == 200 ]] || fail "the forced password change answered $code"
push_block() { curl -sk -b "$jar" "$base/api/ops/health" | python3 -c 'import json, sys; print(json.dumps(json.load(sys.stdin)["push"], sort_keys=True))'; }
block=$(push_block) || fail "the health answer carries no push block"
[[ $block == '{"failed": 0, "last_failure": null, "sent": 0}' ]] && pass "the health answer carries the push block, empty before any push: $block" \
  || fail "the push block before any push: $block"
sql "INSERT INTO notifications_pushattempt (at, outcome) VALUES (now() - interval '2 hours', 'sent'), (now() - interval '1 hour', 'gone'), (now(), 'unreachable'), (now() - interval '25 hours', 'refused')" >/dev/null
block=$(push_block) || fail "the health answer lost its push block"
[[ $block == '{"failed": 2, "last_failure": "unreachable", "sent": 1}' ]] && pass "and counts the last 24 hours' attempts with the last failure's reason: $block" \
  || fail "the push block after three sends in the day: $block"
gauges=$(compose exec -T caddy wget -qO- http://web:8000/metrics | { grep '^nurse_roster_push_attempts{' || true; } | tr '\n' ' ')
[[ $gauges == 'nurse_roster_push_attempts{result="sent"} 1 nurse_roster_push_attempts{result="failed"} 2 ' ]] \
  && pass "/metrics carries the same two counts" || fail "/metrics on pushes: $gauges"

echo "# All checks passed."
