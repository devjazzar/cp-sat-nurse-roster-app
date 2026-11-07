# 03: After a solve: warned and told when the dates change

**What to build:** When a month's Ramadan days or public holidays change after a solve, a unit manager's draft is warned that they changed since its solve, blocking nothing, as after a correction to leave; a submitted roster shows the reviewer that something changed since it was submitted; and every unit manager whose unit has a draft, a submitted or an approved roster in a month touched is told once, naming the month, from the transaction that makes the change. Approved cells, versions and pins stay; the next solve or re-plan uses the dates as they stand, as today. The change may come from the month fixed or returned to the calendar in the table, from a holiday created, changed or removed, or from the cards of tickets 01 and 02, which write through those same operations. Spec: `.scratch/ramadan-and-eid-from-the-calendar/spec.md`.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] The draft's "changed since its solve" list gains two month-level changes, the month's Ramadan days and its public holidays, each the stored solve input's list compared with the month as it stands, carried with no nurse; the per-nurse changes are as before
- [ ] The draft page words them ("The Ramadan days of March 2027 changed since this draft was solved", and the same for the public holidays); submit goes through with the warning and the check on submit runs on the month as it stands, as today
- [ ] A submission records the month's Ramadan days and public holidays at submit beside the nurses it records (a migration), and the submitted roster's "changed since it was submitted" compares them too
- [ ] One new notification kind, sent to the manager of every unit with a draft, submitted or approved roster in a month whose Ramadan days or public holidays changed, once per change per month, inside the transaction that makes the change, after its audit entry; its payload is the month and its words name the month and say which changed; the one who made the change is not a recipient, nor is a manager with no roster in the month
- [ ] The existing per-month fix and "Use the calendar", and the holiday create, change and remove, send it; a change that leaves the month's dates as they were sends nothing
- [ ] API tests under pytest beside the draft's "changed since" tests and the notification events' tests: a draft and a submitted roster warned after a Ramadan change and after a holiday change, unwarned when nothing moved, submit going through; the manager of a unit with each kind of roster told once per month, a manager with no roster not told, the CNO not told
- [ ] The frontend's app-level suite: the draft page's new warning line and the notification's words; the usual full suites and `e2e/ci.sh`
