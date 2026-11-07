# Grilling prompts for the seven proposed features (2026-11-07)

One per new session, pasted as the first message. Each starts `/grill-with-docs` and gives a fresh session what it needs:
the feature, what exists today, where to look, and what not to assume. The facts named were checked on `main` at `da8e35b`.

Common tail, already in every prompt: answer by number, one recommendation per question, look facts up rather than ask,
ask before changing an agreed decision, and end with the design settled enough for `/to-spec`.

---

## 1. Cover for a sick call

```
/grill-with-docs Cover for a sick call.

Read docs/ARCHITECTURE.md, GLOSSARY.md and docs/adr/ first; they win over anything I say here. Then docs/guides/local-development.md section 4.1 for how I answer.

The feature: today, when a nurse calls in sick on a day she is rostered to work, the unit manager records leave on that day and the shift-day is simply short of its headcount, its team leader or a gender; the manager then edits cells by hand or re-plans. I want a "cover": recording leave on a worked day of the roster in force opens a cover for that cell; the app lists the unit's nurses who could take the shift without breaking a hard rule (rest, run, succession, overtime caps, allowed shifts; `web` already checks a grid in-process through the solver's validate), ranked by fairness (fewest hours this month, least overtime, not above cap); the manager offers it to one nurse or to all who could; a nurse accepts from her phone; the acceptance becomes a pinned cell in a new roster version, the way an approved swap does (ADR 0005, the Swaps lifecycle in ARCHITECTURE section 5). An unanswered cover expires when its date passes.

Facts to check yourself before asking me: how leave on a worked day already makes a new version; what the swap lifecycle, its notifications and its expiry do, since a cover should reuse them; what `solver_service.grid` answers and how fast; that nothing today lets a manager offer a shift. Questions I expect: who may open a cover and when (leave recorded by the manager only, or also a nurse reporting sick?); whether a cover can be opened for a shift-day that is short for a reason other than leave; what a nurse sees of why she was listed (nothing about colleagues, as swaps rule); first-accepts-wins or the manager chooses; what the audit log and the month close record; whether a cover can be a half measure (headcount met but no team leader); the glossary term and its avoided synonyms; whether it needs an ADR.

Answer format: numbered questions, one recommendation each, worded so "yes" takes the recommendation. Look up facts; only decisions come to me. Ask before changing an agreed decision. Stop when the frontier is empty and tell me it is ready for /to-spec.
```

## 2. Preferences, not only requests

```
/grill-with-docs Preferences: a second, soft kind of request.

Read docs/ARCHITECTURE.md, GLOSSARY.md and docs/adr/ first; they win over anything I say here. Then docs/guides/local-development.md section 4.1 for how I answer.

The feature: every request a nurse makes today becomes a hard pinned cell when accepted (ADR 0005), capped at a few a month by the unit's request cap. The vendored solver already has soft inputs the app never fills: `Nurse.desired_days` and `Nurse.undesired_days` in solver/nurse_roster/problem.py, with the soft rules `desired_day` and `undesired_day` and their weights in solver/nurse_roster/rules.py. backend/solves/input.py never sets them. I want a "preference": unlimited, made in the same request window, honoured by the solver at the rule's price rather than always, never a pin. My month shows the nurse how many of her preferences were kept; a preference broken last month weighs more this month, so that self-scheduling feels fair over time (the "rotating first access" rule the 2026 HealthStream nurse-scheduling survey says self-scheduling needs).

Facts to check yourself: how the request window, the request cap and the request form work (tickets 19 and 20 in .scratch/nurse-rostering-v1/issues); how a request becomes a pin in the solve input; what the two soft rules cost and whether the unit rules page exposes their weights; how the month close chain carries per-nurse values across months (backend/closes/chain.py, ADR 0004), since a "broken last month" weight is one more carried value. Questions I expect: whether a preference is a day off, a shift on a day, or both; whether it has a cap at all; what the manager sees and may do with them (nothing, or reject); how a re-plan treats them; whether a nurse may convert a preference into a request while the window is open; what My month shows and in what words; whether the carried weight resets at the year; glossary term and avoided synonyms ("wish", "soft request"); whether ADR 0005 needs an addendum.

Answer format: numbered questions, one recommendation each, worded so "yes" takes the recommendation. Look up facts; only decisions come to me. Ask before changing an agreed decision. Stop when the frontier is empty and tell me it is ready for /to-spec.
```

## 3. Skills and credentials per shift-day

