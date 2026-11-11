# 55: Probation: the preceptor, and the solve

**What to build:** The unit manager assigns a nurse on probation her preceptor from a chosen month on, on her row of the Rostering attributes page, and may change it: the list offers only nurses of the unit who hold a skill marked "Lets a nurse precept" that has not expired on the day of assigning, are not on probation in those months, and precept no other nurse in any of them; the current month can be chosen only while its roster is not approved. The assignment ends with the probation, with the preceptor's last month in the unit (a transfer or an end date, and the manager is notified to choose another) and with the nurse on probation's own transfer; a skill that expires later ends nothing. Both nurses are notified when a preceptor is assigned or changed. From here on the roster follows: every solve input, a re-plan's and a close's included, marks each nurse on probation in that month and names her preceptor, so the solver (ticket 52) rosters her on day shifts beside her preceptor and counts her toward nothing; a nurse on probation with no preceptor is still rostered, and the solve's warnings name her. On an approved roster a swap or a cover that would break the following rule is refused, she can neither propose a swap nor be part of one, she is never offered a cover, and every headcount the application works out itself leaves her out. Spec: `.scratch/nurse-rostering-v2/specs/probation.md`; the words: `GLOSSARY.md` (Preceptor, Nurse on probation); the reasons: ADR 0014.

**Blocked by:** 52 The solver rosters a nurse on probation; 53 The skill catalogue's "Lets a nurse precept" mark; 54 Probation on a nurse: the tick, the length and the end

**Status:** ready-for-agent

- [ ] A preceptor assignment: from a month on, which nurse precepts her; the latest that has begun is in force, as a placement is; a manager with a nurse profile may be the preceptor
- [ ] Assigning and changing on the Rostering attributes row, behind its question, with each refusal said: another unit in that month, no marked skill unexpired today, on probation in those months, already precepting in any of them, a month whose roster is approved
- [ ] The assignment ends with the probation (ended, extended or run out), with the preceptor's transfer or end date (the manager notified to choose another), and with the nurse on probation's own transfer; a preceptor's skill expiring later ends nothing
- [ ] Notifications to both nurses when a preceptor is assigned or changed, once each
- [ ] The solve input, a re-plan's and a close's included, marks her on probation month by month across a probation's start and end, and names her preceptor when one is in force and in the input; a stored input without the fields still reproduces; "changes since" reports a changed probation or preceptor
- [ ] An end, an extension or an unticking that touches a month whose roster is approved changes nothing in it; the roster page says how it was planned and offers the re-plan
- [ ] A real solve on a scratch stack: she is beside her preceptor on every day shift her hours hold, works no night, every headcount is met without her, and the draft's per-nurse explanation says which of her preceptor's day shifts she did not follow; with no preceptor the solve's warnings name her
- [ ] Swaps: she cannot propose one or be a colleague in one, and is told why; a swap that takes her preceptor off a followed day shift is refused, the proposer told only what My roster would show. Covers: she is never listed or offered; one that would break the rule is refused. A manager's edit shows the violation; a re-plan keeps her beside her preceptor
- [ ] The headcounts the application works out itself (the approved roster's judging, the cover list, the Day view if it is built) leave her out, with the solver's own reading
- [ ] Requests and preferences are hers as any staff nurse's; the request form offers her allowed day shifts only; an accepted day off holds over following
- [ ] Audit entries for each assignment and its end, with their values
- [ ] Tests at the web API seam (each refusal, the endings, the notifications, the solve input month by month, a swap and a cover refused, her absence from the cover list, a few end to end with the real solver in process) and the frontend app-level suite (the row's preceptor control, the swap page's explanation); six runs at once
- [ ] `docs/ARCHITECTURE.md` names the assignment in the domain model, the fields in the solve input, the notifications and the swap and cover rules; the OpenAPI document and the generated client regenerated; the migration

## Comments

**From ticket 53 (2026-11-11), the mark this ticket reads.** `hospital.models.Skill.lets_a_nurse_precept` (API field
`lets_a_nurse_precept` on `listSkills`). A nurse qualifies through her current records, `NurseSkill.objects.current()`,
of a skill with the mark on, unexpired on the day of assigning; read `expiry` only when the skill's `expires` is on (ticket
33's rule), and decide whether a retired marked skill still qualifies (the spec does not say). The mark is read when
assigning only: clearing it is never refused and must end no assignment, and the Skills page tells every role so.
`hospital/tests/test_skills.py::test_the_mark_is_cleared_while_a_nurse_holds_the_skill` is the place to extend once a
preceptor exists: clear the mark on a skill someone precepts by, and the assignment stands.
