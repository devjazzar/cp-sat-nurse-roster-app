# 03: Management accounts and the audit log

**What to build:** The System Admin creates the CNO, the Deputy CNO and unit manager accounts, each shown its generated password exactly once, deactivates accounts and resets passwords. Exactly one CNO and one Deputy CNO can exist. Every role lands on a navigation scoped to what it may do, and every API endpoint checks the caller's role through one authorization layer that later tickets reuse. The System Admin reads the audit log with filters by user, action and date.

**Blocked by:** 02 System Admin's first run

**Status:** ready-for-agent

- [ ] Create CNO, Deputy CNO, Unit Manager accounts; generated password shown once; forced change at first login; a second CNO or Deputy CNO is refused
- [ ] Deactivate and reactivate an account; reset its password (shown once)
- [ ] Role-scoped navigation and home page for every role; the System Admin creates no nurse and sees no roster
- [ ] One authorization layer applied to every endpoint, with API tests that each role gets 403 where it has no business
- [ ] Audit log page with filters by user, action and date; every account change is audited
- [ ] API tests cover account creation, cardinality, deactivation, reset and the audit log
