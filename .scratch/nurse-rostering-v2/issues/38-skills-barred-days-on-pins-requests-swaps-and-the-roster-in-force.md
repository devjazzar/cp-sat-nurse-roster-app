# 38: Barred days on pins, requests, swaps and the roster in force

**What to build:** A day a nurse may not work, because a required skill of hers expired before it, is treated as her leave and her dates are: a pin on it is set aside, not removed, and counts again when the skill is renewed; a shift request for it is refused as she makes it, her own reason in full. A swap is judged by the solver's code as today: a refusal resting on a colleague's expired skill reads "This swap cannot work for <name> on <date>", a skill need left short reads only that the day's shifts would break the unit's rules, the proposer's own expiry is said in full, and the manager reads every reason; approval is refused when a skill change since made the swap break a hard rule. Nothing rewrites an approved roster when an expiry passes: the Roster page shows the skill rule it now breaks, and the manager edits or re-plans.

**Blocked by:** 35 Solving with skills

**Status:** ready-for-agent

- [x] A pin on a barred day is set aside with a reason of its own in the draft's words, reaches no solve, and counts again when the record is renewed or removed; pinning a shift on a barred day is refused, naming the skill.
- [x] A shift request on a barred day is refused as made with the nurse's own reason; a day-off request is allowed.
- [x] Swap judging maps the two rules to the hidden form for a colleague and the full form for the proposer; the manager reads all; approval re-judges.
- [x] The Roster page's check of an approved roster on the month as it stands shows a skill rule now broken, as it shows any other.
- [x] The architecture document's pinned cell, request and swap paragraphs say so.
- [x] Tests at the web API seam: the pin set aside and counting again, the request refusals, each swap wording from the proposer's and the manager's side, an approval refused, the Roster page's check.

**From ticket 35 (2026-11-09):** every solve, re-plan, draft check, swap and cover judging, submit and approval input now carries
each nurse's `skills` (`nurses.rostering.skills_block`, called by `solves.input.assemble`), so the two rules already reach
everything that checks a grid with the solver's code. What that means for this ticket:
- **Swap judging needed no change to stay hidden.** `swaps.judging._violation_problem` already hides a violation on a colleague
  ("This swap cannot work for <name> on <date>"), says the proposer's own in full, and hides every unit-level rule but
  `headcount` (`SAID_AS_IT_IS`). So `skill_expired` and `skill_need` take the forms the spec asks for. No test pins them yet:
  they are this ticket's.
