#!/bin/bash
# The main session's watcher over running ticket sessions (docs/guides/local-development.md, appendix C). Run it with
# `run_in_background` on the Bash call; it exits, and so wakes the session, on the first of:
#   CHANGED     a pull request's state changed (open, merged, closed) or a check turned failing or recovered
#   LOCK HELD   one holder has kept the heavy-run lock longer than LOCK_LIMIT seconds (default 1800)
#   HEARTBEAT   HEARTBEAT seconds passed (default 1200): look for a session that sits idle while its checks are green
# A new head alone wakes no one, nor does a check that is merely running or green: those are the session's own business.
#
#   HEARTBEAT=1500 LOCK_LIMIT=1800 scripts/watch-tickets.sh <pr> [<pr> ...]
cd "$(dirname "$0")/.." || exit 1
LOCK="$HOME/.cache/nurse-roster-heavy.lock"
snap() {
  for n in "$@"; do
    st=$(gh pr view "$n" --json state --jq .state 2>/dev/null)
    if gh pr checks "$n" 2>/dev/null | awk '{print $2}' | grep -q fail; then v=FAILING; else v=ok; fi
    echo "PR$n $st $v"
  done
}
owner() { cat "$LOCK/owner" 2>/dev/null || echo free; }
first=$(snap "$@"); start=$(date +%s); held=$(owner); since=$start
while :; do
  sleep 60
  now=$(snap "$@")
  if [[ "$now" != "$first" ]]; then echo "CHANGED"; echo "--- before"; echo "$first"; echo "--- now"; echo "$now"; exit 0; fi
  # A new holder restarts the clock.
  if [[ $(owner) != "$held" ]]; then held=$(owner); since=$(date +%s); fi
  if [[ $held != free ]] && (( $(date +%s) - since > ${LOCK_LIMIT:-1800} )); then
    echo "LOCK HELD: $held"; echo "$now"; exit 0
  fi
  (( $(date +%s) - start > ${HEARTBEAT:-1200} )) && { echo "HEARTBEAT"; echo "$now"; echo "lock: $(owner)"; exit 0; }
done
