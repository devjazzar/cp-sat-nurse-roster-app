# 02: System Admin's first run: login, forced password change, health and technical settings

**What to build:** The System Admin's account is created on first start from the one-time password in the environment. They log in on the SPA's login page, are forced to change the password, and land on their home: the health page (solver reachable, queue state, disk and database size, last backup placeholder) and the technical settings (time limit cap, backup time and retention, month close time) with the agreed defaults. Accounts lock for fifteen minutes after five failed logins, sessions expire after twelve idle hours, and every login and failed login is an audit entry.

**Blocked by:** 01 Foundation

**Status:** ready-for-agent

- [ ] First start creates the System Admin from the environment variable with must-change-password set; the variable is ignored on later starts
- [ ] Login page, logout, forced password change at first login with the policy (minimum 10, common-password and similarity checks)
- [ ] Lockout after 5 failed logins for 15 minutes; sessions expire after 12 idle hours
- [ ] Every login and failed login writes an audit entry
- [ ] Health page shows solver reachability, queue state, disk and database size
- [ ] Technical settings page edits the time limit cap (default 300 s), backup time and retention (02:00, 30 days) and close time (00:30), audited
- [ ] API tests cover bootstrap, login, lockout, forced change, settings and that a non-admin cannot read or change technical settings