- **Pins and requests still don't know a barred day,** but a pin can no longer break the solve. `rosters.pins.Judge.day_why` has
  no `barred` reason. Ticket 35 keeps a shift pinned on a barred day out of every input instead
  (`solves.input.without_barred_shifts`, in `assemble` and in the edit check's `rosters.editing.with_edits`), because the
  solver's loader refuses one. The pin row stays, and the grid holds its shift, so the check names the `skill_expired` rule.
  What is left here: the set-aside reason and its words on the draft, and the request refusal. A barred day is every day from
  `solves.input.barred_from`, which mirrors `nurse_roster.problem.barred_days`. The filter cuts only the days a solve plans:
  a re-plan keeps an elapsed one as a fact. Swap and cover judging go through `rosters.approved.with_pins`, which applies the same
  filter, so a swap cell on a barred day is judged on the grid, not as a pin. One test each covers that path: the swap's
  hidden form (`barred_by_an_expired_skill`) and a cover leaving the barred nurse out. Once 38's set-aside lands, drop the filter or keep it as the
  one definition.
- **The Roster page already shows an approved roster's skill rules** among "what the grid breaks on the month as it stands".
  Ticket 35 tested the draft's case and the submit and approval refusals, not the approved roster's.
- **A barred day supersedes a preference** since ticket 35, in the solver and on My month, where it reads "Skill expired".

**Implemented on 2026-11-09,** on branch `claude/ticket-38-barred-days-c81e27`, draft pull request
Nurse-Fold/cp-sat-nurse-roster-app#27, from `main` at `68d4a6a`. The commits:
- `8e8e3a8`: the backend, its tests, the regenerated client, the draft's word, the architecture document and the glossary;
- `5cdcbc6`: the review's points;
- `49b7dd7`: `origin/main` merged in (the CI action bump and the cover check's wait; no file of this ticket's);
- then this comment.

The suites ran locally, one at a time under the heavy-run lock, on a throwaway PostgreSQL 18 container of my own:
- the backend: 2913 passed, on `8e8e3a8`;
- the frontend: one `npm test` run, 697 passed, and `npm run build` succeeded;
- `makemigrations --check`: "No changes detected";
- the OpenAPI document and the client were regenerated from the export: `set_aside` gains `barred` in two schemas.

After `5cdcbc6` I reran the swaps, covers, requests, pins, re-plan and solve input tests (383 passed); the commit touches only
those paths. The solver's suite was not run: nothing under `solver/` changed. GitHub runs the six parallel frontend runs and
the browser checks. No Playwright file changed.

**What the dev stack needs:** a **rebuild** (`docker compose up -d --build`) for the new code. There is no migration, and no
change to compose, the `Dockerfile`, the solver or any dependency.

**What was built, criterion by criterion.**
- **One definition of the bar.** `solves.input.barred_from` now answers a `Bar`: the skill and its expiry, with `first`, the
  first barred day. It picks the skill the solver's `expired_required` picks: the earliest expiry, one before the month counting
  as the day before it, and a tie going to the first name. So a refusal names the skill that `skill_expired` names.
  `rosters.pins.Judge` reads every nurse's bar once, from the same `skills_block` and `required_skills` the solve input uses.
- **A pin on a barred day is set aside.** `barred` is a new reason (`AsideWhy`), and it applies to a **shift** only, in
  `Judge.shift_why`, which now takes the day. A day off on a barred day counts, as it is hers either way.
  - The pin reaches no solve. The draft lists it under "These pins count for nothing at present" as "a day after a skill
    required to work expired, so they can work no shift". The cell reads "pinned, but counts for nothing now", as other
    set-aside pins do.
  - It counts again when the skill is renewed past the day, its record is taken off, or the skill is no longer required to
    work. All of this is worked out when read, and nothing is ended or rewritten.
  - Pinning a shift there is refused on save, and listed among the refusals on a check, naming the skill: "Amal's BLS,
    required to work, counted until 20 June 2026, so Amal can work no shift on 25 June 2026."
  - A manager's acceptance of a shift request there is refused in the same words. An accepted request whose pin is set aside
    shows `set_aside: barred` on the manager's list.
- **Requests.** A shift request on a barred day is refused as it is made, on the `shift` field, in her own words: "Your BLS,
  required to work, counted until 15 June 2026, so you can work no shift on 20 June 2026. You can still ask for the day off."
  A day-off request is made and accepted like any other. A preference is left as ticket 35 left it: allowed, and superseded by
  the bar (see the decisions).
- **Swaps.** A cell asking a shift of a barred nurse is caught with the other cell problems, before the solver's check:
  - for a colleague, the proposer reads "This swap cannot work for Badr Harbi on 1 December 2026.";
  - for the proposer's own cell, the full sentence, "Your BLS, …";
  - the manager reads the full sentence with the nurse's name.

  A skill need left short is the solver's `skill_need` violation, which `_violation_problem` already hid ("This swap cannot
  work on 9 June 2026: that day's shifts would break the unit's rules."), while the manager reads the solver's words.
  Approval judges again, so an expiry recorded after the colleagues accepted refuses it, and so does a skill need written
  since.
- **The roster in force.** Nothing is written when an expiry passes. The Roster page's existing check of the month as it stands
  lists `skill_expired` for each shift the approved grid holds after the expiry, as for any rule.
- **Covers**, as leave is treated there: a barred nurse is left out of the list before her grid is checked, and her acceptance
  is refused in her own words, "Your BLS, required to work, counted until 8 June 2026, so you cannot take this cover."
- **Ticket 35's filter is dropped** (`without_barred_shifts`, and `assemble`'s `planning_from`, which only it used). See
  **Worth your review**.
