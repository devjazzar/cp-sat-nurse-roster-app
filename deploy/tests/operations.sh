#!/usr/bin/env bash
# The compose-level test of ticket 22, on a stack of its own built from this checkout: its own project, secrets, volumes, image
# tag and HTTPS port. It never touches another project, and refuses the installation's own name.
#
#   deploy/tests/operations.sh <project> [--keep]
#
# It checks, in order: the public health answer through Caddy; /metrics refused through Caddy and answered inside; JSON lines
# from web, worker and solver; a backup taken by the worker's job; the retention jobs; a restore by deploy/restore.sh, which
# takes back what was written after the backup; deploy/reset-admin-password.sh lifting a lock from wrong passwords. Then it
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

for service in web worker solver; do
  lines=$(compose logs --no-log-prefix --no-color "$service" | python3 -c '
import json, sys
lines = [line for line in sys.stdin if line.strip()]
for line in lines:
    json.loads(line)
print(len(lines))') || fail "$service logged a line that is not JSON"
  [[ $lines -gt 0 ]] && pass "$service: $lines lines, each one JSON" || fail "$service logged nothing"
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
for task in ops.tasks.remove_ended_jobs notifications.tasks.remove_old_notifications accounts.tasks.clear_expired_sessions; do
  compose exec -T worker python manage.py queue defer --ignore-already-enqueued "$task" '{"timestamp": 0}' >/dev/null
  done_ok() { [[ $(sql "SELECT count(*) FROM procrastinate_jobs WHERE task_name = '$task' AND status = 'succeeded'") -ge 1 ]]; }
  wait_for 60 done_ok && pass "$task succeeded" || fail "$task did not succeed: $(sql "SELECT status FROM procrastinate_jobs WHERE task_name = '$task'")"
done

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

echo "# All checks passed."
