---
status: accepted
date: 2026-11-07
---
# A preference is a priced wish, never a pin; a nurse whose preference last month was not kept pays double this month

Every request a nurse makes today becomes a pinned cell when accepted (ADR 0005), so the unit caps them at a few a month and
the manager decides each one. The solver has always had two soft inputs the app never filled, a day asked off and a day
asked to work, priced by the hospital-wide weights `undesired_day` and `desired_day`. The app now fills them from
*preferences*: wishes a nurse makes in the same request window, a day off or a working day of any shift, that nobody decides,
that the solver keeps when it can at the weight's price, and that never become a pin. The manager reads them and the cost
each solve paid for them, and decides nothing.

So that self-scheduling feels fair over time, every preference of a nurse costs twice the weight in a month that follows one
in which the roster in force did not keep at least one of hers. The vendored solver's contract changes for this (its first
change since ADR 0002, in this repository): the input gains a per-nurse count of preferences the month before did not keep,
the model doubles that nurse's two weights when it is above zero, and the result's `carry_over` block computes the count from
the month's facts, so the carry-over chain (ADR 0004) projects it from the roster in force and corrects it at the close like
the fairness balances. It remembers one month only, so January does not reset it, and a month with no roster for her hands
on zero.

## Considered options

- **A multiplier by the count broken**, so that the most wronged nurse comes first. Rejected: a nurse who marks the month
  off is "broken" every month and grows her own price without limit. Doubling, whatever the count, cannot be grown.
- **No cap**, as first asked. Rejected for the same reason: uncapped, the heaviest user holds a doubled price for good at
  the expense of modest colleagues. Each unit caps preferences a nurse a month, beside its request cap (default 10; 0
  switches them off).
- **A preferred shift on a day.** The solver prices a day, not a shift; a third soft rule would be a larger change to the
  contract. A specific shift stays a request.
- **Pricing in the app without a solver change**, by listing a day twice. The solver refuses a repeated day, by design.

## Consequences

- A preference's price is the CNO's two weights, hospital-wide like every weight; the unit rules page exposes no weight.
- A date holds one wish, a request or a preference. While the window is open a nurse may turn a preference into a request,
  under the request cap. Leave over a preference leaves it on record, counted neither kept nor broken.
- My month shows the nurse how many of her preferences the roster in force kept, and that hers count double this month when
  they do. Whether one was kept is read from the roster in force, so a manager's edit or a re-plan that breaks one counts.
- The solver's schema version moves to 4, and its suite and contract tests with it.
