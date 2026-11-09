---
status: accepted
date: 2026-11-09
---
# A nurse on probation is rostered by the solver, beside her preceptor, and counts toward nothing about a shift

A newly hired nurse spends her first months on *probation*: she works day shifts only, beside a *preceptor* of her unit, and
a shift must be fully staffed without her. Until now every nurse in a solve input counted toward everything: headcounts, the
team leader and both-genders rules, score targets, skill needs and the fairness figures.

The solver rosters her itself. Its contract gains, per nurse, that she is on probation and who her preceptor is. For such a
nurse the model leaves her out of every count about a shift and out of the unit's fairness figures; forbids her the night
shift; makes her work the same shift on the days her preceptor works a day shift, as a hard rule; and places her remaining
day shifts freely, under her own rest and run rules, to fill the hours she owes. She works at most the fewest whole shifts
that cover those hours, so her overtime in a month is always less than one shift's length. When her preceptor's day shifts
are more than her hours hold, the hours win: she follows as many as they hold, the solver chooses which, and she works no
day shift apart from her preceptor's while one of her preceptor's is still free to follow. A nurse on probation with no
preceptor is rostered the same way with nothing to follow, and the solve warns of it.

## Considered options

- **Copy the preceptor's cells onto her row in the app**, after each solve, and keep her out of the solve input. Rejected:
  on the days her preceptor works nights, is off or is on leave her shifts must still be planned, under her own rest and run
  rules and her own hours, which is the solver's work; and every later change to the preceptor's row (an edit, a swap, a
  re-plan) would need the copy made again by code that knows none of the rules.
- **Pin her cells from the preceptor's**, as an accepted request is pinned (ADR 0005). Rejected for the same reason, and a
  pin would be judged against headcounts she must not count toward.
- **Count her at a fraction.** Rejected: a shift must be safe without her, so she counts toward nothing.
- **Make the preceptor work days while she precepts.** Rejected: the preceptor is rostered exactly as before, nights
  included, so a unit's night cover does not depend on who is precepting.

## Consequences

- The following rule is a hard rule like any other: a swap or a cover that would break it is refused, the manager's own
  edit shows it as a violation, and a re-plan keeps her beside her preceptor.
- She takes no part in swaps, is never offered a cover, and takes no part in the unit's overtime share. Requests and
  preferences are hers as any staff nurse's, and an accepted day off holds over following her preceptor.
- Her night and weekend fairness balances stay at zero through probation, so she starts level when it ends. Her hours debt
  and her overtime for the year carry as for any nurse.
- An end or an extension takes effect from a month's first day. A roster already approved for that month stays as it is
  until the manager re-plans it.
- A solve input stored before this has no nurse on probation, and gives what it gave.
