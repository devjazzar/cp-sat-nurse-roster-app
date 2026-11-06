# 15: Nurse's own month and in-app notifications

**What to build:** Every user has a notification bell. A nurse is told when her roster is approved, rejected (manager only) or changed, when a window opens, when a request or swap moves a step; a manager when a solve finishes or something awaits him; an approver when a roster is submitted. A nurse also sees her own month: hours worked, overtime, hours balance and shift counts, and can change her password.

**Blocked by:** 14 Submit, approve, reject

**Status:** ready-for-agent

- [x] Notification model and bell with unread count, list, mark read
- Events emitted:
  - [x] roster submitted, approved, rejected
  - [x] solve finished
  - [ ] roster changed: ticket 16 calls it (comment there)
  - [x] window opened, request decided: ticket 19 (comment there)
  - [ ] swap step reached: ticket 20 (comment there)
- Nurse's own summary from the result in force:
  - [x] hours, overtime, what is carried, shift counts (with My leave taken in)
  - [x] requests and their status: ticket 19 (a slot on My month, comment there)
- [x] Change own password for every role (it was there already: a test now holds it for each role)
- [x] API tests cover each event's recipients and the summary

## Comments

**From ticket 10 (2026-11-05).** A nurse reads their own leave on the page My leave (`/my-leave`, `GET /api/nurses/my-leave`), which their home links to because it had nothing else to show. This ticket's own month should take it in, and keep the type there. Keep the endpoint or its equivalent open to a unit manager: one with a nurse profile and no unit has no other way to read theirs. Hold ticket 14's rule on anything a notification says: a roster change must not tell colleagues that a change was leave.


**From ticket 14 (2026-11-05).** The three roster events have one place each: `rosters.api.submit_roster`, `approve_roster` and `reject_roster`, each inside its transaction after the audit entry. Recipients as the ticket says: submitted to the CNO and the Deputy CNO; approved to the manager and every nurse of the unit's month (`membership.placed_in`, which includes a nurse due to join); rejected to the manager only. **The rejection's comment can name a nurse and their leave, so it must not reach a nurse's notification**, nor the System Admin. A nurse's month is already readable at `GET /api/rosters/mine` (`rosters.reading_api.my_roster`), which builds every colleague's row from the version in force and nothing else; any summary added here must keep to that for colleagues. A nurse's home links to My roster and speaks of this month only.


**Implemented on 2026-11-06,** on branch `claude/ticket-15-notifications-df5fcc`. The backend ran under pytest on a throwaway PostgreSQL 18 container of my own, and the frontend under Vitest with the real routes and generated client over a stubbed `fetch`.

- Results on the final code: backend 1713 passed, frontend 449 of 449, and `npm run build` clean.
- `makemigrations --check` is clean, and `frontend/openapi.json` is the same as a fresh export.
- The frontend suite also ran in **6 clean exports of the final commit at once**: 449 of 449 in each.
- The solver's suite was not run: nothing under `solver/` changed.

What was built:

- **`notifications` app.**
  - `Notification` holds a user, an event, a payload and `read_at`. Migration: `notifications.0001_notification`.
  - **One way to emit:** `notifications.sending.notify(users, event, **payload)`. It tells each active user once, and skips `None` and deactivated users. Each event that exists has its recipients next to the others in that module.
  - `notifications.reading` works out the words and the link **when they are read**.
  - The endpoints, under `/api/notifications`:
    - `GET /unread` is what the bell polls.
    - `GET ""` returns the latest 50.
    - `POST /{id}/read` and `POST /read-all` mark them read.
  - None of them takes a user, so every role reads its own and nobody else's. Someone else's notification gives the same 404 as one that does not exist.
- **The four events that exist today:**
  - Each is emitted inside the transaction of its change, after the audit entry: `submit_roster`, `approve_roster` and `reject_roster` in `rosters.api`.
  - A solve's end is emitted in `solves.running._finish`, and on every failed path through the new `_fail`, which `end_what_the_queue_lost` also uses.
  - The words say only the unit, the month, who did it, and how a solve ended.