```
/grill-with-docs Skills and credentials per shift-day.

Read docs/ARCHITECTURE.md, GLOSSARY.md and docs/adr/ first; they win over anything I say here, and ADR 0002 (the solver is vendored and frozen) is the one this feature strains. Then docs/guides/local-development.md section 4.1 for how I answer.

The feature: a shift-day today requires a headcount, a team leader and both genders (the hard rules `headcount`, `team_leader`, `gender` in solver/nurse_roster/rules.py); nothing else about who is on it. I want skills: the CNO keeps a skill catalogue (for instance ICU-certified, ACLS, preceptor), a nurse's profile lists her skills, each with an expiry date where one applies; a unit rule says "each shift-day needs at least N nurses with skill X" (per shift, as headcount is); the solver refuses to roster a nurse whose credential has expired on that day and treats a short skill as a hard or soft rule, the unit's choice as night rest is; the CNO sees credentials expiring within 90 days. Timefold, UKG and Allocate all roster by skill; the 2026 HealthStream survey found only 34% of hospitals block a nurse with an expired credential from being scheduled.

Facts to check yourself: how `team_leader` and `gender` are modelled and costed (they are "at least one with an attribute" rules; a skill rule generalises them), how the solve input assembles nurse attributes (backend/solves/input.py), what the solver's precheck and explain do with a rule, who may read and set rostering attributes (ARCHITECTURE section 3: the CNO sets gender, the manager the rest; nurses see none but their allowed shifts), and what ADR 0002 says about changing the vendored package. Questions I expect: who owns the catalogue and who sets a nurse's skills; whether a skill has an expiry at all or a credential is a separate thing; what an expired credential does to a roster already in force; whether the rule is per shift-day or per shift; hard, soft, or the unit's choice; what a nurse may see of her own skills; what the import template gains; whether this reopens ADR 0002 as a new ADR (a changed vendored solver, re-vendored under its own version) or the skill rule lives outside the solver (it cannot, if the solver is to honour it); glossary terms and avoided synonyms ("competency", which the glossary already avoids for score).

Answer format: numbered questions, one recommendation each, worded so "yes" takes the recommendation. Look up facts; only decisions come to me. Ask before changing an agreed decision. Stop when the frontier is empty and tell me it is ready for /to-spec.
```

## 4. A hospital-wide day view

```
/grill-with-docs A hospital-wide day view for the CNO and the Deputy CNO.

Read docs/ARCHITECTURE.md, GLOSSARY.md and docs/adr/ first; they win over anything I say here. Then docs/guides/local-development.md section 4.1 for how I answer.

The feature: the CNO and the Deputy CNO see rosters one unit at a time (the Rosters overview and approvals). I want one screen for one date: every unit in a row, with its headcount on each shift against the unit's required range, its team leader and gender requirements met or not, who is on leave, overtime hours so far in the month, and open covers if the cover feature exists by then. Clicking a unit opens its roster on that date. Read-only. It answers the "blind spots" the 2026 HealthStream survey found in department-only scheduling, where 57% of hospitals are.

Hard limit, not up for discussion: a nurse belongs to one unit and is never rostered on another (GLOSSARY, Unit). This view does not float anyone; if floating comes up, it is a separate feature with its own ADR.

Facts to check yourself: what the Rosters overview already shows and to whom (ticket 14 and 17 in .scratch/nurse-rostering-v1/issues); what a roster version holds per cell and what the unit rules hold per shift (headcount range, team leader, gender); what My month computes for hours and how (the solver's own arithmetic on the version in force); what the audit log records of reads; what the role table in ARCHITECTURE section 3 lets the Deputy CNO read. Questions I expect: the default date (today) and how far ahead it goes (only months with a roster in force? drafts too, marked?); whether the unit manager gets it for her own unit; whether it shows names or counts (the Deputy CNO reads rostering attributes, so names are allowed, but a wall of 300 names is not a day view); overtime per unit as a sum or the nurses above cap; what it shows for a unit with no roster that month; printing; whether it is one API read per unit or one for the hospital; glossary term; no ADR expected.

Answer format: numbered questions, one recommendation each, worded so "yes" takes the recommendation. Look up facts; only decisions come to me. Ask before changing an agreed decision. Stop when the frontier is empty and tell me it is ready for /to-spec.
```

## 5. Web push for things with a deadline

