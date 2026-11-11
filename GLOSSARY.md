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
A user's roster identity: her hospital ID, her unit, her rostering attributes (gender, team leader, score, allowed shifts, Ramadan-reduced, breastfeeding), her skills, certificates and licences, and her probation (whether she is on one, the CNO's; its length and an early end, her unit manager's; its last day derived from them and her start date). Her username is her hospital ID. The CNO sets and corrects her gender; the CNO and the Deputy CNO record her skills, certificates and licences; her unit manager sets the rest. The CNO and the Deputy CNO read them; the System Admin never does, and nor do nurses, but for two exceptions: the request form offers a nurse only the shifts she may work, so she can see her own allowed shifts, and she reads her own skills, certificates and licences with their identifiers and expiries, since they are hers to renew; nothing else of her attributes.
_Avoid_: staff record, employee record, nurse record

**Start date**, **End date**:
The first and (optional) last day a nurse is part of her unit. Days outside them count like leave: nothing owed, nothing worked, no debt.
_Avoid_: hire date, joining date, termination date

**Transfer**:
A nurse's move to another unit, effective from a chosen month. Until that month begins the nurse belongs where they are.
_Avoid_: move, reassignment, secondment

**Placement**:
From a given month on, the unit a nurse belongs to and the shifts she may work there. The latest that has begun is in force; a later one is a transfer still to come.
_Avoid_: assignment, membership record

**Probation**:
A newly hired nurse's first months, counted in whole calendar months from her start date: one to three as her unit manager sets, extended to six at most. It ends on a month's last day, by itself or earlier by her unit manager, and follows her across a transfer.
_Avoid_: orientation, trial period, preceptorship

**Nurse on probation**:
A nurse during her probation. She works day shifts only, beside her preceptor on the days her preceptor works one, with no overtime beyond rounding her hours up to a whole shift, and counts toward nothing about a shift: a shift is fully staffed without her.
_Avoid_: trainee, orientee, preceptee, new hire, probationer; and "regular nurse" for one whose probation is over

**Preceptor**:
The nurse of her unit a nurse on probation works beside, one nurse on probation at a time. She holds a skill the catalogue marks as letting a nurse precept.
_Avoid_: mentor, trainer, buddy

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
The hospital IT role. Creates the accounts of the CNO, the Deputy CNO and the unit managers and corrects the names on them (accounts only: never units, assignments or nurses, though deactivating a unit manager takes them off their unit), sets the technical limits (such as the time limit cap), and sees the audit log, the solve history, the health page and the backups. Sees no roster.
_Avoid_: admin, superuser, IT

**CNO**:
The Chief Nursing Officer, exactly one per hospital. Owns the hospital rules, the shift catalogue, the skill catalogue, the leave types, the public holidays and the Ramadan dates; creates the units and assigns each its unit manager; adds nurses and corrects their genders and start dates, records their skills, certificates and licences, and corrects the names of staff nurses; and may approve or reject submitted rosters like the Deputy CNO.
_Avoid_: nursing director, matron

**Deputy CNO**:
Approves or rejects submitted rosters, and records nurses' skills, certificates and licences beside the CNO. Exactly one per hospital.
_Avoid_: assistant CNO

**Unit Manager**:
Runs the one unit the CNO assigned to the account, one per unit, and a unit waits with none until the CNO assigns one: its unit rules, its nurses' rostering attributes, its request windows, its solves, its drafts, its swaps and every change to its approved roster.
_Avoid_: head nurse, charge nurse, supervisor

**Staff Nurse**:
A nurse's role. Sees her unit's approved roster, makes requests and preferences during a request window, proposes swaps and reads her own skills with their expiries.
_Avoid_: nurse user, regular nurse

**Password sheet**:
The generated passwords of the nurses a confirmed import just added, shown once, for the CNO to print or copy.
_Avoid_: credentials file, password list

**Lockout**:
A username refused every login for fifteen minutes after five failed logins in a row, whether or not an account has it. Even the right password is refused meanwhile.
_Avoid_: account lock, ban, blocked account

**Throttle**:
A client address refused every login for the rest of a fifteen-minute window after too many failed logins from it, whatever username is tried. Everyone behind that address shares it.
_Avoid_: rate limit, IP ban, block

**Staff list**:
The CSV the CNO exports of every nurse: their hospital ID, full name, gender, unit, dates, role and status, and any transfer to come.
_Avoid_: nurse export, roster, employee list

