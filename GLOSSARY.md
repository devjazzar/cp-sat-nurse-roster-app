# Nurse Rostering

One installation serves one hospital: its units, their nurses, the rules they roster by, and
the monthly rosters the solver produces and the hospital approves.

## Language

### Organisation and people

**Hospital**:
The single organisation an installation serves. There is never more than one per installation.
_Avoid_: tenant, site, customer

**Unit**:
A nursing unit with its own staff, its own rules and its own rosters. A nurse belongs to exactly one unit and is never rostered on another.
_Avoid_: department, ward

**Nurse**:
A user who appears on a unit's rosters: any user with a nurse profile. Every staff nurse is one; a unit manager may be.
_Avoid_: staff, employee, staff member

**Nurse profile**:
A user's roster identity: her hospital ID, her unit and her rostering attributes (gender, team leader, score, allowed shifts, Ramadan-reduced, breastfeeding). Her username is her hospital ID.
_Avoid_: staff record, employee record, nurse record

**Start date**, **End date**:
The first and (optional) last day a nurse is part of her unit. Days outside them count like leave: nothing owed, nothing worked, no debt.
_Avoid_: hire date, joining date, termination date

**Hospital ID**:
The hospital's own identifier for a nurse. It is her username and the name she carries on every roster.
_Avoid_: employee number, badge number, staff number

**User**:
A login. Every user has exactly one role.
_Avoid_: account, login

**Role**:
What a user may see and do. One of: System Admin, CNO, Deputy CNO, Unit Manager, Staff Nurse.
_Avoid_: permission level, access level, user type

**System Admin**:
The hospital IT role. Creates the accounts of the CNO, the Deputy CNO and the unit managers (accounts only: never units, assignments or nurses), sets the technical limits (such as the time limit cap), and sees the audit log, the solve history, the health page and the backups. Sees no roster.
_Avoid_: admin, superuser, IT

**CNO**:
The Chief Nursing Officer, exactly one per hospital. Owns the hospital rules, the shift catalogue, the leave types, the public holidays and the Ramadan dates; creates the units and assigns each its unit manager; adds nurses; and may approve or reject submitted rosters like the Deputy CNO.
_Avoid_: nursing director, matron

**Deputy CNO**:
Approves or rejects submitted rosters. Exactly one per hospital.
_Avoid_: assistant CNO

**Unit Manager**:
Runs the one unit the CNO assigned to the account, exactly one per unit: its unit rules, its nurses' rostering attributes, its request windows, its solves, its drafts, its swaps and every change to its approved roster.
_Avoid_: head nurse, charge nurse, supervisor

**Staff Nurse**:
A nurse's role. Sees her unit's approved roster, makes requests during a request window and proposes swaps.
_Avoid_: nurse user, regular nurse

### Rosters

**Roster**:
A unit's plan for one month: for every nurse and every date, the shift she works or that she is off.
_Avoid_: schedule, rota, timetable, plan

**Draft**:
A roster the unit manager is still shaping. It may be regenerated or edited freely and nobody outside the unit's management sees it.
_Avoid_: working copy, proposal

**Submitted**:
A draft sent to the Deputy CNO for a decision.
_Avoid_: pending, under review

**Approved**:
The roster in force for its unit and month: the one staff nurses see. Changes to it during the month are the unit manager's alone and need no further approval.
_Avoid_: published, final, live, released

**Rejected**:
A submitted roster the Deputy CNO sent back, with a comment. It returns to draft.
_Avoid_: declined, returned

**Roster version**:
One saved state of a unit's roster for a month, with who changed it, when and why. The latest approved version is the one in force.
_Avoid_: revision, snapshot, copy

**Re-plan**:
Solving a month that has started again from a chosen date, keeping every earlier day as a fact.
_Avoid_: re-solve, re-run, regenerate

**Pinned cell**:
A nurse's shift (or day off) on one date fixed as a fact, by the unit manager, by an accepted request or by an accepted swap; the solver may not change it.
_Avoid_: locked cell, fixed cell, override

**Leave**:
A date a nurse is off for a recorded reason (sick, annual, educational, and so on), entered by the unit manager. It counts as worked for her hours.
_Avoid_: absence, day off, vacation

