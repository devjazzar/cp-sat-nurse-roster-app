# 03: A nurse's skills

**What to build:** The CNO records each nurse's skills on the Nurses page, with an expiry where the catalogue says the kind expires, renews one by changing its expiry, and takes one off. Her unit manager (and the manager of a unit she is due to join) and the Deputy CNO read them; she reads her own with their expiries on My month; nobody else does. They follow her across a transfer, stay when she is deactivated or ends, and are the CNO's for a manager with a nurse profile too. The audit log says whose skills changed and by whom, never which skill or date. Turning a catalogue skill's "expires" on is refused, naming the nurses, while a record of it has no date.

**Blocked by:** 02 The skill catalogue

**Status:** ready-for-agent

- [ ] A nurse skill row: nurse, skill, expiry (null for a non-expiring kind), recorded by and when, removed by and when; at most one current row a nurse and skill; a correction or removal ends the row, as leave does.
- [ ] A record of an expiring kind is refused without an expiry, one of a non-expiring kind with one; a retired skill can be neither recorded nor renewed, but a record of it stays.
- [ ] The CNO sets, renews and removes on the nurse's row of the Nurses page; the unit manager reads them on his nurses' rows (his unit, and a nurse due to join), the Deputy CNO on any unit's; a Staff Nurse and a manager with a nurse profile read their own on My month; the System Admin never.
- [ ] Changing "expires" from off to on in the catalogue is refused while any current record of that skill lacks an expiry, naming the nurses; off again is allowed and the dates kept.
- [ ] Audit: `nurse.skills_changed` with whose and by whom only.
- [ ] The architecture document's roles table (CNO sets skills; managers and Deputy CNO read; the nurse reads her own) and the nurse profile entry say so.
- [ ] Tests at the web API seam: each role's reading and writing, the refusals, a transfer, a deactivated nurse, the audit entry's shape; frontend tests for the Nurses page controls and My month.
