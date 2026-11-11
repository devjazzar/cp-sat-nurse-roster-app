# 54: Probation on a nurse: the tick, the length and the end

**What to build:** The CNO ticks "On probation" when adding a staff nurse, on the form or in an optional CSV column, and may correct it later: unticking removes the probation from the first month whose roster is not yet approved, and ticking a nurse already added is allowed only while six months from her start date have not passed. Probation begins on her start date and is counted in whole calendar months, a month she joins after the 1st not counted; its last day is derived, never entered. Her unit manager works on her row of the Rostering attributes page: the length (1, 2 or 3 months, standing at 3 until he chooses), Extend (one month at a time, to 6 at most) and End (the last day becomes the last day of the month under way), each behind its question, with the last day shown. It ends by itself on its last day; at the start of her last month the unit manager is notified ("Layan Alharbi's probation ends on 31 March. Extend it or let it end."). It follows her across a transfer. The CNO and the Deputy CNO read it; the staff list says who is on probation and until when. Nothing in a roster or a solve input changes in this ticket: tickets 55 and 56 do that. Spec: `.scratch/nurse-rostering-v2/specs/probation.md`; the words: `GLOSSARY.md` (Probation, Nurse on probation).

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [x] The nurse profile holds her probation: on probation (the CNO's), the length in months and whether it was ended early (her unit manager's); the last day is derived from them and her start date
- [x] The month counting, on worked dates: a start on the 1st counts that month; a start on the 15th does not (15 December and 3 months ends 31 March); February; across a year's end; a corrected start date moves it
- [x] The CNO's tick on the nurse form and the CSV's optional "On probation" column (empty meaning no; the template updated); refused for a unit manager with a nurse profile
- [x] The CNO's corrections: unticking applies from the first month whose roster is not approved; ticking later is refused once six months from her start date have passed
- [x] The unit manager's length, Extend and End on the Rostering attributes row, with the refusals: a length outside 1 to 3 at first, an extension beyond 6, an extension of an ended probation; the CNO and Deputy CNO read the row, the System Admin never
- [x] Setting her allowed shifts to the unit's night shift alone is refused while she is on probation
- [x] It ends by itself on its last day; the notification to the unit manager at the start of her last month, once, from the hourly job
- [x] A transfer carries the probation along, counted from her start date as before
- [x] The staff list carries who is on probation and until when
- [x] Audit entries for the tick, the length, an extension and an end, with their values
- [x] Tests at the web API seam (each role, the counting, the refusals, the automatic end, the notification, a transfer, the CSV, the audit entries) and the frontend app-level suite (the form's tick, the attributes row and its questions); six runs at once
- [x] `docs/ARCHITECTURE.md`'s roles table and domain model name the probation and who sets what; `GLOSSARY.md`'s Nurse profile entry names it; the OpenAPI document and the generated client regenerated; the migration

## Comments

**Implemented on 2026-11-11,** on branch `claude/ticket-54-probation-on-a-nurse-7c870f` (`a0dfe34`, `ba12fe8`, `0a0b175`,
`ff29b9d`, `76c9b1c`, then the no-manager fix and this comment), from `main` at `e8b1308`. Draft pull request
[devjazzar/cp-sat-nurse-roster-app#17](https://github.com/devjazzar/cp-sat-nurse-roster-app/pull/17).

The suites ran locally under the heavy-run lock, on `76c9b1c`:
- the backend on a throwaway PostgreSQL 18 container of my own: 3242 passed. After it, the no-manager fix added one test; the
  probation and end-date files ran again: 75 passed;
- the frontend: `npm test` 781 passed, and `npm run build` was clean;
- `makemigrations --check`: "No changes detected";
- `frontend/openapi.json` and the generated client were regenerated from the export and committed; CI checks that they match;
- no Playwright file changed, and there is no new journey;
- GitHub's two workflows (the three suites, the image, six frontend runs at once, the browser checks) were green on `76c9b1c`.

**What the dev stack needs:** `docker compose up -d --build`. Two migrations come with it: `nurses` 0006 (the probation's
four fields and two constraints) and `notifications` 0009 (the new event). `web` runs them at start. There is a new hourly job,
`nurses.tasks.tell_probations_ending` at minute 25, which the worker registers itself. No `compose.yaml`, `Dockerfile`, solver
or dependency change.

**What was built, criterion by criterion.**
- **The record.**
  - `NurseProfile` gains `on_probation` (the CNO's tick), `probation_months` (1 to 6, default 3, held by a check constraint),
    `probation_ended_in` (a month, on its 1st) and `probation_notified_for`.
  - The last day is never stored. `nurses/probation.py` derives it, and every reader goes through that module: the rows, the
    staff list, the night refusal and the job.
- **The counting** (`first_counted_month`, `last_day_after`). Tested on hand-counted dates:
  - 1 Dec + 3 → 28 Feb; 15 Dec + 3 → 31 Mar; 12 Nov + 1 → 31 Dec;
  - 31 Jan + 1 → 28 Feb; 20 Dec 2027 + 2 → 29 Feb 2028; 20 Nov + 2 → 31 Jan, across the year's end;
  - a start corrected from 15 Dec to 1 Dec → 28 Feb, and to 2 Jan → 30 Apr.
- **The CNO's tick.**
  - On the Add a nurse form, as "On probation", with a line saying her unit manager sets how long it lasts.
  - In the import: an optional sixth column, "On probation". It takes Yes, No, Y, N, TRUE or FALSE in any case, and empty means
    no. A file whose header leaves the column out imports as before. The template names the column, the import page explains
    it, and the preview shows it.
  - Refused (422 on `on_probation`) for a unit manager's nurse profile, both on giving one and on a correction.
- **The corrections**, on Correct details, for a staff nurse only. The tick is sent only when it changes, so a save of the rest
  is never refused over the six months.
  - Unticking walks her months from her start date's month and stops at the first whose roster, in the unit that month falls
    under, is not approved. The months before stay as an early end would keep them. With none approved, the probation is gone.
  - A later tick is refused once six months from her start date, counted the same way and using the start date as corrected in
    the same save, have passed. It is also refused while her allowed shifts are her unit's night shift alone (see Decisions).
    It starts again at 3 months.
- **The unit manager**, on her Rostering attributes row. A new "On probation" column shows "Until 31 Mar 2027", the number of
  months and "Ended early". Three buttons sit beneath, each behind its question:
  - **Length** opens a choice of 1, 2 or 3 months, each with its last day, worked out by the server.
  - **Extend** asks "Extend the probation of … by a month?" with the new and old last days.
  - **End** asks "End the probation of …?" and says the last day becomes the last day of this month, so this month keeps its
    roster, and that an ended probation cannot be extended.
  - A button shows only when its action would be allowed: the row carries `lengths`, `if_extended` and `if_ended` from the
    server, on the hospital's clock.
  - The API refuses a length outside 1 to 3 (pydantic), a length once extended beyond 3, an extension beyond 6, any change to a
    probation ended early, and any change to one the CNO unticked. It also refuses a nurse not on probation, and a nurse due to
    join (403, her current unit's manager's).
  - The CNO and the Deputy CNO read the row with no button. The System Admin gets 403 on the row and on the Nurses list.
- **The night shift alone** is refused on both allowed-shifts endpoints while the probation is not over, its first month still
  to come included.
- **Time.**
  - The probation ends by itself, because its last day is read. The next day the row says "No" and Extend is refused.
  - `tell_probations_ending` tells her unit's manager once in her last month, from its first hour: "Layan Alharbi's
    probation ends on 31 March. Extend it or let it end." The notification links to Rostering attributes.
  - An extension tells him again in the new last month. One ended early, or unticked, tells nobody.
  - A unit with no manager tells its next manager that month.
  - The payload is the unit, the last month and the nurse's profile id, so the date is the payload's and an extension does not
    rewrite an old notification.
- **A transfer** carries it, since it is on the profile. A test: transferred to ICU from January, ICU's manager reads the same
  last day and extends it; ER's manager gets 403, and ICU's manager is the one told in April.
- **Reading.**
  - The CNO's Nurses list says "On probation until 31 Mar 2027" under Status.
  - The staff list gains "On probation" ("Yes" or empty) and "Probation's last day", for a probation not over yet.
- **Audit.** `nurse.probation_ticked`, `nurse.probation_unticked`, `nurse.probation_length_set`, `nurse.probation_extended`
  and `nurse.probation_ended` each carry before and after:
  `{"on_probation", "months", "ended_early", "last_day"}`. The audit log page has words for all five.
- **Docs.**
  - `docs/ARCHITECTURE.md` gains three rows in section 3's roles table, a Probation entry in section 4, the job in section 7,
    and the column in section 8's import.
  - The section 3 paragraph and the Notification entry name the two exceptions: the audit log's values, and a notification that
    names a nurse.
  - `GLOSSARY.md`'s Nurse profile and Notification entries name it.

**What was driven, and how.** On my own scratch stack, `e2e/stack.sh up nr-t54` (seeded), on 11 November 2026, in the
built-in browser.
- **As Carla, the CNO:**
  - added Layan Alharbi, starting 15 December 2026, with On probation ticked. The list said "On probation until 31 Mar 2027";
  - imported, through the import's preview and confirm endpoints in the signed-in page, a six-column file: Sara Qasim (1
    November, "Yes") and Huda Nabil (empty). The preview read Yes and No, and the confirm took both.
- **As Mona, ER's manager, at 375 px:**
  - the row read "Until 31 Mar 2027 · 3 months · Length · Extend" for Layan, with no End before her start month;
    "Until 31 Jan 2027 · 3 months · Length · Extend · End" for Sara; and "No" for Huda;
  - Length on Sara offered "1 month, until 30 Nov 2026", "2 months, until 31 Dec 2026" and "3 months, until 31 Jan 2027".
    Setting 2 said "The probation of Sara Qasim is 2 months, until 31 Dec 2026.", with focus on her Set attributes button;
  - Extend asked "It then ends on 31 Jan 2027 instead of 31 Dec 2026, 3 months in all…" and then said so;
  - End asked about 30 Nov 2026, and the row became "Until 30 Nov 2026 · 3 months · Ended early" with no button;
  - the page had no sideways scroll at 375 px.
- **The clock** moved to 1 March 2027 (`stack.sh clock nr-t54 110`), and the job fired twice. Mona had one notification, in
  the words above, and its link opened Rostering attributes.
- **On 1 April 2027** every row said "No": Layan's and Sara's probations had ended by themselves.

The stack, its volumes and its env file are down and removed. My PostgreSQL container `t54-pg` is removed.

**What was found, and fixed.**
- An import file with five columns in its header took a six-cell line (an unquoted comma in a name) as a full line. A line now
  counts only when its cells match its own header, as before this ticket. This was found by the existing test.
- From the review: her unit manager could still Extend or End a probation the CNO had unticked, which wrote an extension the
  last day ignored. It is now refused and not offered. Tested.
- A unit with no manager in her last month would have marked the notification sent and told nobody. Tested.

**Findings for you, not fixed.**
- A unit dropping a shift (`membership.narrow_allowed_shifts`) or a transfer carrying a list can still leave a nurse on
  probation with the night shift alone. Only the two allowed-shifts saves and the tick refuse it. Left to ticket 55, where the
  solve meets it (comment there).

**What was NOT checked.**
- The Nurses page and the import page at 375 px, and the import page's own buttons in a browser. The import was driven through
  its endpoints from the signed-in page; the page's column and wording are covered by the app-level tests only by type.
- The CNO's untick and later tick in a browser. API and app-level tests only.
- A transfer in a browser. API test only.
- Two people at once: Extend pressed by two tabs. Each write locks the nurse's row, as attribute saves do; no race test.
- Dark mode, and browsers other than the built-in one.
- The six parallel frontend runs locally: GitHub's, green.

**Decisions taken here.**
- **An early end is a month** (`probation_ended_in`), not a flag. The spec says "whether it was ended early". A month also
  keeps the CNO's untick of approved months and End in the month she joins after the 1st (31 December for a 15 December
  start), and a corrected start date still moves the rest.
- **An untick that keeps approved months** leaves `on_probation` false with that month set. Her unit manager can no longer
  change it, and the row says "Taken off by the CNO, after the months already approved".
- **The CNO's tick is refused while her allowed shifts are the night shift alone.** The spec refuses only the other order.
- **A tick within six months of her start but after three** is allowed, and ends at once: the audit entry shows its past last
  day, and the row shows none.
- **The questions' outcomes come from the server** (`lengths`, `if_extended`, `if_ended`), so the browser's clock, which the
  browser checks move apart from the server's, never decides a date.

**Worth your review.**
- **End on a month's last day** ends it that day: the month under way is that month. A test holds it.
- **End when the probation already ends this month** still marks it "Ended early", which stops an extension and the
  notification. It does not change the last day.
- **End before the month she starts in is refused** ("…begins on her start date, 15 December 2026. If she is not to be on
  probation, the CNO unticks it."). The alternative was a probation of no days left ticked.
- **Length is refused for a length that would have ended it before this month** ("2 months would have ended … on 31 October
  2026, before this month. End it instead, at the end of this month."). The spec makes lowering and End one act.
- **A re-tick starts again at 3 months**, rather than keeping the length her unit manager last chose.
- **The staff list's words:** "On probation" (Yes or empty, as the import reads it) and "Probation's last day", only for a
  probation not over yet. The Nurses list: "On probation until 31 Mar 2027".
- **The questions' words:**
  - "How long is the probation of …?", with radio choices "2 months, until 28 Feb 2027".
  - "Extend the probation of … by a month?"
  - "End the probation of …?"
  - The buttons are named "Length of …'s probation", "Extend the probation of …" and "End the probation of …".
- **The System Admin reads a probation's values in the audit log:** your decision of 2026-11-11, now written into section 3.

**Review.** `code-review` against `e8b1308`, both axes in fresh sub-agents.
- **Spec:**
  - The unticked probation still open to her unit manager: fixed, as above.
  - Two refusals beyond the spec: the tick refused over the night shift alone, and a length ending it before this month. Both
    kept, under Decisions and Worth your review.
- **Standards:**
  - The job missing from section 7's job list: added.
  - The glossary's Notification entry not naming a probation's last month: added.
  - "notice", a word the glossary avoids, in two docstrings and the ticket 55 comment: now "notification".
  - `describe` disagreeing with `ended_early` for an untick: now the same.
  - The night-alone test written twice: now one function.
  - `Line.width` and `OPTIONAL`: renamed `header_width` and `OPTIONAL_COLUMNS`.
  - A docstring's indent and an import's order: fixed.
- **Not changed:**
  - `on_probation_in` has no caller yet; it is ticket 55's month-by-month question, named in its comment.
  - `Layout.optional` serves one layout, and is how the skills layout stays untouched.
  - The endpoints re-check what the row's outcomes say, since a row can be stale.
- **By hand, against `better-interface`, `better-writing` and `better-accessibility`:**
  - The Length button's name now starts with its visible word.
  - The questions name the nurse and both dates.
  - Each action's answer goes to the page's status line, with focus on her row's button.
  - The checkbox has its description tied to it.

**Things later tickets should know.** Comments are left on tickets 55, 56 and 61.
- **55:** `probation.on_probation_in(nurse, month)` for the solve input. The fields' meanings, the kept months of an untick, and
  the night-alone gap.
- **56:** `last_day` and `running` against `on_probation_in` for a past month, and the staff list's columns.
- **61:** the row's new fifth column and its buttons behind `mayChange`; keep the Deputy's controls on a flag of their own.
  The `attributes-<id>` focus target.
