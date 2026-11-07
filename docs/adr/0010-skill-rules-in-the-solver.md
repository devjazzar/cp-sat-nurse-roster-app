---
status: accepted
date: 2026-11-07
---
# Skill rules live in the vendored solver; the solve input goes to version 2, and version 1 is still read

Skills and credentials per shift-day add two rules: a skill need (at least so many nurses holding
a skill on a shift each day, hard or soft by the unit's flag) and the bar on a nurse whose required
skill has expired (no shift that day). Both go into the vendored solver's rule registry
(`solver/nurse_roster/rules.py`), beside team leader and gender, which they generalise. This is
the first change to the package since ADR 0002 vendored it, and that ADR anticipates it: it froze
the original repository, not the package, so that a change to the request/result contract lands in
the same commit as the app code that depends on it.

The alternative, checking skills in the app around a solver that knows nothing of them, was
rejected: the registry exists so that a rule cannot be in the model and missing from the
validator, and the app checks every grid (a draft as it is edited, a swap, an approval, a close)
with the solver's own code. A rule outside it would have to be repeated in each of those places,
and the solver's roster could still break it.

The solve input moves from version 1 to version 2: each nurse carries her skills with the last
day in the month each counts, and the department block carries its skill needs and its hard/soft
flag, the hospital's weights the skill shortfall price. The loader goes on reading a version 1
input as one with no skills, no needs and the flag at its default, because every stored input is
read again later: a result is explained from it, a draft is compared with it, a result is restored
onto it, and a closed month is re-closed from it. The solver had refused older schemas of its
internal problem (DESIGN.md, 2026-11-03); the request contract now keeps the old version readable
instead, since the app's history depends on it. Version 2 is the only version the app writes.

## Consequences

- An expiry reaches the solver as a date inside the month, or not at all: a skill expired before
  the month is left out, one valid past its last day is held all month.
- The solver's precheck, explain and validate words gain the two rules, and the swap judging keeps
  a colleague's skills behind the same hidden form as her other facts.