- **Docs.** `docs/ARCHITECTURE.md`:
  - the pinned cell paragraph: the bar for a shift, the refusal's words, set aside and counting again, the re-plan and the
    close;
  - Requests step 2: the request refused in her words, a day off allowed, an accepted one set aside;
  - Swaps steps 2 and 4: the hidden forms and the re-judged approval;
  - Covers step 2: a barred nurse left out;
  - section 5: nothing rewrites an approved roster.

  `GLOSSARY.md`'s **Pinned cell** names the set-aside.
- **Tests at the web API seam:**
  - `rosters/tests/test_pins.py` `TestABarredDay`:
    - set aside and kept out of the input;
    - counting again on renewal, on removal, and when the skill is no longer required;
    - a refusal on save and on a check naming the skill, while a day off pins.
  - `requesting/tests/test_requests.py`:
    - the shift request refused, and the day off made and accepted;
    - one accepted before the expiry set aside, and the acceptance of one after it refused.
  - `swaps/tests/test_swaps.py`:
    - a colleague's expiry hidden, with the manager's full words;
    - the proposer's own expiry, from both sides;
    - a skill need hidden, from both sides;
    - approval refused after an expiry, and after a skill need written since.
  - `covers/tests/test_offers.py`: the acceptance refused in her words.
  - `rosters/tests/test_review.py`: an approved roster unchanged, and its page naming `skill_expired` on her days.
  - `rosters/tests/test_replan.py`: a barred pin set aside before the date too, and a re-plan's end not `outdated` by it.
  - `src/app.test.tsx`: the draft's new words.

**What was driven, and how.** I used my own scratch stack, `e2e/stack.sh up t38` (ports 18380 and 18843), today being 9 November 2026.
The setup went through the API: Carla added BLS (expires, required to work); Mona solved January 2027 for real and pinned
Amal's Day on the 10th and 20th, Night on the 25th and off on the 26th; then Carla recorded Amal's BLS until 15 January. I used
the desktop app's browser with the pane hidden, at an emulated 1280 by 900, and read pages by their text and accessibility tree.
- **As Mona, Roster, January 2027.** The draft listed the 20th's D and the 25th's N under "These pins count for nothing at
  present", each "a day after a skill required to work expired, so they can work no shift". Those two cells read "pinned, but
  counts for nothing now", while the 10th and the 26th stayed pinned. Pinning Day on the 21st from the cell menu put "Amal
  Saleh's BLS, required to work, counted until 15 January 2027, so Amal Saleh can work no shift on 21 January 2027." under
  "These would be refused, so the check leaves them out". The check listed `skill expired` for her shifts after the 15th.
  I discarded the edit.
- **As Amal, My month, January 2027.**
  - A Day request on the 22nd was refused under the shift field: "Your BLS, required to work, counted until 15 January 2027,
    so you can work no shift on 22 January 2027. You can still ask for the day off." The field had `aria-invalid` and
    `aria-describedby` pointing at that sentence.
  - A day off on the 22nd was made: "Your request for a day off on 22 Jan 2027 is made." Mona accepted it through the API,
    and it counted as a pin.
- **Renewal.** Carla renewed Amal's BLS to 2028 through the API, and the draft's pins on the 20th and 25th counted again, with
  no set-aside.
- **The swap, December 2026 (approved).** Dana proposed giving Badr her Night on 1 December (the stack's sound swap), and Badr
  accepted, both through the API. Then Carla recorded Badr's BLS until 30 November.
  - As Mona on Swaps, the swap read "It cannot be approved as the month stands now: Badr Harbi's BLS, required to work,
    counted until 30 November 2026, so Badr Harbi can work no shift on 1 December 2026." Approve through the API was 409 with
    the same words. Mona rejected it.
  - Dana then proposed the same cells through the API and read only "This swap cannot work for Badr Harbi on 1 December 2026."
    Badr proposed them and read "Your BLS, required to work, counted until 30 November 2026, so you can work no shift on
    1 December 2026."
- **As Mona, Roster, December 2026.** Version 1 was still in force and unchanged. The page read "The roster in force, on the
  month as it stands, breaks 18 hard rules", starting with "Badr Harbi, 2 December: skill expired: Badr works N on
  2026-12-02, …", and listed "Badr Harbi: skills changed" among the changes since the solve.

The stack is down and its volumes gone.

**What was found, and fixed.**
- On `main`, a re-plan whose month held a shift pinned on a barred day before its date would have ended `outdated`, and so
  could never put a version in force. Its input kept that pin as a fact, while `changes_since`'s fresh assembly (which has no
  date) dropped it, so the pins compared unequal. Setting the pin aside uniformly removes the mismatch. A test holds that the
  end is `version`.