- **The bell** is in every role's header, beside the username. It is a link to the Notifications page, whose accessible name carries the count ("Notifications, 3 unread"). It polls `GET /api/notifications/unread` every 30 s, and every 10 ms in tests.
- **Notifications page** (`/notifications`):
  - Newest first, with "New" on the unread ones and a status line with the count.
  - Following a notification's link marks it read. A notification with no link has "Mark as read", and the page has "Mark all as read".
  - Focus goes to the status line when either button goes.
- **My month** (`/my-month`, `GET /api/rosters/mine/month`) takes in My leave:
  - The reader's hours worked, the leave counted as worked, the hours the month asks of them, overtime, what is carried into next month (owed or worked ahead), and the count of each shift.
  - Beside them, their leave with its type, from `GET /api/nurses/my-leave`, which stays open to a unit manager.
  - `/my-leave` now leads to `/my-month` and keeps its month.
  - The nurse's header reads Home, My month, My roster.
  - The home page and the Leave page's line for a manager with no unit now point to My month.

Seams:
- `notifications/tests/test_events.py` (15 tests): who is told of each event, through the real endpoints, with the scripted solver and the real worker's code.
- `notifications/tests/test_reading.py` (13 tests): reading, marking read, and the idle limit.
- `rosters/tests/test_own_month.py` (14 tests): **expected values worked by hand** from `fixtures/sound_rosters.json`. Amal's June is 17 shifts of 12 h, which is 204 h worked, against 26 days that are not Fridays at 8 h, which is 208 h owed. They are not taken from the code.
- `accounts/tests/test_login.py`: every role changes its own password.
- `app.test.tsx`: 21 new tests, and the new pages added to the route guards.
- The code came before most of the backend tests, so **I broke each guard by hand and saw its test fail**. That covered the deactivated-user skip, the de-duplication, a rejection told to nurses, a failed solve not told, a solve told to its starter instead of the unit's manager, the poll counted as activity, the poll's refusal counted as activity, the bell going on after a refusal, following a link without marking it read, and the status line's focus.
- **The test harness:** `start` in `app.test.tsx` now answers the bell's poll by default (`NO_BELL`). The two tests that compared a page's whole list of requests filter it out (`pageReads`). One import test replaced `fetch` for every address; it now holds only the import's request, because the bell's poll was taking its place.

**Driven in the built-in browser,** on scratch project `nr-t15`:
- The setup:
  - It ran the production compose file with its own image (`nr-t15-app`), secrets and volumes.
  - `web` was published on `127.0.0.1:18015` under `DJANGO_DEBUG`, with no Caddy, and the real solver and worker.
  - The unit was the solver's four-nurse sample as ER, rostering December 2026.
  - Everything has been removed since.
- **As the manager:**
  - A real solve of 15 s, cost 127. **The bell turned to "1 unread" on its own** about 30 s later, with no reload.
  - Opening the notification led to the Roster page for December, and the bell cleared at once.
  - A real submit.
- **As the Deputy CNO:**
  - The bell had 1 unread: "Mona Ali submitted the ER roster for December 2026."
  - Its link led to the unit roster.
  - **A real rejection, with a comment naming Badr and his sick leave.**
- **The database after the rejection:**
  - The solve's end went to the manager, the submit to the CNO and the Deputy CNO, and the rejection to the manager only.
  - No payload held "sick" or "Badr".
- **As the manager:**
  - "Dina Deputy rejected the ER roster for December 2026. The comment is with the draft."
  - "Mark all as read".
  - A real resubmit.
