#!/usr/bin/env bash
# Run one heavy local command under the machine-wide lock, so only one session at a time runs a full suite or a scratch
# stack (docs/guides/local-development.md, appendix A, "How to work"). It waits for the lock, runs the command, and releases
# the lock when the command ends, whatever the outcome, so a hold never outlives its work.
#
#   scripts/heavy-run.sh <owner> <command> [args...]   e.g. scripts/heavy-run.sh ticket-56 bash -c 'cd backend && uv run pytest'
#   scripts/heavy-run.sh --status                      who holds it, since when, and whether the holder is still alive
#
# Run it with `run_in_background` on the Bash call: the wait can be long, and the session is woken when it ends.
# A lock whose recorded process is gone is taken over (its holder was killed before it could release). A lock with no
# recorded process, from before this script, is waited on, never removed.
set -uo pipefail
LOCK="$HOME/.cache/nurse-roster-heavy.lock"

alive() { [[ -f $LOCK/pid ]] && kill -0 "$(cat "$LOCK/pid")" 2>/dev/null; }

if [[ ${1:-} == --status ]]; then
  if [[ ! -d $LOCK ]]; then echo free; exit 0; fi
  echo "held by: $(cat "$LOCK/owner" 2>/dev/null || echo unknown)"
  if [[ ! -f $LOCK/pid ]]; then echo "no pid recorded (taken by hand)"; elif alive; then echo "pid $(cat "$LOCK/pid") alive"
  else echo "pid $(cat "$LOCK/pid") gone: stale, the next heavy-run takes it over"; fi
  exit 0
fi
if [[ $# -lt 2 ]]; then echo "usage: $0 <owner> <command> [args...] | --status" >&2; exit 2; fi
owner=$1; shift
mkdir -p "$(dirname "$LOCK")"

waited=0
until mkdir "$LOCK" 2>/dev/null; do
  if [[ -f $LOCK/pid ]] && ! alive; then
    echo "heavy-run: taking over a stale lock from $(cat "$LOCK/owner" 2>/dev/null || echo unknown)" >&2
    rm -rf "$LOCK"; continue
  fi
  (( waited++ == 0 )) && echo "heavy-run: waiting for $(cat "$LOCK/owner" 2>/dev/null || echo unknown)" >&2
  sleep 30
done
trap 'rm -rf "$LOCK"' EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
echo "$owner $(date)" > "$LOCK/owner"
echo $$ > "$LOCK/pid"
echo "heavy-run: lock taken by $owner" >&2

"$@"
status=$?
echo "heavy-run: $owner's command exited $status; lock released" >&2
exit $status