**Findings for you, not fixed:** none.

**What was NOT checked.**
- The proposer's words in the swap composer's page: they were read from the API's answer. The page shows a refusal's sentences
  as it shows every other.
- A screen reader, beyond the accessibility tree.
- The six parallel frontend runs and the browser checks, locally: GitHub runs them on the pull request.
- The whole backend suite after `5cdcbc6`, locally: the paths it touches were rerun.

**Decisions taken here.**
- **The bar applies to a shift only.** A day off may be pinned, requested and accepted on a barred day. A preference on one
  stays allowed, as ticket 35 left it to supersede: refusing it would tell her nothing she does not read on My month already.
- **Covers treat a barred day as leave** (the run's instruction "wherever the code treats leave"), though no criterion names
  covers.
- **The refusal's words** use the glossary's terms: "counted until" for the expiry (the last day a skill counts) and
  "required to work". The draft's set-aside line names no skill, because the set-aside reasons are fixed phrases
  (`SET_ASIDE`). The cell's menu refusal names it.

**Worth your review.**
- **Ticket 35's filter is dropped, not kept.** Setting the pin aside in `rosters.pins` is the one place, as for every other
  set-aside reason. Keeping `without_barred_shifts` beside it would have been a second, slightly different definition: it kept
  an elapsed pin in a re-plan, and that is what made the re-plan's end `outdated` (above).
  - The price: an elapsed barred pin is no longer a fact of a re-plan. The roster in force's cell that day is, and it
    normally holds what the pin held.
  - A month's close still reads pins as facts, the bar ignored (it uses only `day_why`, as before), so a shift pinned and
    worked on a barred day is reported among what the facts broke. Leave and dates still set a pin aside at the close.
- **A colleague's barred cell is now refused before the solver's check,** as leave is. So the manager reads the app's sentence,
  naming the skill and the date, rather than the solver's `skill expired: …` text. The solver's `skill_expired` violation on a
  colleague is still hidden by `_violation_problem`, but no swap reaches it now. Only a swap that asks no shift of her could,
  and such a swap newly breaks nothing of hers.
- **`barred_from` stays in `solves.input`,** under the name the run named, though only `Judge` calls it now. So `rosters.pins`
  imports it inside `Judge.__init__`, as `assemble` imports `closes.chain`. Moving it beside `skills_block` in `nurses.rostering`
  would remove that.

**Review.** `code-review` against `68d4a6a` ran its two axes in parallel.
- **Standards:** no hard breach of a documented standard. Of the judgement calls:
  - the bar's sentence built in four places is now one method, `Judge.bar_said`;
  - `barred_from` reads by name, not tuple index;
  - the cover's reason folding has a comment;
  - a stray blank line is gone;
  - the module's place and the per-reason branches are kept (above, and the pattern predates this).
- **Spec:** two missing tests are added: the manager's side of the proposer's own expiry, and an approval refused after a
  skill need written since. The cover exclusion and the re-plan change are kept, and the two `Worth your review` items above
  are its other points. The glossary line describes the set-aside and does not define the bar.

**Things later tickets should know.**
- `Judge.shift_why(nurse_id, day, shift)` now takes the day. `Judge.bar(nurse_id, day)` is the bar on a day, and
  `Judge.bar_said(nurse_id, day, whose)` is how a sentence that says it begins.
- `set_aside` may now be `barred` on the draft's pins and on the manager's request rows.
- A close reads a barred pin as a fact (worked). If a later ticket wants leave's treatment there too, it is
  `rosters.pins.month_pins` with `facts=True`.
