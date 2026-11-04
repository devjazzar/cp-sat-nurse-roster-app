---
status: accepted
date: 2026-11-04
---
# The solver is vendored into this monorepo; the original repository is frozen

The CP-SAT solver was developed and audited in `cp-sat-nurse-roster` as a stand-alone
command-line project. Its package and tests are copied into `solver/` here, and from then on
this repository is the only source of truth. The original repository stays as read-only history.

A git submodule or a published package would keep two repositories alive for one product and
let the app and the solver drift. Copying costs nothing now and keeps every change to the
solver's request/result contract in the same commit as the app code that depends on it.
