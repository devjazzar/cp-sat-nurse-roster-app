---
status: accepted
date: 2026-11-04
---
# An accepted request or swap becomes a pinned cell, not a soft preference

The solver offers two ways to honour a nurse's wish: soft day requests (`undesired_days`,
`desired_days`, priced by a weight) and hard pinned cells. The app uses only pinned cells. A
request a unit manager has accepted, and a swap both nurses and the manager have accepted, are
promises the hospital has made; a roster that quietly breaks one for a cheaper objective would
not be understood by anyone. The price is that pins can make a month infeasible, which the
solver's precheck reports before a solve and the manager resolves by cancelling a request.

The soft request kinds stay available in the solver and may be offered later as a weaker,
unapproved "preference"; v1 does not expose them.
