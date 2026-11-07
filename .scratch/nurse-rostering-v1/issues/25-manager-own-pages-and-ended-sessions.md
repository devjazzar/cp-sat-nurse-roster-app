# 25: A manager's own pages, and a session that ends

**What to build:** Two fixes to problems ticket 24's browser checks found.

- A unit manager who is also on the roster can reach their own roster and month from the app's links, not only by typing the address.
- When a session ends behind the user's back, the app says so. It does not ask a question that can no longer be acted on, and it does not call an approved roster "the draft".

**Blocked by:** 24 Browser smoke journeys

**Status:** ready-for-agent

- [ ] A unit manager with a nurse profile has **My roster** and **My month** in the header (the wide header and the phone Menu) and on Home, the same links a staff nurse has.
  - A manager without a nurse profile has neither link.
  - The manager gets no request or swap links. Those are staff nurses' alone, since only staff nurses' cells are swapped (`docs/ARCHITECTURE.md`, swaps).
  - The pages themselves already admit the manager (`onlyFor(staff_nurse, unit_manager)`); only the links are missing.
- [ ] The roster page's unsaved-changes question names the month rather than "the draft", so it reads right for a **Draft** and an **Approved** roster alike: "Your changes to June's roster are not saved yet. If you leave, they are lost." The same holds for the line beside the Solve button, "Save or discard your changes to the draft first…", wherever it can show on an approved roster.
- [ ] A session that ends behind the user's back goes straight to the login page, on any page, with no "Leave without saving?" question first. Behind the user's back means a 401 while the app believes someone is signed in (`frontend/src/router.tsx`, `sessionCheck`): the 12-hour idle limit, a deactivated account, or a password changed elsewhere. Staying on the page can save nothing without a session.
- [ ] The login page then says: "You were signed out. Changes you had not saved are lost. Sign in to carry on."
  - It gives one message whatever the cause; the browser cannot tell which it was.
  - It shows only after a session that ended this way. Never after Log out, a wrong password, or a first visit.
  - It goes once the user signs in.
- [ ] Unsaved edits are not kept: nothing of a roster is stored in the browser to be offered back after the next login (shared ward computers).
- [ ] Signing in after a session ended goes back to the page the user was on, if their role may still open it, otherwise to Home. A plain login still goes to Home, as now.
- [ ] `docs/ARCHITECTURE.md`'s screens-per-role paragraph says a unit manager with a nurse profile also has My roster and My month, and says what happens when a session ends.
- [ ] Tests:
  - Vitest for the manager's links (with and without a nurse profile), the month-named question, the straight redirect, the login message and when it shows, and the return to the page;
  - one Playwright check added to ticket 24's checks (`e2e/`): the manager-nurse opens My roster and My month from the links; a session ended under an edit (a manager deactivated, as ticket 24's check does) lands on the login page with the message and no question; and signing in again returns to the page.

No new ADR and no new glossary term. The words are the glossary's: **Draft**, **Approved**, **Nurse profile**, **Unit Manager**.

## Comments

**Decided with the user (2026-11-07),** grilling ticket 24's two findings against the docs. All eight questions were answered with the recommendation:
1. both links, only with a nurse profile;
2. one wording naming the month;
3. no question when the session has ended, straight to login;
4. no browser copy of unsaved edits;
5. one login message, no reason;
6. on any page, never after Log out;
7. back to the page after signing in, if the role may still open it;
8. this one ticket, with the architecture paragraph and one browser check.

**From ticket 24 (2026-11-07).** How the findings were seen:
- The manager-nurse's pages were opened by address in the checks, since nothing links to them.
- When a deactivated manager saved, the app went to the login page. The roster page's guard asked first, "Leave without saving your changes? Your changes to the draft are not saved yet …", on an approved roster, and the login page then said nothing.
- `e2e/tests/journey/after/races.spec.ts` and `e2e/support.ts` (`signIn`, `go`) have what the new check needs. Run the checks with `e2e/ci.sh`, or with two stacks of your own as `README.md` says.

**Spec (2026-11-07):** `.scratch/manager-own-pages-and-ended-sessions/spec.md`, written with `/to-spec` on three seams the user agreed:
1. the API's `Me` gains `has_nurse_profile`;
2. the frontend's app-level Vitest suite as the main seam;
3. ticket 24's Playwright race check, "a manager deactivated while editing…", rewritten for the new behaviour, plus one step opening My roster and My month from the links.

The spec also requires that the page to return to is an address inside the app, never a full URL.
