# 54: Probation on a nurse: the tick, the length and the end

**What to build:** The CNO ticks "On probation" when adding a staff nurse, on the form or in an optional CSV column, and may correct it later: unticking removes the probation from the first month whose roster is not yet approved, and ticking a nurse already added is allowed only while six months from her start date have not passed. Probation begins on her start date and is counted in whole calendar months, a month she joins after the 1st not counted; its last day is derived, never entered. Her unit manager works on her row of the Rostering attributes page: the length (1, 2 or 3 months, standing at 3 until he chooses), Extend (one month at a time, to 6 at most) and End (the last day becomes the last day of the month under way), each behind its question, with the last day shown. It ends by itself on its last day; at the start of her last month the unit manager is notified ("Layan Alharbi's probation ends on 31 March. Extend it or let it end."). It follows her across a transfer. The CNO and the Deputy CNO read it; the staff list says who is on probation and until when. Nothing in a roster or a solve input changes in this ticket: tickets 55 and 56 do that. Spec: `.scratch/nurse-rostering-v2/specs/probation.md`; the words: `GLOSSARY.md` (Probation, Nurse on probation).

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] The nurse profile holds her probation: on probation (the CNO's), the length in months and whether it was ended early (her unit manager's); the last day is derived from them and her start date
- [ ] The month counting, on worked dates: a start on the 1st counts that month; a start on the 15th does not (15 December and 3 months ends 31 March); February; across a year's end; a corrected start date moves it
- [ ] The CNO's tick on the nurse form and the CSV's optional "On probation" column (empty meaning no; the template updated); refused for a unit manager with a nurse profile
- [ ] The CNO's corrections: unticking applies from the first month whose roster is not approved; ticking later is refused once six months from her start date have passed
- [ ] The unit manager's length, Extend and End on the Rostering attributes row, with the refusals: a length outside 1 to 3 at first, an extension beyond 6, an extension of an ended probation; the CNO and Deputy CNO read the row, the System Admin never
- [ ] Setting her allowed shifts to the unit's night shift alone is refused while she is on probation
- [ ] It ends by itself on its last day; the notification to the unit manager at the start of her last month, once, from the hourly job
- [ ] A transfer carries the probation along, counted from her start date as before
- [ ] The staff list carries who is on probation and until when
- [ ] Audit entries for the tick, the length, an extension and an end, with their values
- [ ] Tests at the web API seam (each role, the counting, the refusals, the automatic end, the notification, a transfer, the CSV, the audit entries) and the frontend app-level suite (the form's tick, the attributes row and its questions); six runs at once
- [ ] `docs/ARCHITECTURE.md`'s roles table and domain model name the probation and who sets what; `GLOSSARY.md`'s Nurse profile entry names it; the OpenAPI document and the generated client regenerated; the migration

## Comments
