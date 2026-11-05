# 07: Nurses, one at a time

**What to build:** The CNO adds a nurse: hospital ID, full name, gender, unit and start date. Her account is created with the hospital ID as username and a generated password shown once; at first login she must change it and then sees her unit's roster page with "no roster yet". The CNO transfers a nurse to another unit effective from a chosen month, sets an end date to deactivate her, and the CNO or her unit manager resets her password. Nurses are never deleted.

**Blocked by:** 06 Units and managers

**Status:** ready-for-agent

- [ ] Add a nurse creates the user, the nurse profile and the password shown once; hospital ID unique
- [ ] A unit manager may also be given a nurse profile by the CNO; role stays Unit Manager
- [ ] Transfer with an effective month; end date deactivates; no delete endpoint
- [ ] Password reset by the CNO for any nurse and by the unit manager for his unit's nurses only
- [ ] Staff nurse home shows her unit and 'no roster yet'
- [ ] Unit manager sees his unit's nurse list; names and shifts only is enforced for nurses from the start
- [ ] Archiving a unit is refused while a nurse belongs to it: `Unit.nurse_count` counts real nurse profiles (see ticket 06's comments)
- [ ] A nurse's unit is in `units.scope`, so unit-scoped endpoints resolve it for her (see ticket 06's comments)
- [ ] API tests cover creation, uniqueness, transfer, deactivation, resets and scoping
