# 15: Nurse's own month and in-app notifications

**What to build:** Every user has a notification bell. A nurse is told when her roster is approved, rejected (manager only) or changed, when a window opens, when a request or swap moves a step; a manager when a solve finishes or something awaits him; an approver when a roster is submitted. A nurse also sees her own month: hours worked, overtime, hours balance and shift counts, and can change her password.

**Blocked by:** 14 Submit, approve, reject

**Status:** ready-for-agent

- [ ] Notification model and bell with unread count, list, mark read
- [ ] Events emitted: roster submitted, approved, rejected, changed; solve finished; window opened; request decided; swap step reached
- [ ] Nurse's own summary from the result in force: hours, overtime, balance, shift counts, requests and their status
- [ ] Change own password for every role
- [ ] API tests cover each event's recipients and the summary