```
/grill-with-docs Web push notifications for things with a deadline.

Read docs/ARCHITECTURE.md, GLOSSARY.md and docs/adr/ first; they win over anything I say here. Then docs/guides/local-development.md section 4.1 for how I answer.

The feature: the bell on every page is the only notification; email, SMS and push were left out of v1 (ARCHITECTURE section 1 and 12). A swap to accept, a cover offered, a request window closing or a roster approved is missed by a nurse who does not open the app, and swaps expire. I want Web Push through the PWA's service worker (ticket 23: frontend/public/sw.js has no fetch listener; it registers at scope /), with VAPID keys of the installation's own, sent through the browser's push service and nothing else of ours. A payload carries no name, no date and no unit: only which kind of thing waits ("You have a swap to answer"), and tapping it opens the app's page. Opt-in per device from the notifications page. Only notification kinds with a deadline are pushed; the rest stay on the bell.

Facts to check yourself: the notification kinds and events that exist (backend/notifications, ticket 15 and 20 in .scratch/nurse-rostering-v1/issues) and which have deadlines; what the service worker does today and the no-cache rules ticket 23 put on it; that the solver network must stay without internet while web and worker may reach the push services (compose.yaml networks: backend and frontend are internal; which service would send, and through which network); iOS Safari's rules for Web Push (installed to the home screen only); the retention rules on notifications (a year). Questions I expect: which kinds are pushed; which service sends (the worker, as a job per notification, or web at write time); the key pair's storage and rotation (.env or the database); what happens when a push subscription is refused by the push service (drop it after N failures); the words of each payload; opt-in and opt-out per device and what a deactivated account's subscriptions do; what the audit log records; whether "no personal data leaves the server" needs an ADR, I think yes, a short one; glossary term for a subscription and a push.

Answer format: numbered questions, one recommendation each, worded so "yes" takes the recommendation. Look up facts; only decisions come to me. Ask before changing an agreed decision. Stop when the frontier is empty and tell me it is ready for /to-spec.
```

## 6. Compare two solves of the same month

```
/grill-with-docs Compare two solves of the same month, side by side.

Read docs/ARCHITECTURE.md, GLOSSARY.md and docs/adr/ first; they win over anything I say here. Then docs/guides/local-development.md section 4.1 for how I answer.

The feature: a unit manager who changes a weight or the time limit and solves again sees each result in full on the solve history, but never two side by side; tuning is blind. A re-plan already has a comparison (ticket 17: the cells changed, the cost of each on the re-plan's input, rule by rule, the facts that broke rules). I want the same comparison between any two results of the same unit and month from the solve history: cost per rule, the violations, per-nurse hours and overtime, and the cells that differ, with the two solves' inputs' differences named (which weight, which limit, which pins or leave changed between them). Read-only; the manager still chooses a result as the draft the way she does today.

Facts to check yourself: what a Result holds (solver/nurse_roster/result.py, backend/solves/result.py) and whether the solve input is stored with it (GLOSSARY, Solve input: it is); what the re-plan comparison computes and where it lives (backend/solves/replans.py, the frontend's replan components); who reads the solve history (the manager; the System Admin reads it without roster content, ARCHITECTURE section 3). Questions I expect: whether the comparison is between results or between a result and the roster in force; whether two results of different inputs can be compared cell by cell at all, or only by their rule costs; what "which input changed" lists; whether the Deputy CNO may read it; printing or exporting it; whether it is computed on the server (reuse of the re-plan code) or in the browser; no ADR and probably no new glossary term.

Answer format: numbered questions, one recommendation each, worded so "yes" takes the recommendation. Look up facts; only decisions come to me. Ask before changing an agreed decision. Stop when the frontier is empty and tell me it is ready for /to-spec.
```

## 7. Ramadan dates proposed from the Umm al-Qura calendar

```
/grill-with-docs Ramadan dates proposed from the Umm al-Qura calendar.

Read docs/ARCHITECTURE.md, GLOSSARY.md and docs/adr/ first; they win over anything I say here. Then docs/guides/local-development.md section 4.1 for how I answer.

The feature: the CNO types each year's Ramadan dates by hand on the Holidays and Ramadan page, and the solver applies the Ramadan reduction to the nurses marked Ramadan-reduced on those days (GLOSSARY, Ramadan days; hospital rules). I want the page to propose the dates from the Umm al-Qura calendar, the civil calendar Saudi Arabia uses, for the CNO to confirm or shift by a day, since the real dates follow the moon sighting announced the evening before. The Eid days that follow could be proposed as public holidays the same way. Nothing changes without the CNO's confirmation; what a solve used stays stored with it as now (ARCHITECTURE section 9).

Facts to check yourself: how Ramadan days are stored and edited today (ticket 09 or the hospital rules ticket in .scratch/nurse-rostering-v1/issues; the holidays page), that they have no history of their own and the audit log keeps changes; which Python library gives Umm al-Qura dates offline (the hijri-converter package does; the solver network has no internet and web should need none either); how a roster in force reacts when a Ramadan date is moved after approval. Questions I expect: propose only, or also fill in when the year's dates are empty; whether to propose Eid al-Fitr and Eid al-Adha as holidays, and how many days; what the page says when the proposal and the stored dates differ; what a change after a month is approved does (nothing to the roster; the next solve or re-plan uses the new dates; the manager is told?); whether the library is pinned like the others (ARCHITECTURE section 11); no ADR, no new glossary term expected.

Answer format: numbered questions, one recommendation each, worded so "yes" takes the recommendation. Look up facts; only decisions come to me. Ask before changing an agreed decision. Stop when the frontier is empty and tell me it is ready for /to-spec.
```
