# 20: Swaps

**What to build:** On an approved roster a nurse composes a swap: a set of cell changes on her own cells and on colleagues' cells needed to make it work, for dates not yet passed. It is refused at once if the resulting grid breaks a hard rule. Every involved colleague accepts or rejects; one rejection ends it. When all accept, the unit manager sees before and after, the re-run validation and the cost change, and approves (the cells become pinned cells in a new version in force) or rejects. The proposer may withdraw; a proposal expires when a date passes or a new version changes one of its cells. Everyone involved is notified at each step and every swap stays on record.

**Blocked by:** 16 Changes after approval; 15 Nurse's own month and notifications

**Status:** ready-for-agent

- [ ] Swap composer for a nurse: pick cells of herself and colleagues in her unit, choose new values; validation at proposal refuses hard violations with the reason
- [ ] Participants accept or reject; states pending, awaiting_manager, approved, rejected, withdrawn, expired
- [ ] Manager decision view with before/after, validation and cost change; approval writes pins with origin 'swap' as a new version with origin 'swap'
- [ ] Hourly expiry job; expiry also on a new version touching the cells
- [ ] Notifications at each step; audit entries; a nurse sees her swaps and their status
- [ ] API tests cover composition, refusal, acceptance paths, manager decision, expiry and authorization