### Rosters

**Roster**:
A unit's plan for one month: for every nurse and every date, the shift she works or that she is off.
_Avoid_: schedule, rota, timetable, plan

**Draft**:
A roster the unit manager is still shaping. It may be regenerated or edited freely and nobody outside the unit's management sees it.
_Avoid_: working copy, proposal

**Submitted**:
A draft sent to the Deputy CNO, or the CNO, for a decision. Nothing changes it until they decide.
_Avoid_: pending, under review

**Approved**:
The roster in force for its unit and month: the one staff nurses see. Changes to it during the month are the unit manager's alone and need no further approval.
_Avoid_: published, final, live, released

**Rejected**:
A submitted roster the Deputy CNO or the CNO sent back, with a comment for the unit manager. It returns to draft.
_Avoid_: declined, returned

**Roster version**:
One saved state of a unit's approved roster for a month, with who changed it, when and why. The latest is the one in force. Approval makes the first; each change after it, a manager's edit, leave recorded on a worked day, a re-plan, an accepted request or an approved swap, makes the next. Only the unit's manager, the CNO and the Deputy CNO read why.
_Avoid_: revision, snapshot, copy

**Re-plan**:
Solving an approved month again from a chosen date, today or later, keeping every earlier day as a fact: the roster in force, recorded leave and pins. Its roster becomes the next roster version, unless the roster in force or the month's facts changed while it ran.
_Avoid_: re-solve, re-run, regenerate

**Pinned cell**:
A nurse's shift (or day off) on one date fixed as a fact, by the unit manager, by an accepted request or by an accepted swap; the solver may not change it, and every solve keeps it. Leave wins over one. A pin that no longer fits the nurse's dates, leave, unit or shifts, or a shift on a day an expired required skill keeps her off, is set aside and counts for nothing until it fits again.
_Avoid_: locked cell, fixed cell, override

**Leave**:
A date a nurse is off for a recorded reason (sick, annual, educational, and so on), entered by the manager of the unit that month falls under. It counts as worked for her hours. Only she, that manager, the CNO and the Deputy CNO see its reason; to her colleagues, and in every roster file or printout, it is a day off.
_Avoid_: absence, day off, vacation

**Leave type**:
The recorded reason for a leave (sick, annual, educational, and so on), from a list the CNO keeps. Every type counts the same for a nurse's hours.
_Avoid_: absence type, leave category

**Day view**:
One date across every unit, for the CNO and the Deputy CNO: each unit's headcount on each shift against its range, its team leader and gender requirements met or not where it has them, who is on leave and the month's overtime, all from the roster in force, checked on the month as it stands with the solver's own code. A unit whose month has no roster in force shows its state alone; a date in a closed month shows the close's facts. Read-only; it floats nobody.
_Avoid_: dashboard, staffing board, bed board, daily board

### Requests

**Request**:
A nurse's wish about one date of a coming month, made during a request window and accepted or rejected by her unit manager: either a day off or a specific shift. Accepted, it is a promise the roster keeps, as a pinned cell; rejected, withdrawn, cancelled, replaced by leave recorded on its date, or expired because its month closed before a decision, it stays on record and never reaches the solver. Only she and her unit manager read it and its reasons.
_Avoid_: solve request, wish, day request

**Preference**:
A nurse's wish about one date of a coming month, made during a request window beside her requests: a day off, or a working day of any shift. Nobody decides it and it is never a pin; the solver keeps it at a price, the soft rule's weight, doubled for a nurse one of whose preferences the month before did not keep. A date holds one wish, a request or a preference; while the window is open she may withdraw one or ask for it as a request instead. The unit caps how many a nurse makes a month. Only she and her unit manager read them.
_Avoid_: wish, soft request, desired day, undesired day

**Kept**:
What a preference is once the roster in force gives the nurse what she preferred on its date, however that roster came about; otherwise it is not kept. One on a date she is on leave is neither.
_Avoid_: honoured, satisfied, granted

**Request window**:
The days, from an open date to a close date on the hospital's clock, that a unit manager opens for the unit's nurses to make requests and preferences for one target month. A unit has at most one waiting to open or open at a time.
_Avoid_: request period, submission window

