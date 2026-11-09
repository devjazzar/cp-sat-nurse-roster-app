# 35: Solving with skills

**What to build:** Every solve, re-plan, draft check, submit, approval, restore and month close of a unit carries its nurses' skills and its skill needs to the solver, as a version 2 solve input. A nurse's skill is sent with its expiry when that falls in the month, with its past expiry when it expired before the month (so the bar applies and absence means no record), and with none when it is valid past the month or does not expire; the required skills and the weight come from the hospital rules. The manager reads the precheck's warnings and the result's explanation for the new rules in dates, not day numbers; the draft check names a need he breaks or a barred day he fills; submit and approval refuse a roster that breaks one on the month as it stands; a draft is warned that skills changed since its solve.

**Blocked by:** 31 Solver; 33 A nurse's skills; 34 Skill needs and the price

**Status:** ready-for-agent

- [ ] The solve input assembler writes version 2 with the nurse `skills` clamped to the month as the spec says, `required_skills` and `skill_shortfall` from the hospital rules, and the unit's `skill_needs` and flag. A stored version 1 input is still explained, compared with, restored from and re-closed from.
- [x] A skill rename is carried through stored inputs when they are read, as a shift rename is; stored inputs keep the names they were given.
- [x] A draft's changes since its solve gain the kind `skills`: a nurse's skills as the month would see them differ from the stored input's, or the needs, the flag, the required skills or the weight differ.
- [x] Precheck warnings, the result's explanation, violations and the draft check show the two rules in the page's words with dates; the shortfall per rule reads like any soft rule, a hard need or a barred day like any hard rule.
- [x] Submit and approval refuse a grid breaking a hard skill need or filling a barred day, as for any hard rule; a re-plan honours skills on the days it plans; the close reports what the facts broke and never refuses.
- [x] The failure kind `refused` covers a version 2 input the solver refuses, read as rules to review.
- [x] The architecture document's solve input, lifecycle and "what a solve shows" paragraphs say so.
- [x] Tests at the web API seam with the scripted solver for the assembled input (each clamping case, a nurse with no record, a renewed skill), changes since, the words in dates, submit and approval refusals; a few end to end with the real solver in process on a small month where a need or a bar decides the roster.

## Comments

**From ticket 33 (2026-11-09):** a nurse's skills are `nurses.models.NurseSkill` rows: `NurseSkill.objects.current()` are
the ones that count, one per nurse and skill, `expiry` the last day it counts. Read `expiry` only when `skill.expires` is
on: turning `expires` off keeps the recorded dates, which must then count for nothing (the API already sends null there,
`nurses.skills.as_rows`). A retired skill's records stay current until the CNO takes them off. Each write audits
`nurse.skills_changed` and ends a row rather than rewriting it, so "skills changed since the solve" can compare what the month
sees with the stored input, or look for rows recorded or removed after the solve.

**From ticket 34 (2026-11-09):** the solve input is already version 2. `solves.input.assemble` writes `"version": 2`; the
department block carries the unit's `skill_needs` and `skill_needs_hard`; the general block carries `weights.skill_shortfall`
and `required_skills`, the live skills marked required to work (`hospital.rules.required_skills()`, retired ones left out;
change it there if a retired required skill should still bar). What is left here is the nurses' `skills`, changes since, the
rename carried through stored inputs on read, and the words in dates. The four-nurse service sample is version 2 with no
skills; the solver's `tests.er_fixture.version_1` derives a version 1 input from it.

**From the review of ticket 34 (2026-11-09), decided by the user:**
- A "work this day" preference on a day barred by an expired required skill costs its weight unavoidably, because only leave supersedes a preference. Decide here whether a barred day should supersede preferences as leave does: in the solver, and in the count of preferences not kept.
- Also decide whether a retired required skill should still bar. `hospital.rules.required_skills()` sends live ones only.

**Implemented on 2026-11-09,** on branch `claude/ticket-35-solving-with-skills-e1b8da`, draft pull request
Nurse-Fold/cp-sat-nurse-roster-app#21, from `main` at `9aa8158`. The commits:
- `13eb7ed`: the backend, the solver change, the frontend words and the regenerated client;
- `91f5892`: the architecture document, `solver/DESIGN.md`, and a note on ticket 38;
- `ca3bcad`: a shift pinned on a barred day is kept out of the input, and the precheck's words name no pronoun;
- `a9f675b`: the review's points;
- then this comment.

