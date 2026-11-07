#!/usr/bin/env bash
# Verify the frontend on the clean copy scripts/verify-backend.sh exported (docs/guides/local-development.md, "Verify on a
# clean copy"): `npm ci`, the suite once on its own, then six runs of it at the same time, then the build. The parallel runs
# are the point: a test that waits on a clock or on the order of two renders passes alone and fails under load, and
# `e2e/ci.sh` on the same machine is that load. Ticket 24's first head failed here.
#
#   scripts/verify-frontend.sh <dir> [runs]
#
# Each parallel run's full output is kept in <dir>/frontend-run-<n>.log, for the name of what failed.
set -uo pipefail
if [[ $# -lt 1 ]]; then echo "usage: $0 <dir> [runs]" >&2; exit 2; fi
dir=$1; runs=${2:-6}
failed=0

cd "$dir/frontend" || exit 1
npm ci --no-audit --no-fund --silent >/dev/null 2>&1 || { echo "npm ci failed"; exit 1; }

npm test 2>&1 | grep -E "^ +Tests "; [[ ${PIPESTATUS[0]} == 0 ]] && echo "alone: passed" || { echo "alone: FAILED"; failed=1; }

pids=()
for n in $(seq "$runs"); do
  (npm test > "$dir/frontend-run-$n.log" 2>&1) & pids+=($!)
done
for n in $(seq "$runs"); do
  if wait "${pids[$((n - 1))]}"; then
    echo "run $n: $(grep -E '^ +Tests ' "$dir/frontend-run-$n.log" | tr -s ' ')"
  else
    echo "run $n: FAILED: $(grep -E '^ FAIL ' "$dir/frontend-run-$n.log" | sort -u | head -3 | tr -s ' ' | tr '\n' ';')"
    failed=1
  fi
done

npm run build 2>&1 | grep -E "built in|error"; [[ ${PIPESTATUS[0]} == 0 ]] && echo "build: passed" || { echo "build: FAILED"; failed=1; }

[[ $failed == 0 ]] && echo "frontend: every check passed" || echo "frontend: FAILED, see above"
exit $failed