**Swap**:
A nurse's proposal to change a set of cells on her unit's approved roster: her own and those of any colleagues needed to make the change work. It needs every involved colleague's acceptance, then the unit manager's; approved, it becomes pinned cells in a new roster version. It expires when one of its dates passes or a new version changes one of its cells. Its proposer may withdraw it while it waits; five withdrawn on one roster in a day stop her proposing there until the first is a day old. A refusal tells the proposer nothing of a colleague that My roster would not show. Rejected, withdrawn or expired, it stays on record.
_Avoid_: exchange, trade, shift change

**Cover**:
One more nurse needed on one shift on one date of the roster in force, which the unit manager offers to the staff nurses who could take it without breaking a hard rule, ranked by who stands furthest below her owed hours this month, then least overtime this year. Leave that takes a shift off the roster in force opens one by itself, unoffered; the manager may open one by hand for any shift-day today or later. The first nurse to accept takes it, and her acceptance is a pinned cell in a new roster version. A cover is about the shift-day, never about whose absence made it short: a nurse offered one reads the date, the shift and the manager's note, and nothing of why or of who else was asked. One not taken expires when its date passes.
_Avoid_: sick call, replacement, fill-in, open shift, extra shift, cover request

**Notification**:
Something a user is told in the application, about a roster's submit, approval, rejection or change, a solve's end, a
request window opening or closing, a decision on a request, and each step of a swap and of a cover. Each user reads only their own. It says nothing of a nurse's leave, and a
rejection's comment stays on the roster.
_Avoid_: alert, message, notice

**Push subscription**:
A device's standing permission to be sent pushes for one user, held as the address the browser's push service gave it and the keys that go with it. It belongs to whoever last turned pushes on there, and a user holds at most ten; turning them off, pressing Log out, a deactivation, an address the push service says is gone, ten failed sends in a row, or the same user turning pushes on for an eleventh device (which ends their earliest) ends it.
_Avoid_: device token, endpoint, device

**Push**:
One message sent to a push subscription, through the browser's push service, saying only which kind of thing waits for the user (a swap to answer, requests open, a roster to approve) and nothing else: never a name, a date or a unit. Only a notification with a deadline is pushed; the rest stay on the bell. Tapping it opens the kind's page.
_Avoid_: push notification, alert

### Solving

**Solve**:
One run of the solver on one solve input, producing one result.
_Avoid_: run, job, generation

**Solve input**:
Everything the solver needs for one unit and one month: the hospital rules, the unit rules, the nurses with their carry-over, leave, preferences, accepted requests and pinned cells, and the time limit.
_Avoid_: request, request JSON, problem, payload

**Result**:
What a solve returns: the roster, the hard rules it breaks, its cost, each nurse's hours accounting and each nurse's carry-over.
_Avoid_: solution, output

**Carry-over**:
The per-nurse values one month hands to the next: hours owed or worked ahead, fairness balances, overtime so far this year, her recent shift history, and how many of her preferences the month did not keep.
_Avoid_: balance, state, history

**Opening values**:
A nurse's carry-over as of the day she is added: overtime this year, hours owed or worked ahead, and her fairness balances. Entered by the unit manager, editable until her first month closes.
_Avoid_: initial balances, starting values

**Projected carry-over**:
The carry-over computed from a month's roster in force before that month has closed. It is what the next month's solve starts from.
_Avoid_: estimate, provisional balance

**Month close**:
Recording what really happened in a month that has ended and computing its carry-over from that record and the previous month's closed carry-over. The close may be redone while the following month is still open; once that month has closed too, the month is fixed for good.
_Avoid_: month-end reconciliation, closing, finalisation

**Solve history**:
Every solve a unit has run, each with its solve input and result, kept for good.
_Avoid_: job history, run log

**Failure kind**:
Why a failed solve gave no answer, as one of a few fixed kinds (the solver unreachable, restarted and lost the solve, run past
the time limit, refusing the solve input, and the like), each read in fixed words naming no one. It is all the System Admin reads
of why a solve failed: the solver's and the worker's own words can name a nurse and a date.
_Avoid_: error, reason, cause

**Time limit**:
How long a solve may search. The unit manager chooses it, up to the time limit cap.
_Avoid_: timeout, budget ("budget" names only a push job's 30 seconds of sending, never a solve's time limit)

**Time limit cap**:
The longest time limit the System Admin allows any solve.
_Avoid_: max time limit, limit

### Rules

**Hospital rules**:
The rules every unit rosters by: the shift catalogue, the skill catalogue, hours per day, Ramadan and breastfeeding reductions, weekend days, forbidden successions, overtime caps and the weights.
_Avoid_: general rules, general settings, global settings