The suites ran locally, one at a time under the heavy-run lock, on a throwaway PostgreSQL 18 container of my own:
- the backend: 2815 passed, run on `13eb7ed` plus the docs;
- the solver's whole suite with its service tests: 603 passed;
- the frontend: one `npm test` run, 671 passed, and `npm run build` succeeded;
- `makemigrations --check`: "No changes detected";
- the OpenAPI document and the generated client were regenerated from the export.

After `ca3bcad` and `a9f675b`, I reran these, not the whole backend again:
- the backend's `solves` tests and the pins, re-plan and review tests;
- the solver's `test_skills.py` and `test_preferences.py`;
- the new app tests.

GitHub runs the six parallel frontend runs and the browser checks. No Playwright file changed.

**What the dev stack needs:** a **rebuild** (`docker compose up -d --build`), because the vendored solver changed. There is no
migration, no compose, `Dockerfile` or dependency change.

**What was built, criterion by criterion.**
- **The assembled input.** Each nurse's `skills` come from `nurses.rostering.skills_block`, merged in `solves.input.assemble`
  with the current rows prefetched:
  - a live skill's expiry is sent when it falls in the month or before it, so a required one bars her, and absence keeps meaning
    no record;
  - null is sent when it is valid past the month's last day, or when the kind does not expire (an expiry kept while `expires` was
    off counts for nothing);
  - no entry is sent for no record, and none for a **retired** skill (see decision 2).

  `required_skills`, the weight, the needs and the flag were already ticket 34's.
- **Version 1 still read.** These are tested:
  - the explanation of a stored input;
  - a draft's changes since a version 1 input;
  - a restore of a result whose input is version 1, which loads, explains, and warns `skills` where a nurse now has some.

  **Not ticked:** a re-close from a stored version 1 close input has no test of its own. A re-close assembles the month again
  from today's data, and the close in force's stored input is only read for its credited days, but nothing pins that down.
- **The rename on read.** `solves.input.in_current_skill_names` maps a stored input's nurse skill keys, its `required_skills`
  and its needs' skills to today's names, through `SkillRename`. It is used:
  - for a result's explanation and a re-plan's comparison (`solves.history_api`);
  - inside `changes_since`.

  The stored input keeps its names. The result's own `violations` texts are stored text and keep the old name.
- **Changes since, kind `skills`.**
  - Per nurse: her skills as the month sees them differ from the stored input's (a stored version 1 reads as none).
  - With an empty `hospital_id`, a change of the unit's own: the needs, the flag, `required_skills` or the weight. The page
    says "The skill needs, the skills required to work or the skill shortfall weight changed".
  - A rename is no change, and a renewal the month cannot see (valid past it either way) is none.
  - A submission now keeps each nurse's `skills`, so a skill change while it waits is news to the approver (`new_since`).
  - A re-plan whose month's skills changed while it ran ends `outdated`, through the same comparison.
- **The words.** The solver's texts already said "day N", and `in_dates` turns each into its date. So the precheck, the
  explanation, violations, the draft check and the close all read in dates. The penalties panel labels the soft rule
  `skill_need` by its weight's name, "Short of a skill need", where it showed the raw id. A hard need and a barred day are
  violations like any other.
- **Submit, approval, re-plan, close.** These fall out of the assembled input:
  - submit and approval refuse a grid breaking a hard need or filling a barred day, and a soft need passes;
  - a re-plan's input carries skills and needs, and the solver plans only its days;
  - the close lists `skill_expired` and `skill_need` among what the facts broke, in dates, and closes.
- **`refused`.** A version 2 input the solver refuses is failure `refused`, with its words in dates.
- **Tests.**
  - `solves/tests/test_input.py`: each clamping case, no record, a renewal, a removal, a retired skill, `expires` turned off,
    changes since per nurse and per unit, the rename, and version 1.
  - `test_history.py`: the explanation under a renamed skill, `refused` on version 2, and the version 1 restore.
  - `rosters/tests/test_review.py`: submit and approval.
  - `test_replan.py`: skills in a re-plan, outdated on a skill change, and an elapsed barred pin as a fact.
  - `test_pins.py`: the draft check of a barred day.
  - `test_own_month.py`: a barred preference.
  - `closes/tests/test_guards.py`: the close.
  - End to end with the real solver: a hard ICU need and Badr's expiry decide a June, with the precheck in dates beforehand.
  - Solver rule tests in `tests/test_preferences.py`.
  - `src/app.test.tsx`: the change lines, the skill violations in the draft check, the soft rule's label, and "Skill expired" on
    My month.
