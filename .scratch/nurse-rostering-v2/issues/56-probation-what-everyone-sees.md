# 56: Probation: what everyone sees

**What to build:** Wherever the unit's roster is read, a nurse on probation's row sits below the counted nurses under an "On probation" heading, with her preceptor's name: the manager's grid, My roster for every nurse of the unit, the print page, the Excel file and the CSV. The totals those pages and files show (nurses on a shift each day, headcounts) leave her out. My month names her preceptor and her probation's last day for her, and names the nurse on probation for her preceptor. Each month reads by its own state: she is under the heading in a month she is on probation in, and among the counted nurses from the month after it ends. Spec: `.scratch/nurse-rostering-v2/specs/probation.md`; the words: `GLOSSARY.md` (Nurse on probation, Preceptor).

**Blocked by:** 55 Probation: the preceptor, and the solve

**Status:** ready-for-agent

- [ ] The roster reads (the manager's grid, My roster, the print page) carry, per row, whether she is on probation in that month and her preceptor's name, and order her rows last under the heading
- [ ] The Excel file and the CSV show the same heading and order; their totals and the pages' totals leave her out
- [ ] A version in force planned before a probation changed (an end or extension not yet re-planned) is shown as it was planned, with the roster page's line from ticket 55
- [ ] My month for a nurse on probation: her preceptor (or that none is assigned yet) and her probation's last day; for a preceptor: the nurse on probation she is paired with; nothing of either for anyone else
- [ ] A colleague reads no more of her than the heading, her preceptor's name and her cells, as My roster shows any row; her leave is still the same empty cell as a day off
- [ ] The heading and the preceptor's name read well on a phone and to a screen reader (a row group with its own name), held against `better-interface`, `better-writing` and `better-accessibility` by hand
- [ ] Tests at the web API seam (the reads and both files, month by month across a probation's end, each role) and the frontend app-level suite (the heading on the grid, My roster and the print page; My month for both nurses); six runs at once
- [ ] `docs/ARCHITECTURE.md`'s exports and roles sections say so; the OpenAPI document and the generated client regenerated

## Comments

**From ticket 54 (2026-11-11).** A probation's last day is `nurses.probation.last_day(nurse)`, derived and never stored. `probation.running(nurse)` says whether it is over on the hospital's clock. Whether she is on probation in a given month is `on_probation_in(nurse, month)`, which a roster read of a past month needs, since `running` is about today.
- `NurseRow.probation` (Nurses page) and `NurseAttributesRow.probation` (Rostering attributes) are empty once a probation is over.
- The staff list has the import's "On probation" column ("Yes", or empty) and "Probation's last day".
- My month's last day for her should read the same function.

**From ticket 55 (2026-11-12).** Who precepts whom, month by month, is `nurses.preceptors`:
- `preceptors.assignment_in(nurse, month)` is the assignment in force that month (None outside her probation, before the first,
  or after a leaving ended it); `preceptors.spans(nurse, since)` groups it into runs of months, as the Rostering attributes row
  shows ("Preceptor: Amal Hassan, December 2026 to March 2027"). For a roster, read the month's solve input instead
  (`row.get("on_probation")`, `row.get("preceptor")`): it is what the solve and the checks read, and it leaves out a preceptor
  who is not in the month or is herself on probation.
- The headcounts the app works out itself already leave her out in the cover list's "already full" and the Day view's counts and
  overtime (`covers.judging.CoverMonth.full`, `rosters.day._figures`). The sheets' totals (grid, print page, Excel, CSV) are yours:
  read `on_probation` off the month's input, as those two do.
- The Day view lists her on her shift and counts her toward nothing, so its `present` and its list of names can differ by her.
  The "On probation" heading is yours to add there if it is wanted.
- The swap and cover refusals say "Faten Ali is on probation in June 2026, so a swap cannot change their cells" and "…works beside
  her preceptor, Amal Hassan, on their day shifts", on the strength of your heading. They show on My roster only once your
  "On probation" heading with her preceptor's name is there.
- My month for both nurses: `assignment_in(nurse, month).preceptor` for her, and for the preceptor, the nurse whose assignment in
  force names him (`PreceptorAssignment.objects.filter(preceptor=…)`, then `assignment_in` on each row's nurse, as
  `preceptors.precepted_in` does).