**Unit rules**:
The rules of one unit: its shifts, headcounts, team leader and gender requirements, skill needs, score targets, rest and run limits, fairness limits, and the request and preference caps.
_Avoid_: department rules, department settings, unit settings

**Shift**:
A named working period with a length in hours, defined in the hospital's shift catalogue. A unit works a subset of the catalogue.
_Avoid_: duty, slot

**Run**:
A stretch of a nurse's consecutive worked days, with a day off on each side. The unit's longest run bounds how long one may be.
_Avoid_: block, stretch, cycle

**Full run**:
A run as long as the unit's longest run allows: three in a row where the longest run is three.
_Avoid_: long run, maximum run

**Overtime share**:
The part of a unit's overtime in a month that falls to one nurse, in proportion to the hours she owes that month. How far her overtime has stood above or below it so far this year is one of her fairness balances.
_Avoid_: overtime quota, overtime average, overtime target

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

**Allowed shifts**:
The only shifts of her unit a nurse may work, or none named for any it works, now or later. They belong to her placement, because they mean something only in a unit.
_Avoid_: permitted shifts, eligible shifts

**Team leader**:
A nurse who may lead a shift. A unit may require one on every shift.
_Avoid_: in-charge, senior

**Skill**:
An entry of the hospital's skill catalogue, which the CNO keeps, that a nurse may hold and a skill need may count. Each is of one kind, said in the catalogue: a skill in the plain sense (an ability: triage, IV cannulation), a certificate or a licence; "skill" names both the whole catalogue's entries and the plain kind, as "unit rules" names a set and a page. Whether it expires, whether it is required to work, and whether it lets a nurse precept, is said there too, and so is the body that issues it. The CNO and the Deputy CNO record what a nurse holds.
_Avoid_: credential, competency, qualification

**Certificate**:
A skill of the kind that attests something a nurse has done or earned, from a body the catalogue names (a university, a training provider): a degree, a diploma, a course certificate. Held for good unless the catalogue says it expires. A nurse's record of one carries its identifier and its issue date.
_Avoid_: certification, qualification, diploma (as the kind's name), degree (as the kind's name)

**Licence**:
A skill of the kind that permits a nurse to practise, from a body the catalogue names (the Saudi Commission for Health Specialties), renewed on a date: the kind the catalogue says expires and is usually required to work. A nurse's record of one carries its identifier, its issue date and its expiry.
_Avoid_: license, registration, permit, licence check

**Identifier**:
The number or code a body gave a nurse's certificate or licence. Recorded with it, unique among the current records of one catalogue entry, read by the CNO, the Deputy CNO and the nurse herself, and in no file, notification or audit entry.
_Avoid_: licence number, certificate number, ID (which the hospital ID is), serial

**Expiry**:
The last day a nurse's skill counts; every skill of a kind the catalogue says expires has one. From the next day the skill is expired: it counts toward no skill need and, if required to work, keeps her off every shift.
_Avoid_: expiration date, valid until, renewal date, lapsed

**Required to work**:
A mark on a skill in the catalogue: a nurse who holds one that has expired works no shift that day. Her hours stay owed, as for any nurse whose days cannot hold them. A nurse with no record of it is rostered as before, and the gap is listed for the CNO to fill.
_Avoid_: mandatory credential, blocking credential, licence check

**Skill need**:
A unit rule: on a shift the unit works, at least so many nurses holding a skill each weekday and each weekend day, counting nurses on exactly that shift. Hard or soft by the unit's choice, as night rest is; the price when soft is the skill shortfall weight.
_Avoid_: skill requirement, skill coverage, skill mix, competency mix

**Ramadan days**:
The dates of a month on which a Ramadan-reduced nurse owes fewer hours. Derived from the Umm al-Qura calendar unless the CNO fixes them after the moon sighting.
_Avoid_: fasting days

### Operations

**Backup**:
A copy of the whole database but who is signed in, taken by the worker every night at the System Admin's backup time and kept
for their number of days. Only the System Admin sees and downloads one, since it holds every account and every nurse's leave.
_Avoid_: dump, snapshot, export

**Restore**:
Putting a backup in place of the database, by a script on the server, never from the application. Everything done since the
backup is lost, so the database as it stood is backed up first. No lockout or throttle comes back with it, and the
deactivations, password resets and changes and push key rotations it undid are listed, to be done again by hand.
_Avoid_: rollback, recovery
