# 55: Probation: the preceptor, and the solve

**What to build:** The unit manager assigns a nurse on probation her preceptor from a chosen month on, on her row of the Rostering attributes page, and may change it: the list offers only nurses of the unit who hold a skill marked "Lets a nurse precept" that has not expired on the day of assigning, are not on probation in those months, and precept no other nurse in any of them; the current month can be chosen only while its roster is not approved. The assignment ends with the probation, with the preceptor's last month in the unit (a transfer or an end date, and the manager is notified to choose another) and with the nurse on probation's own transfer; a skill that expires later ends nothing. Both nurses are notified when a preceptor is assigned or changed. From here on the roster follows: every solve input, a re-plan's and a close's included, marks each nurse on probation in that month and names her preceptor, so the solver (ticket 52) rosters her on day shifts beside her preceptor and counts her toward nothing; a nurse on probation with no preceptor is still rostered, and the solve's warnings name her. On an approved roster a swap or a cover that would break the following rule is refused, she can neither propose a swap nor be part of one, she is never offered a cover, and every headcount the application works out itself leaves her out. Spec: `.scratch/nurse-rostering-v2/specs/probation.md`; the words: `GLOSSARY.md` (Preceptor, Nurse on probation); the reasons: ADR 0014.

**Blocked by:** 52 The solver rosters a nurse on probation; 53 The skill catalogue's "Lets a nurse precept" mark; 54 Probation on a nurse: the tick, the length and the end

**Status:** ready-for-agent