- **As the CNO:** two "submitted" notifications. The newest led to the roster, and a **real approval** followed.
- **As Amal:**
  - Her bell held only the approval, which led to My roster. Nothing reached her about the rejection.
  - My month for December read 216 h worked, 216 h owed, no overtime, nothing carried, 3 Day and 15 Night. That is **exactly the real solver's own `nurses` block for her** in the stored result.
  - After one day of sick leave on 1 December, a day she works, it read:
    - 204 h worked, 8 counted as worked, 208 owed, 4 hours owed into January, and 14 Night.
    - Leave won over the shift.
    - Sick showed with its type in the Leave card.
  - No sideways scroll at 375 px. `/my-leave?month=2026-12` landed on My month for December.
- **As the System Admin:**
  - The forced password change page has no bell, so nothing polls there.
  - After the change, the bell read "Notifications" and the page said "You have no notifications".
- **The database at the end:** every staff nurse had exactly one notification, the approval. The System Admin had none.

That run found one bug, fixed with a test: **"Mark all as read" went away when pressed, and focus fell to the page's body.** It now goes to the status line, and so does focus from "Mark as read".

What was NOT checked:

- **That polling leaves the idle limit alone, in the browser.** API tests hold it, the same way ticket 11's do. The real 12 hours were not waited out.
- **Dark mode, 320 px, 200% zoom, RTL, a screen reader, and browsers other than the built-in one.** The bell's accessible name and the status line were read from the accessibility tree, and not heard.
- **Through Caddy.**
- **A failed solve, a solve with no roster, and one stopped with the best roster kept, in the browser.** These are API tests, and their words were not seen on the page.
- **A large unit or many notifications.** The list shows the latest 50, and nothing is ever deleted.
- **The dev stack was not touched:** no restart, no migration, no login. When this branch reaches `main`, `web` and `worker` there need a restart for `notifications.0001`. Until then the bell's poll fails, and so does every roster decision and solve end, since they write notifications.

**Decisions taken here:**

- **Worth your review: the words are worked out when read, and the payload holds identifiers only.** It keeps a unit, a month, who did it, and a solve and how it ended. Never a comment, a nurse or a leave.
  - So the words follow a renamed unit or a corrected name.
  - The payload keeps no version number, since a later version would make "version 1 is in force" untrue. The review found this.
- **Worth your review: what awaits a manager today is a rejection.** Requests waiting for a decision (ticket 19) and swaps that all colleagues accepted (ticket 20) are the rest, and those tickets add them.
- **Recipients:**
  - **Submitted** goes to the CNO and the Deputy CNO, so two approvers are each told.
  - **Approved** goes to the unit's manager and every nurse of the month (`membership.placed_in`). That includes a nurse due to join, who can read the month on My roster, but no nurse of another unit.
  - **Rejected** goes to the manager only. The comment stays on the roster, and a test searches every payload for it.
  - **A solve's end** goes to **whoever manages the unit when it ends**, read again then. A manager taken off the unit since starting it is told nothing, since its pages are no longer theirs. The new manager, who now has the draft, is told.
- **Edge cases:**
  - A deactivated user is told nothing.
  - A manager who is also a nurse of the month is told once, with the manager's link.
  - A unit with no manager tells nobody of a rejection or a solve's end, and tells its nurses of an approval.
- **The links come from the reader's role and what they hold now:**
  - An approver goes to the unit roster.
  - A manager of the unit goes to their Roster page.
  - A nurse, or a manager who is a nurse elsewhere, goes to My roster for an approval.
  - A manager since taken off the unit gets the words and no link.
- **The System Admin** has the bell, since the ticket says every user has one. Nothing is ever sent to them, because they see no roster. They cannot read anyone else's notifications, as nothing takes a user. A test runs a whole rejection and approval and finds none for them.
- **A queued solve that the manager stops sends nothing,** since they did it themselves on the page that says so. A running solve that is stopped ends in the worker and tells them, because its best roster becomes the draft some seconds later.
- **The poll is not activity.** The poll's auth, `notifications.api.Polled`, calls `accounts.sessions.not_activity` before checking anything, so **a refused poll is not activity either**. That includes the 403 of a forced password change, which a test holds. Reading the list and marking read are activity.
- **On the page, a refusal of any kind (status below 500) stops both the interval and the refetch on window focus.** A test reads the query's own options, as ticket 11's does. A 401 ends the session and goes to the login page through the existing query client.
- **The own month is worked out, not read from a stored result.**
  - It runs `assemble(unit, month)` and the solver's own `Problem.required_hours`, `leave_credit` and `carry_over` against the reader's row of the latest version. This is the arithmetic of a result's `nurses` block, and the browser run matched one exactly.
  - A stored result is the solve's grid. It would not follow hand edits or later versions, and it holds every colleague's leave.