**Leave type**:
The recorded reason for a leave (sick, annual, educational, and so on), from a list the CNO keeps. Every type counts the same for a nurse's hours.
_Avoid_: absence type, leave category

### Requests

**Request**:
A nurse's wish about one date of a coming month, made during a request window and accepted or rejected by her unit manager: either a day off or a specific shift. Accepted, it is a promise the roster keeps; rejected, it stays on record and never reaches the solver.
_Avoid_: solve request, preference, wish, day request

**Request window**:
The period, from an open date to a close date, that a unit manager opens for the unit's nurses to make requests for one target month. A unit has at most one open at a time.
_Avoid_: request period, submission window

**Swap**:
A nurse's proposal to change a set of cells on her unit's approved roster: her own and those of any colleagues needed to make the change work. It needs every involved colleague's acceptance, then the unit manager's; accepted, it becomes pinned cells. A rejected swap stays on record.
_Avoid_: exchange, trade, shift change, cover

### Solving

**Solve**:
One run of the solver on one solve input, producing one result.
_Avoid_: run, job, generation

**Solve input**:
Everything the solver needs for one unit and one month: the hospital rules, the unit rules, the nurses with their carry-over, leave, accepted requests and pinned cells, and the time limit.
_Avoid_: request, request JSON, problem, payload

**Result**:
What a solve returns: the roster, the hard rules it breaks, its cost, each nurse's hours accounting and each nurse's carry-over.
_Avoid_: solution, output

**Carry-over**:
The per-nurse values one month hands to the next: hours owed or worked ahead, fairness balances, overtime so far this year, and her recent shift history.
_Avoid_: balance, state, history

**Opening values**:
A nurse's carry-over as of the day she is added: overtime this year, hours owed or worked ahead, and her fairness balances. Entered by the unit manager, editable until her first month closes.
_Avoid_: initial balances, starting values

**Projected carry-over**:
The carry-over computed from a month's roster in force before that month has closed. It is what the next month's solve starts from.
_Avoid_: estimate, provisional balance

**Month close**:
Recording what really happened in a month that has ended and computing its carry-over from that record and the previous month's closed carry-over. The close may be redone while the following month is still open.
_Avoid_: month-end reconciliation, closing, finalisation

**Solve history**:
Every solve a unit has run, each with its solve input and result, kept for good.
_Avoid_: job history, run log

**Time limit**:
How long a solve may search. The unit manager chooses it, up to the time limit cap.
_Avoid_: timeout, budget

**Time limit cap**:
The longest time limit the System Admin allows any solve.
_Avoid_: max time limit, limit

### Rules

**Hospital rules**:
The rules every unit rosters by: the shift catalogue, hours per day, Ramadan and breastfeeding reductions, weekend days, forbidden successions, overtime caps and the weights.
_Avoid_: general rules, general settings, global settings

**Unit rules**:
The rules of one unit: its shifts, headcounts, team leader and gender requirements, score targets, rest and run limits, fairness and request limits.
_Avoid_: department rules, department settings, unit settings

**Shift**:
A named working period with a length in hours, defined in the hospital's shift catalogue. A unit works a subset of the catalogue.
_Avoid_: duty, slot

**Hard rule**:
A rule a roster must satisfy. The solver returns no roster that breaks one.
_Avoid_: constraint, mandatory rule

**Soft rule**:
A rule the solver may break at a price. Its weight is that price.
_Avoid_: preference, penalty rule, objective

**Weight**:
The price of breaking a soft rule once. Zero switches the rule off.
_Avoid_: penalty, priority, cost factor

**Violation**:
A hard rule a roster breaks.
_Avoid_: error, conflict, infeasibility

**Score**:
A nurse's performance score, from 0 to 1, which the solver uses to balance the strength of shifts.
_Avoid_: rating, grade, competency

**Team leader**:
A nurse who may lead a shift. A unit may require one on every shift.
_Avoid_: in-charge, senior

**Ramadan days**:
The dates of a month on which a Ramadan-reduced nurse owes fewer hours. Derived from the Umm al-Qura calendar unless the CNO fixes them after the moon sighting.
_Avoid_: fasting days
