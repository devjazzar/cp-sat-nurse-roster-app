#!/usr/bin/env bash
# Restores the database from a backup. Restore is deliberately a script on the server, not a button (docs/ARCHITECTURE.md
# section 2). Run it from anywhere; it works on the stack of the compose.yaml beside it, as `docker compose` does there.
#
#   ./restore.sh nurse-roster-20261105T230000Z.dump      a backup the server keeps (the names are on the health page)
#   ./restore.sh /home/it/copies/nurse-roster-....dump   a copy from elsewhere, an off-site one for instance
#
# What it does, in order (deploy/INSTALL.md, "Restore a backup"):
#   1. stops `web` and `worker`, so nothing writes; Caddy stays up and answers 502 meanwhile;
#   2. takes a backup of the database as it stands, kept beside the others, so a wrong choice can be undone;
#   3. restores into a new database, and only once that has worked puts it in the old one's place;
#   4. starts `web` and `worker` again: `web` migrates a backup from an older version forward.
# If anything fails before step 3's swap, the database is as it was, and `web` and `worker` start again on it.
#
# Options: --yes skips the question. The project is compose's own: COMPOSE_PROJECT_NAME, COMPOSE_FILE and
# COMPOSE_ENV_FILES are honoured, as `docker compose` honours them.
set -euo pipefail
cd "$(dirname "$0")"

usage() { echo "usage: $0 [--yes] <backup name or file>" >&2; exit 2; }
ask=1
case "${1:-}" in --yes) ask=0; shift ;; esac
[[ $# -eq 1 ]] || usage
backup=$1

DB=nurse_roster
RESTORING=nurse_roster_restoring
NAME='^nurse-roster-[0-9]{8}T[0-9]{6}Z\.dump$'

compose() { docker compose "$@"; }
psql_db() {
  compose exec -T -e PGOPTIONS='-c client_min_messages=warning' db \
    psql --username "$DB" --dbname postgres --quiet --no-psqlrc --set ON_ERROR_STOP=1 "$@"
}
# One-off containers of the worker's image read the backups volume, whether or not the worker runs.
in_worker() { compose run --rm --no-deps -T worker "$@"; }

if [[ -f $backup ]]; then
  source_of() { cat -- "$backup"; }
  what="the file $backup"
elif [[ $backup =~ $NAME ]]; then
  in_worker test -f "/backups/$backup" || { echo "No backup called $backup on this server. The health page lists them." >&2; exit 1; }
  source_of() { in_worker cat "/backups/$backup"; }
  what="the backup $backup"
else
  echo "$backup is neither a file here nor the name of a backup (nurse-roster-<UTC time>.dump)." >&2
  exit 1
fi

compose ps --status running --services | grep -qx db || { echo "The database service is not running: start it first." >&2; exit 1; }

if [[ $ask == 1 ]]; then
  echo "This replaces every row of the application's database with $what."
  echo "Everything done since that backup is lost; a backup of the database as it stands is taken first."
  read -r -p "Type RESTORE to go on: " answer
  [[ $answer == RESTORE ]] || { echo "Nothing was changed."; exit 1; }
fi

swapped=0
restart() {
  status=$?
  if [[ $swapped == 0 ]]; then
    psql_db -c "DROP DATABASE IF EXISTS $RESTORING WITH (FORCE)" >/dev/null 2>&1 || true
    [[ $status == 0 ]] || echo "The restore did not finish. The database is as it was; starting the application again." >&2
  fi
  compose up -d --no-deps web worker
}
trap restart EXIT

echo "Stopping web and worker…"
compose stop web worker

echo "Taking a backup of the database as it stands…"
before=$(in_worker python manage.py backup | tail -n 1)
echo "Kept as $before."

echo "Restoring $what into a new database…"
psql_db -c "DROP DATABASE IF EXISTS $RESTORING WITH (FORCE)" -c "CREATE DATABASE $RESTORING OWNER $DB"
source_of | compose exec -T db pg_restore --username "$DB" --dbname "$RESTORING" --no-owner --exit-on-error --single-transaction

echo "Putting it in the old one's place…"
psql_db -c "DROP DATABASE $DB WITH (FORCE)" -c "ALTER DATABASE $RESTORING RENAME TO $DB"
swapped=1

echo "Starting web and worker…"
trap - EXIT
compose up -d --no-deps --wait web worker
echo "Restored from $what. The database as it stood before is the backup $before."