- **Docs.** `docs/ARCHITECTURE.md`:
  - section 6 says what the nurse's `skills` hold, the barred preference, and the rename on read;
  - section 5 gives the `skills` change, the submission, the re-plan, submit, approval and the close;
  - section 8's "what a solve shows" names the two rules' words.

  `solver/DESIGN.md` gives the barred preference.

**What was driven, and how.** I drove my own scratch stack, `e2e/stack.sh up nr35` (ports 18350/18753), in the desktop app's
browser. The pane was hidden, so I worked the pages by their accessibility tree and read what they rendered; there are no
screenshots. The setup went through the API as Carla. The stack was taken down afterwards.
- **As Carla (API):** I added ICU (not expiring) and BLS (expiring, required to work), recorded ICU on Amal and Emad, and BLS on
  Badr to 20 January 2027.
- **As Mona, on Unit rules:** I added "Skill need 1", Day, ICU, 1 and 1, with "Never break the skill needs" ticked, and saved:
  "Saved."
- **Roster, January 2027, before solving:** the solver's check said "Badr: BLS, required to work, expires inside the month: its
  last day is 2027-01-20, and she works no shift after it". The pronoun was wrong for Badr, so I changed the words (below).
- **Solved:** the solve finished, Day held Amal or Emad every day, and Badr worked nothing after the 20th.
- **The draft check:** I pinned Day on Badr's 25 January, unsaved. Before the fix the check said the solver's code could not
  check it: its loader refuses a pin on a barred day. After the rebuild it said "The draft with these changes breaks 2 hard
  rules" and listed "Badr Harbi, 25 January: skill expired: Badr works D on 2027-01-25, BLS is required to work and its last
  day was 2027-01-20". I discarded the edit.
- **Changes since:** Carla renewed Badr's BLS to 31 December 2027 through the API, and the draft read "This draft was solved
  before these changes: Badr Harbi: skills changed".
- **A soft need:** I set the skill shortfall weight to 5 on the stack's database, a shortcut for the CNO's page. Mona unticked
  the flag and asked for 2 on a weekday on Unit rules. The draft then also listed "The skill needs, the skills required to work
  or the price of a short skill changed", the wording since changed to the glossary's.
- **Solved again:** "Penalties per rule" led with "Short of a skill need 170, 34 × 5, its weight. Counted in: nurse short of a
  skill need on a shift-day.", then "The unit: skill need: 2027-01-04 D has 0 holding ICU, needs 2 (2 short)" and four more, "and
  22 more like these".

**What was found, and fixed.**
- **A shift pinned on a barred day made the month unreadable.** The solver's loader refuses such a pin on a day it plans, so a
  hand edit, and any later solve, failed as "could not check" or `refused`.
  - `solves.input.without_barred_shifts` now keeps the pin out of the input, in `assemble` and in the edit check's
    `rosters.editing.with_edits`. The pin row stays, and the grid holds the shift, so the check names `skill_expired`.
  - A re-plan keeps such a pin before its date, as the fact the solver accepts there.
  - Swaps and covers add their cells as pins the same way (`rosters.approved.with_pins`). A swap onto a colleague's barred
    day read only "This swap cannot be checked against the roster now. Ask your manager.", and a cover could not be judged.
    The same filter now applies there:
    - the proposer reads "This swap cannot work for Emad on 9 June 2026", and the manager reads the skill in full
      (`swaps/tests/test_swaps.py`, the `barred_by_an_expired_skill` case);
    - a cover is still judged, and leaves the barred nurse out (`covers/tests/test_covers.py`).
  - Ticket 38's set-aside reason and its words are still 38's, and the note on 38 says so.
- **The precheck said "she" for any nurse.** The solver's line now reads "…its last day is <date>, so no shift after it".
- **A skill name the solver refuses** (a leading `= + - @ '`, or a line break) left every solve of a unit refused once a nurse
  held it. The catalogue now refuses such a name, beside its field.

