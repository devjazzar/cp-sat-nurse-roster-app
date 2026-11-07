---
status: accepted
date: 2026-11-07
---
# A cover adds one nurse to a shift-day; the first acceptance is the promise, as a pinned cell

When leave takes a shift off the roster in force, the shift-day is short and the manager had only hand edits and a re-plan.
A cover is the third way: the app lists the unit's staff nurses who could take the shift without newly breaking a hard rule,
judged with the solver's own check as a swap is, ranked by who stands furthest below her owed hours this month and then least
overtime this year; the manager offers it to any of them; the first to accept takes it, judged again at that moment, and her
acceptance becomes a pinned cell of origin `cover` in a new roster version, in force at once (ADR 0005).

Two choices a reader will question:

- **The manager does not choose among acceptors.** A sick call cannot wait for a second round; the manager chose by ticking
  who may accept, and the ranking put the fairest first. Letting the manager pick afterwards would make every acceptance
  provisional and add a step to the one flow that is always urgent.
- **A cover only adds a nurse; it never takes one off.** It is not a swap with an empty side: it is about the shift-day, not
  the absent nurse's cell, so the taker is tied to no colleague's leave, and two absences on one shift-day are two covers. A
  shift-day that needs a different nurse rather than one more (at its maximum headcount with no team leader) lists nobody,
  and the manager edits the roster.

## Considered options

- **A cover as a swap proposed by the manager** (the absent nurse's cell to a colleague): one lifecycle fewer, but the taker's
  cell would name whose leave made it short, which no nurse may learn, and a swap needs every colleague's acceptance where a
  cover needs one.
- **Re-plan only:** the solver fills the shift fairly, but moves other cells too, and the manager cannot ask anyone first.

## Consequences

- A new version that puts one more nurse on a cover's shift-day, whatever made it, ends one waiting cover of that shift-day as
  filled, and an acceptance while a re-plan runs makes the re-plan end outdated, as a swap's approval does.
- A cover's pin is read by the month close like any pin; a cover still waiting when its date has passed has expired.