- [x] A preceptor assignment: from a month on, which nurse precepts her; the latest that has begun is in force, as a placement is; a manager with a nurse profile may be the preceptor
- [x] Assigning and changing on the Rostering attributes row, behind its question, with each refusal said: another unit in that month, no marked skill unexpired today, on probation in those months, already precepting in any of them, a month whose roster is approved
- [x] The assignment ends with the probation (ended, extended or run out), with the preceptor's transfer or end date (the manager notified to choose another), and with the nurse on probation's own transfer; a preceptor's skill expiring later ends nothing
- [x] Notifications to both nurses when a preceptor is assigned or changed, once each
- [x] The solve input, a re-plan's and a close's included, marks her on probation month by month across a probation's start and end, and names her preceptor when one is in force and in the input; a stored input without the fields still reproduces; "changes since" reports a changed probation or preceptor
- [x] An end, an extension or an unticking that touches a month whose roster is approved changes nothing in it; the roster page says how it was planned and offers the re-plan
- [x] A real solve on a scratch stack: she is beside her preceptor on every day shift her hours hold, works no night, every headcount is met without her, and the draft's per-nurse explanation says which of her preceptor's day shifts she did not follow; with no preceptor the solve's warnings name her
- [x] Swaps: she cannot propose one or be a colleague in one, and is told why; a swap that takes her preceptor off a followed day shift is refused, the proposer told only what My roster would show. Covers: she is never listed or offered; one that would break the rule is refused. A manager's edit shows the violation; a re-plan keeps her beside her preceptor
- [x] The headcounts the application works out itself (the approved roster's judging, the cover list, the Day view if it is built) leave her out, with the solver's own reading
- [x] Requests and preferences are hers as any staff nurse's; the request form offers her allowed day shifts only; an accepted day off holds over following
- [x] Audit entries for each assignment and its end, with their values
- [x] Tests at the web API seam (each refusal, the endings, the notifications, the solve input month by month, a swap and a cover refused, her absence from the cover list, a few end to end with the real solver in process) and the frontend app-level suite (the row's preceptor control, the swap page's explanation); six runs at once
- [x] `docs/ARCHITECTURE.md` names the assignment in the domain model, the fields in the solve input, the notifications and the swap and cover rules; the OpenAPI document and the generated client regenerated; the migration

## Comments

**From ticket 53 (2026-11-11), the mark this ticket reads.** `hospital.models.Skill.lets_a_nurse_precept` (API field
`lets_a_nurse_precept` on `listSkills`). A nurse qualifies through her current records, `NurseSkill.objects.current()`,
of a skill with the mark on, unexpired on the day of assigning; read `expiry` only when the skill's `expires` is on (ticket
33's rule), and decide whether a retired marked skill still qualifies (the spec does not say). The mark is read when
assigning only: clearing it is never refused and must end no assignment, and the Skills page tells every role so.
`hospital/tests/test_skills.py::test_the_mark_is_cleared_while_a_nurse_holds_the_skill` is the place to extend once a
preceptor exists: clear the mark on a skill someone precepts by, and the assignment stands.

**From ticket 54 (2026-11-11).** A nurse's probation is on her profile and read only through `backend/nurses/probation.py`:
- **The solve input, month by month:** `probation.on_probation_in(nurse, month)` says whether she is on probation in a month (from her start date's month to her probation's last day). Every other reader (the rows, the staff list, the night refusal, the hourly notification) goes through `last_day` and `running`.
- **The fields:** `on_probation` is the CNO's tick. `probation_months` is 1 to 6. `probation_ended_in` is a month whose last day became the probation's: her unit manager's End, or the CNO's untick, which keeps the months up to the last one whose roster (in the unit that month falls under) is approved. So `on_probation` false with `probation_ended_in` set is a probation kept for approved months. `probation_notified_for` is the last month her unit manager was told of.
- **Approved months:** an End, an extension or an untick that touches an approved month changes no roster here. The roster page's line and the re-plan offer are yours ("changes since" included).
- **Not refused here, and yours to decide:** the CNO's tick and her unit manager's allowed-shifts save both refuse the night shift alone. But a unit narrowing its shifts (`membership.narrow_allowed_shifts`) or a transfer carrying a list can still leave a nurse on probation with only the night shift. The solver's narrowing would then leave her no shift. `stranded_by` is the place to add it.
- **Audit:** `nurse.probation_ticked`, `nurse.probation_unticked`, `nurse.probation_length_set`, `nurse.probation_extended` and `nurse.probation_ended` carry `probation.describe(nurse)` before and after (the user's decision, 2026-11-11). An assignment's entries can follow the same shape.
- **Notifications:** `Event.PROBATION_ENDING` names the nurse by her profile's id in the payload, with her last month as `month`. The `Notification` docstring now allows that; a preceptor assignment's notifications can name nurses the same way.

**From ticket 54's review (2026-11-11):** the user chose to close here the gap ticket 54 left: a unit dropping a shift, or a transfer, can leave a nurse on probation with the unit's night shift alone as her allowed shifts. This ticket makes that impossible or refused, and says how.

**From ticket 52 (2026-11-12), what the solve input must carry:** each nurse in the month gains two optional fields, read in
version 1 or 2: `on_probation` (true for a nurse on probation in that month; absent = false) and `preceptor` (the preceptor's
hospital id, that is her `id` in the same input; absent or null = none). Write `preceptor` only when the assignment is in force in
that month **and** the preceptor is a nurse of that input: the loader refuses an id not in the input, the nurse's own, a
preceptor herself on probation, one named by two nurses, and a preceptor on a nurse not on probation, each as `request:
nurses[i].preceptor: ...`. A nurse on probation with no preceptor is fine: precheck warns ("<id>: on probation with no preceptor,
...") and she is rostered on day shifts. Her `night_balance`, `friday_balance` and `overtime_balance` going in are ignored and
come out of a result's `carry_over` as 0. The solver refuses her allowed shifts if the night shift alone (`problem: <id>: on
probation she works no night shift ('N'), and her allowed shifts hold no other`): the gap above, which the solver now reports
loudly rather than leaving her no shift. The new hard rule is `following`; its violation reads "following: <id> works A on day
3, her preceptor <id> works D" (day indices from 0, the `date` field the date). **The per-nurse explanation:** `solves.result`
keeps only priced soft rules, and a hard rule has no match on a valid roster, so "which of her preceptor's day shifts she did not
follow" has no channel yet: on a draft, her followable days left off are the days her preceptor works a day shift she is allowed
while she is off; that list is yours to work out, or to ask the solver for in a later ticket.

**Implemented on 2026-11-12,** on branch `claude/ticket-55-preceptor-and-solve-999929` (`247eac7` the assignment and the solve
input, `6b16745` its tests, `fab7fc7` the frontend, `5db908a` the docs, `639b000` the OpenAPI fix, `99f9095` and `4df7917` the two
code reviews' points), from `main` at `fca2e29`. Draft pull request
[devjazzar/cp-sat-nurse-roster-app#30](https://github.com/devjazzar/cp-sat-nurse-roster-app/pull/30).
- The backend suite ran on a throwaway PostgreSQL 18 container of my own, under the heavy-run lock: **3541 passed** on `99f9095`.
  The second review's fixes came after it, and the files they touch (all of `nurses/`, `notifications/`, the probation tests of
  `solves/` and `swaps/`, `hospital/tests/test_skills.py`) ran again on `4df7917`: **918 passed**.
- `makemigrations --check`: "No changes detected". Two migrations: `nurses` 0009 (the assignment) and `notifications` 0011 (two
  events).
- The frontend: `npm test` **831 passed**, and `npm run build` was clean. `frontend/openapi.json` and the client were regenerated
  from the export, and orval accepts the document.
- The solver suite did not run: `solver/` did not change.
- No Playwright file changed, and there is no new journey.

**What the dev stack needs:** `docker compose up -d --build`, for the two migrations, which `web` runs at start. There is no new
job, and no `compose.yaml`, `Dockerfile`, solver or dependency change.

**What was built, criterion by criterion.**
- **The assignment** (`nurses.models.PreceptorAssignment`, read only through `nurses.preceptors`).
  - It holds the nurse on probation, her preceptor, the unit, `from_month`, and `until`, set once a nurse's leaving ends it.
  - The latest begun is in force, as a placement is, and only in the months she is on probation (`probation.on_probation_in`).
    So an End, an extension or the end by itself moves it with nothing written.
  - A manager with a nurse profile is offered and may be assigned.
- **Assigning and changing**, on her Rostering attributes row.
  - The button is "Choose preceptor", or "Change preceptor" once she has one. It opens a question with a From month, taken from
    the row's `preceptor_months`, and a Preceptor list.
  - The list holds the nurses the server offers from that month (`GET …/preceptor-choices?month=`). It is read again when the
    month changes, and says why it is empty when it is.
  - The row shows "Preceptor: Amal Hassan, December 2026 to March 2027", or "No preceptor".
  - A choice replaces this unit's choices from that month on. The unit she is due to join chooses there (story 34), and its
    plan stays.
  - Refusals, each said:
    - herself;
    - not a nurse of the unit that month;
    - no marked skill unexpired today;
    - on probation in one of her months from then;
    - already precepting another nurse in one of them;
    - a month that is over;
    - a month outside her probation;
    - a month in which she is in another unit;
    - a month whose roster is approved.
- **Endings.**
  - With the probation: derived. The CNO's untick also ends every assignment for good, so a later tick brings no preceptor back.
  - The preceptor's transfer or end date writes `until`. It is logged, and her unit's manager is told ("January 2027 is Amal
    Hassan's last month in ER, … Choose another preceptor for Layan Alharbi.").
  - Her own transfer: the same, with nobody told.
  - A leaving already recorded when assigning ends it then. An end date's month is still theirs.
  - A skill expiring later, its mark cleared (ticket 53's test, extended), or its record taken off ends nothing.
- **Notifications** (`preceptor_assigned` and `preceptor_leaving`, on the bell only, never pushed).
  - Her: "From January 2027 your preceptor is Amal Hassan. You work beside them on their day shifts."
  - The new preceptor: "From January 2027 you precept Layan Alharbi, a nurse on probation, who works beside you on your day shifts."
  - A preceptor freed by a change, or by an End, a shorter Length or an untick: "From February 2027 you no longer precept Layan
    Alharbi."
  - Once each, from the first month the change makes a difference: choosing the same preceptor again tells and logs nothing.
- **The solve input** (`solves.input._mark_probation`), a re-plan's and a close's included.
  - `on_probation` is written for each nurse on probation that month.
  - `preceptor` is written only when an assignment is in force, its preceptor is in the input and not herself on probation, and
    no other nurse names that preceptor. Of two, the assignment made first keeps the preceptor.
  - So the loader never refuses the input, whatever a later correction does.
  - Neither field is written for anyone else, so a month with nobody on probation is the input it always was.
  - "Changes since" reports `on_probation`, `off_probation` and `preceptor`. The month at a submit keeps both fields.
  - Tested month by month: May, June and July across her probation's end on 30 June.
- **An approved month.** An Extend reaching an approved June changes nothing in it (tested with the real solver in process). Its
  roster page says "Faten Ali: is on probation this month, but it was planned with her counted" under "This roster was solved
  before these changes", where the re-plan is.
- **The real thing**, on scratch stack `nr-t55` (below).
- **Swaps.**
  - She cannot propose: the composer and the propose step both say "You are on probation in June 2026, and a nurse on probation
    takes no part in a swap: you work beside your preceptor, and the roster is planned around that."
  - She is not in a colleague's composer, and a cell of hers is refused: "Faten Ali is on probation in June 2026, so a swap cannot
    change their cells."
  - A swap that breaks the following rule tells the proposer "This swap cannot work on 6 June 2026: Faten Ali is on probation and
    works beside her preceptor, Amal, on their day shifts." The manager reads the solver's own line.
- **Covers and edits.**
  - She is never listed: the exclusion is `on_probation`, and her own words are "…takes no cover: a shift is fully staffed without
    her."
  - A preceptor whose taking a cover would break the rule is not listed either.
  - A manager's edit shows the `following` violation.
  - A night shift for her is refused as a pin, an edit or a request, through a new `Judge` reason, `night_on_probation`.
- **Headcounts the app works out itself**, read as the solver reads them (`row["on_probation"]` from the month's input):
  - the approved roster's checks, which already run on the solver's code;
  - the cover list's "already full";
  - the Day view's counts and its overtime totals. It still lists her on her shift.
- **Requests.** The form offers her allowed day shifts only, in a month she is on probation. An accepted day off holds over
  following (tested with the real solver).
- **Audit.**
  - `nurse.preceptor_assigned`: before `{preceptor, from_month, until}` (and `replaced`, any plans it replaced), after the new one.
  - `nurse.preceptor_ended` for each leaving and untick, before and after.
- **The night-alone gap (ticket 54's review).**
  - A unit's rules that would leave a nurse on probation with the night shift alone are refused (`membership.left_night_alone`):
    "Layan Alharbi (h1) would have only N, the night shift, of these shifts, and a nurse on probation works no night shift.
    Change their allowed shifts first."
  - A transfer that would carry her that list empties it, flagged "To check" for the new unit's manager, as a list with no shift
    in common is.
  - Both are judged by her probation in the placement's months, so a transfer after her probation keeps an N-only list.
  - `stranded_by` is unchanged. The probation check sits beside it as its own function.
- **The explanation of days not followed** (`solves.result.not_followed`, the result's `following`, the panel "Nurses on
  probation").
  - It takes each of her preceptor's day shifts she is allowed and did not work, with the first reason that holds: her leave or a
    day outside her dates, a barred day, a day already over, a pin or an accepted request, or else her own rules ("her hours, or
    her own rest and run rules, held no more").
  - It is read from the stored input and roster with the solver's own `Problem`.
  - With no preceptor: "… had no preceptor this month, so her day shifts were placed freely." The solve's precheck names her
    ("Faten: on probation with no preceptor…").
- **Docs.**
  - `docs/ARCHITECTURE.md`: the roles table (two rows), the Preceptor assignment in the domain model, the Notification entry,
    section 6 (the fields the app writes, "changes since", the explanation, headcounts, the night-alone gap), and the swap and
    cover lifecycles.
  - `GLOSSARY.md`'s Notification entry.

**What was driven, and how.**
- **Setup.** Scratch stack `nr-t55` was seeded by `e2e/stack.sh up`: ER is the four-nurse sample, December 2026 is approved, and
  today is 12 November. In the stack's Django shell, I added Faten Ali on probation from 1 December (December to February) and
  recorded "Preceptorship" (marked) for Amal Saleh.
- **The question.** In the built-in browser as Mona, on Rostering attributes, Faten's row showed Length, Extend and "Choose
  preceptor". The question offered From January or February 2027, not December, whose roster is approved, and only Amal Saleh.
  The save answered "From January 2027, Amal Saleh precepts Faten Ali.", and the row read "Preceptor: Amal Saleh, January 2027 to
  February 2027".
- **The solve.** January was solved for real (30 s), and succeeded with no violation.
  - The input carried `Faten: on_probation true, preceptor Amal`.
  - Faten `D.DDD.DD.D.DD..D....D.DDDD.D.D.` and Amal `N..D..D.NN..N..N.NN.NNN.N.N.NNN`: Faten was beside her on both of Amal's
    day shifts (4th and 7th) and worked no night.
  - The D count without her was exactly 1 every day, the N count 1–2. Faten's hours were 204 of 208, 4 short and carried.
  - The draft's panel said "Faten Ali works beside Amal Saleh, her preceptor, on all 2 day shifts of theirs.", and the fair shares
    leave her out.
- **Ticket 52's review, the preceptor's own roster.** December, approved before Faten existed, had Amal on 1 D and 17 N; January
  had her on 2 D and the rest nights. I saw no pull toward day shifts. One month apart proves nothing either way.
- The stack is down and its volumes removed.

**What was NOT checked.**
- The second review's fixes were not driven on the stack, which ran `99f9095`. They have their tests.
- The full backend suite after `4df7917`: only the files it touches ran.
- Six frontend runs at once, and the browser checks: GitHub's, on the pull request.
- A swap or a cover refused in a browser. They ran at the API seam only, on a roster the real solver made in process.
- Performance on a large unit: `precepted_in` reads each assignment's nurse's rows, once per candidate. That is fine for a unit's
  handful of nurses on probation.

**Decisions taken here.**
- **The ends.** A probation's end is derived. A leaving's end is written and final, so a cancelled transfer brings nothing back
  once the manager was told. The CNO's untick ends it for good.
- **Two nurses naming one preceptor in a month**, which only a later correction can cause: the assignment made first keeps the
  preceptor in the input, and the other is rostered with no one to follow and named by precheck.
- **The "no longer precept" notification** goes on an End, a shorter Length or an untick. One that runs out by itself tells nobody.
- **Notifications are sent at the act, not by the hourly job.** The spec's "sent by the hourly job" fits the clock's own events.
  An assignment and a leaving are acts, and telling at once gives the manager the most time.

**Worth your review.**
- **A retired marked skill does not qualify.** It follows `nurses.skills.tracked`: a retired skill is no record to a solve input
  or the expiries either.
- **How the night-alone gap is closed:** refused on the unit's rules, and emptied ("To check") on a transfer. A transfer is the
  CNO's, who cannot set allowed shifts, so refusing it would leave the CNO with nothing to do.
- **The swap and cover words**, which name her probation and her preceptor on the strength of ticket 56's "On probation" heading
  with her preceptor's name. Until 56 lands, My roster does not show that pairing.
  - "This swap cannot work on 6 June 2026: Faten Ali is on probation and works beside her preceptor, Amal, on their day shifts."
  - "Faten Ali is on probation in June 2026, so a swap cannot change their cells."
  - "You are on probation in June 2026, and a nurse on probation takes no part in a swap: …"
  - "You are on probation in June 2026, and a nurse on probation takes no cover: a shift is fully staffed without her."
- **The explanation's line:**
  - "Faten Ali works beside Amal Saleh, her preceptor, on 6 of their 8 day shifts. Not on:"
  - then each day, "7 June, D: she was on leave or outside her dates" / "her hours, or her own rest and run rules, held no more".
- **Extend and Length are refused** when her preceptor in her last month would go on into a month in which they precept another
  nurse ("Extended, … would reach April 2027, when her preceptor … precepts …. Choose … another preceptor from that month
  first."). The spec refuses no extension; without this, the input would drop one pairing silently.
- **The preceptor's words use they/them**, since a preceptor is any nurse. Her own words keep the glossary's she.

**Review.** `code-review` against `fca2e29`, both axes in fresh sub-agents, then a second run on the fixes, which were more than
small.

*Standards, first run:*
- A choice from an earlier month was a no-op: fixed (`first_gained`).
- The dead notification branch: removed.
- "On leave" covering days outside her dates: reworded.
- The OpenAPI document not regenerated for the month filter: done. GitHub's orval step had refused the earlier one.
- The month rule written twice: now one, `preceptors.month_refusal`.
- `q` and `d` and a local named `probation`: renamed.
- Kept:
  - the swap words, under Worth your review;
  - the ticket-53 test reading `preceptors.assignment_in`: the place ticket 53 named, and it has no API reading of its own;
  - the "leave her out" readings in three places, each one line over the input's `on_probation`;
  - the N+1 in `precepted_in`, small at a unit's scale.

*Spec, first run:*
- A preceptor's or her own recorded leaving now caps an assignment made afterwards.
- The preceptor is told when the probation ends the pairing by an act.
- A nurse already precepting her is not told again.
- Rest and run misses are no longer called "hours".
- The night-alone gap is judged by the placement's months.
- Kept:
  - no audit entry for a probation's derived end: the probation's own entries carry its last day, and running out is no act;
  - the Extend and Length refusal: under Worth your review.

*Second run:*
- A choice no longer deletes the joining unit's plan.
- Re-choosing a preceptor capped by a leaving is no change.
- Her own end date caps it.
- A released preceptor is told under the assignment's unit and month.
- A replaced plan is in the audit entry.
- An untick ends assignments for good.
- Each has a test.

*GitHub's backend job* found the swap scene's real solve gives another June on its machines (the same reproducible settings, a
different roster), and six tests read its rows. The scene now pins every cell of the June found here, so the solver only confirms
it; the in-process solve tests assert what the rule holds (every one of Amal's day shifts followed) rather than a count from one
search (`83e0a5d`).

No Codex review, as the brief says.

**Things later tickets should know.** Comments are left on tickets 56 and 61.
- **56:** read `on_probation` and `preceptor` off the month's input for the sheets' totals and the heading. The swap words lean on
  your heading. `preceptors.assignment_in` and `spans` serve My month.
- **61:** the row's fourth action, "Choose/Change preceptor", shows behind `mayChange` and also for a nurse due to join. The
  Deputy CNO reads the preceptor and assigns none.

**Merged on 2026-11-12:** `origin/main` (tickets 51 and 60) merged in at `7ac08d1`, with one conflict, both tickets' notes on
ticket 61, both kept; no migration clash and no change to the generated client. The overlapping tests passed locally (backend 275,
frontend 65), and both workflows (backend, solver, frontend, image, browser checks) were green on `7ac08d1`; `main` was
fast-forwarded from `c62cc35` to `7ac08d1`. What follows it is this ticket's markdown only (`[skip ci]`).

**Reviewed by the user (2026-11-12):** all five points kept as built.
- A retired skill marked "Lets a nurse precept" lets no one precept.
- The night-alone gap: a unit dropping a shift that would leave her the night shift alone is refused; a transfer empties her
  allowed shifts for the new unit's manager to choose.
- The swap and cover refusals name her probation and her preceptor, leaning on ticket 56's "On probation" heading.
- The explanation's words for the days she did not follow her preceptor.
- Extend and Length are refused when her preceptor would then precept two nurses in one month.
