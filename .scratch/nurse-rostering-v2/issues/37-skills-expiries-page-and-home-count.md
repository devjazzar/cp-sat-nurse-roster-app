# 37: The expiries page and the home count

**What to build:** The CNO and the Deputy CNO see every unit's skills expired or expiring within 90 days, and every nurse with no record of a skill required to work, each row with the nurse, her unit, the skill, its state and date; a unit manager sees the same for his own unit on his Nurses page. Deactivated nurses and those past their end date are left out. The CNO's home shows how many rows the page has, beside the units with no manager. There is no notification; the page is the reminder.

**Blocked by:** 33 A nurse's skills

**Status:** ready-for-agent

- [ ] One read endpoint scoped by role: the CNO and Deputy CNO every unit, a unit manager his unit; the System Admin and nurses refused. Rows: expired, expiring within 90 days of today on the hospital's clock, and no record of a required skill, for nurses active and not past their end date, oldest date first.
- [ ] An Expiries page for the CNO and Deputy CNO, linked from their pages beside Nurses; the same list on the manager's Nurses page.
- [ ] The CNO's home shows the count, worked out when read.
- [ ] The horizon is fixed at 90 days; no job, no notification, no export.
- [ ] The architecture document's screens-per-role paragraph names the page.
- [ ] Tests at the web API seam for each role, the three row kinds, the horizon's edge, a deactivated nurse and one past her end date, and the home count; frontend tests for the page and the count.

## Comments

**From ticket 33 (2026-11-09):** no page says yet that an expiry has passed: the Nurses page, Rostering attributes and My
month show "until 30 Jun 2027" and a Retired badge only, because "expired" needs the hospital's today, which this page will
compute. Records are `nurses.models.NurseSkill.objects.current()`; for a kind whose `expires` is off, ignore the kept date.