**Findings for you, not fixed:**
- **A skill already stored with such a name** still refuses every solve of a unit where a nurse holds it, until the CNO renames
  it. Nothing finds them. I expect none on the dev stack.
- **The solver's words are in ISO dates** ("2027-01-25"), as every rule's are today, where the page's own lines say "25 January".
  That is the existing reading of "with dates" (`in_dates`), kept.
- **The precheck names nurses by hospital ID** ("Badr:"), as all its lines do.

**What was NOT checked:**
- A re-close from a stored version 1 close input, as above.
- The skill shortfall weight set on Hospital rules by hand: I set it on the stack's database.
- The pages at phone width and with a screen reader. The words were held against `better-writing` and `better-interface` by
  hand: "Skill expired" sits beside "On leave", and the unit's change line has no name prefix.
- A swap or a cover on a barred day beyond the two tests above: the rest is ticket 38's.
- The six parallel frontend runs and the browser checks, locally: they are GitHub's, on the pull request.

**Decisions taken here, and Worth your review:**
- **Worth your review, 1: a day barred by an expired required skill supersedes a preference, as leave does.** This changes the
  solver. In the search, the explanation and the carry-over, a wish on a barred day costs nothing and is no preference not kept
  (`nurse_roster.problem.superseding`). My month marks it "Skill expired", counted neither way (outcome `barred`).
  - Why: no roster can keep it, and counting it would double her price next month for something no roster could give, which
    ADR 0013's cap on growth argues against.
  - It matches your decision at ticket 31's review that fairness treats a barred day as leave.
- **Worth your review, 2: a retired required skill bars nobody,** and a retired skill is sent as no record.
  - Why: a retired skill can be neither recorded nor renewed, so a nurse barred by one could be freed only by the CNO taking the
    record off.
  - The architecture document already said a retired one bars nobody, and the documents win.
  - Retiring one shows as a `skills` change, for the unit and for each nurse who held it.
- **Worth your review: a unit's own skill change is a `DraftChange` with an empty `hospital_id`,** rather than a new kind or a
  second list. That keeps the one kind the ticket names.
- **Worth your review: a shift pinned on a barred day is kept out of the input here,** ahead of ticket 38. Without it, a hand edit
  makes the check unreadable and every solve refused, which is a regression from this ticket.
- **Worth your review: the catalogue now refuses a skill name the solver would refuse.** That is ticket 32's form, changed here
  because this ticket makes such a name break solves.
- Unit-level changes are not kept in a submission: the approver sees a nurse's skill change while it waited, not a change of
  the unit's needs.

**Review:** `code-review` against `9aa8158`, both axes.
- **Standards:** no hard violation. Fixed:
  - the change line's wording now uses the glossary's "skill shortfall weight";
  - `changes_since` maps names once (`in_current_skill_names`), not per nurse and skill.

  Kept:
  - `current_skill_name` beside `rosters.drafts.current_code`: the same shape, for a different log;
  - `barred_from` restates the solver's `barred_days` on dates, because the assembler has no `Problem` yet;
  - the empty `hospital_id`, as above;
  - the name `superseding`;
  - `department` as a local name: it is the solver's key.
- **Spec:**
  - Fixed: a re-plan dropped an elapsed shift pinned on a barred day, which is a fact. It now keeps it, with a test.
  - Added: a test for the version 1 restore.
  - Kept: the precheck's dates are tested end to end with the real solver, not with the scripted one.
  - Scope: the name validator and the barred-pin filter are flagged above.
  - The two decisions were found consistent.

**Things later tickets should know.**
- **38:** read its new comment. Swap judging already hides both rules correctly. A barred pin is kept out of the input
  (`solves.input.without_barred_shifts`), but not yet set aside on the draft or refused as a request.
- **Anyone reading "barred":** the solver's `nurse_roster.problem.barred_days` is the definition. `solves.input.barred_from`
  mirrors it on dates for the assembler, so change both together.
- **Anyone adding a change kind of the unit's own:** it is a `DraftChange` with an empty `hospital_id`; the frontend's
  `changeSays` reads that.

**Reviewed by the user (2026-11-09):** all five points kept as recommended.
- A barred day supersedes a preference, as leave does.
- A retired required skill bars nobody.
- A unit's own skill change is a `DraftChange` with an empty `hospital_id`.
- A shift pinned on a barred day is kept out of the input.
- The catalogue refuses a skill name the solver would refuse.
