# 06: Units and their managers

**What to build:** The CNO creates units, renames them, archives a unit that has no nurses, and assigns each unit exactly one unit manager account. A unit manager with no unit assigned can log in and sees "no unit assigned"; an assigned manager sees only his unit everywhere. The CNO reassigns a unit when its manager is unavailable.

**Blocked by:** 03 Management accounts

**Status:** ready-for-agent

- [ ] Create, rename, archive (refused while nurses belong to it) units; audited
- [ ] Assign and reassign exactly one Unit Manager account per unit; a manager account can hold one unit
- [ ] Unit manager home shows the unit or 'no unit assigned'; every unit-scoped endpoint resolves the caller's unit and refuses others
- [ ] Unit rules row seeded with the reviewed defaults and a review flag when a unit is created
- [ ] API tests cover creation, archive guard, assignment cardinality and scoping
