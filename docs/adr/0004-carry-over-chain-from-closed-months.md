---
status: accepted
date: 2026-11-04
---
# Next month plans from a projected carry-over; a month's close always starts from the previous closed month

A unit's roster for a month is normally solved and approved before the previous month has
ended, so its solve input takes the *projected* carry-over (computed from the previous month's
roster in force at that moment). When a month ends, the app closes it automatically from the
roster in force plus every recorded leave and pin, and that close takes as its input the
carry-over of the *previous closed month*, never the projection the plan used. Each closed
month therefore corrects the projection error of the one before it, and the error never
accumulates along the chain. A close may be redone (to record late facts) until the following
month is itself closed. The carry-over handed into January has the overtime-to-date and the
fairness balances reset to zero: the year boundary is applied when January's input is built,
never inside a close.

The alternative, waiting for the close before solving the next month, would delay every roster
to the first days of the month it covers; carrying projections forward unconditionally would
let small differences compound across the year.