- **Leave wins over a shift in the hours.** A shift the version still holds on a day of leave recorded since is not counted as worked, because that day already counts through the leave credit. The review found this, and ticket 16 has the version that takes the shift off.
- **Which months:**
  - Before approval, My month says "No roster yet … Your hours show here once it is approved", and still shows the leave.
  - **A month already over shows its leave and no hours,** as My roster shows no month before this one. Ticket 21 has a comment.
  - Each new version (ticket 16) is read as it comes, and a test makes a version 2 by hand to hold this.
  - Leave recorded since counts at once. What is carried says it is worked out again at the month close.
- **Worth your review: a nurse sees the hours the month asks of them.** That figure is lower for a Ramadan-reduced or breastfeeding nurse. The glossary says nurses never read their rostering attributes, and this shows their effect on their own hours only, never the flags, and never to a colleague. The ticket asks for the balance and overtime, which mean nothing without it.
- **Nothing of a colleague** reaches My month. One test compares the whole answer before and after a colleague's leave. Another finds no colleague's name in it.
- **Change own password:** the header link and the endpoint were there already for every role. Only a test for each role was added.
- **Worth your review:** "Mark all as read" marks everything unread, including any past the 50 shown and any that arrived since the page loaded. A manager with a nurse profile still has no link to My month in their header, as ticket 14 kept for My roster. It is open to them at its address, and a test holds it.

**Review.** The `code-review` skill's two axes against `0805a78`.

Spec found:
- "Version n is in force", which a later version would make stale.
- A shift on a day of leave counted twice.
- The bell asking again on window focus after a refusal.
- No test of a manager with a nurse profile on My month.
- A shift retired since making the hours vanish. A shift a unit's rules name cannot be retired, so this cannot happen. Hours are now read from the catalogue anyway.

All fixed, apart from the last. It also raised the queued solve stopped by hand, mark-all, and later events extending `reading`'s match blocks; all three are taken as above.

Standards found:
- "account", a word the glossary says to avoid, in a docstring.
- The solve's outcomes as bare strings, now `SolveOutcome`.
- The link's fields copied twice.
- A middle man, `names_for`.
- Code shared by My roster and My month, now `_InForce.heading()` and `.approved_at`.
- A guard defined mid-module.
- Missing type hints and import order.
- Frontend nits.

All fixed. Kept as judgement calls: each new event touches `Event`, `sending` and `reading`, which `Event`'s docstring says, and the `LINK` class string defined per page, as other pages do.

`better-interface` and its domain skills, by hand from the code and the run:
- The bell is a 36 px link with the count in its name, and the badge is hidden from the accessibility tree.
- The Notifications page's status line announces the count, and takes focus from the buttons that go.
- My month keeps h1, then the month's h2, then the cards' h3.
- The copy uses the glossary's words: Notification, leave, version, roster.
- `interface-review` is yours to invoke.

**Things later tickets should know:** comments are on 16, 19, 20 and 21. `docs/ARCHITECTURE.md` sections 4 and 8 and the glossary's new Notification entry say where this sits.

**Reviewed by the user (2026-11-06), and kept as built:**
- An approval's notification carries no version number, since its words are worked out when it is read.
- What awaits a manager today is a rejection only.
- A nurse sees the hours the month asks of them, which a Ramadan or breastfeeding reduction lowers, without the reduction being named.
- "Mark all as read" also marks notifications beyond the 50 shown.
- A manager with a nurse profile has no link to My month in their header.
