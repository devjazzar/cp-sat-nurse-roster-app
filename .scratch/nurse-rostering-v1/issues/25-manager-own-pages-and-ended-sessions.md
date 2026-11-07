# 25: A manager's own pages, and a session that ends

**What to build:** Two fixes to problems ticket 24's browser checks found.

- A unit manager who is also on the roster can reach their own roster and month from the app's links, not only by typing the address.
- When a session ends behind the user's back, the app says so. It does not ask a question that can no longer be acted on, and it does not call an approved roster "the draft".

**Blocked by:** 24 Browser smoke journeys

**Status:** ready-for-agent

- [x] A unit manager with a nurse profile has **My roster** and **My month** in the header (the wide header and the phone Menu) and on Home, the same links a staff nurse has.
  - A manager without a nurse profile has neither link.
  - The manager gets no request or swap links. Those are staff nurses' alone, since only staff nurses' cells are swapped (`docs/ARCHITECTURE.md`, swaps).
  - The pages themselves already admit the manager (`onlyFor(staff_nurse, unit_manager)`); only the links are missing.
- [x] The roster page's unsaved-changes question names the month rather than "the draft", so it reads right for a **Draft** and an **Approved** roster alike: "Your changes to June's roster are not saved yet. If you leave, they are lost." The same holds for the line beside the Solve button, "Save or discard your changes to the draft first…", wherever it can show on an approved roster.
- [x] A session that ends behind the user's back goes straight to the login page, on any page, with no "Leave without saving?" question first. Behind the user's back means a 401 while the app believes someone is signed in (`frontend/src/router.tsx`, `sessionCheck`): the 12-hour idle limit, a deactivated account, or a password changed elsewhere. Staying on the page can save nothing without a session.
- [x] The login page then says: "You were signed out. Changes you had not saved are lost. Sign in to carry on."
  - It gives one message whatever the cause; the browser cannot tell which it was.
  - It shows only after a session that ended this way. Never after Log out, a wrong password, or a first visit.
  - It goes once the user signs in.
- [x] Unsaved edits are not kept: nothing of a roster is stored in the browser to be offered back after the next login (shared ward computers).
- [x] Signing in after a session ended goes back to the page the user was on, if their role may still open it, otherwise to Home. A plain login still goes to Home, as now.
- [x] `docs/ARCHITECTURE.md`'s screens-per-role paragraph says a unit manager with a nurse profile also has My roster and My month, and says what happens when a session ends.
- [x] Tests:
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

**Implemented on 2026-11-07,** on branch `claude/ticket-25-manager-pages-sessions-4e4e16`, from `main` at `05f2259`. The suites:
- backend under pytest on a throwaway PostgreSQL 18 container of my own: 2326 passed (2320, and 6 for `has_nurse_profile`);
- frontend under Vitest: 566 passed (550 before it), 6 of 6 in six parallel `npm test` runs; `npm run build` passed;
- `e2e/ci.sh` (`E2E_CI_PREFIX=nr-t25ci`), end to end on the final head: passed in 717 s, Playwright 68 of 68 and `operations.sh` to "All checks passed" (30 `ok` lines), everything removed after. Its first run, one commit earlier, failed the rewritten race check and the two after it (below, under Review).

`makemigrations --check` is clean. `frontend/openapi.json` was regenerated from the export, and with it the client (`model/me.ts`, `zod.ts`); nothing else in the generated files moved. The solver's suite was not run: nothing in `solver/` changed.

**What was built, against the spec, point by point.**
- **API.** `Me` (the login's, the session's and the password change's answer) gains `has_nurse_profile`: whether the user has a nurse profile, of any role, read on the request's user. No endpoint, no request per page, no schema change. `accounts/tests/test_login.py` asserts it on the login and the session for a Unit Manager with and without one, a Staff Nurse, the CNO, the Deputy CNO and the System Admin.
- **Links.** A Unit Manager with a nurse profile has My roster and My month in the header, on a wide screen and in the phone Menu (both built from one list, `navigation(user)` in `roles.ts`), and on Home, under their unit's lines, whatever unit they hold. A manager without one has neither. No request or swap link is added. Other roles are unchanged (their tests are as before).
- **Wording.** The roster page's question reads "Your changes to the roster of June 2026 are not saved yet. If you leave, they are lost." on a Draft and an Approved roster alike. A check on an Approved roster with a change unsaved finds no other "draft" on the page but the page's opening lines, which say how drafts work whatever the state. "Save or discard your changes to the draft first: a solve is given only saved pins." stays: it shows only beside Start solve or Solve again, which only a month that is not submitted or approved has (`!frozen`), so the roster there is surely a draft, as the spec allows.
- **A session that ends behind the user's back** (a 401 while a user is cached, `sessionCheck` in `router.tsx`) clears the cache and the user as before, and goes to `/login` with `ignoreBlocker`, so the roster page's guard asks nothing. The guard still asks when the user leaves on purpose (the month links, Solve history; both tested).
- **The login message.** "You were signed out. Changes you had not saved are lost. Sign in to carry on." in a `role="alert"` paragraph above the form, with focus on Username (as before), and the field described by it. It shows only when the login page's address says the session ended (`?ended=true`), which only `sessionCheck` writes. Not on a first visit, not after Log out, not after a plain login then Log out (tested). After a wrong password only "Wrong username or password." shows (tested). Signing in leaves the page, so the message goes with it.
- **No browser storage.** Nothing is written to `localStorage` or `sessionStorage` (tested after a session end). Unsaved edits live only in the roster page's state, which goes with the page.
- **The return.** The login page's address also carries the page the user was on, path and search (`?back=/roster?month=2026-06`). Signing in goes there (`router.history.push`) if it is an address in the app: it must start with one `/` not followed by `/` or `\`. A full URL, `//host` and a relative path are ignored, and the login goes Home (all three tested). The signed-in layout still sends a forced password change first (tested), and a page's own role guard sends a role that may not open it Home (tested: a nurse signing in where the System Admin was). A plain login still goes Home.
- **Docs.** `docs/ARCHITECTURE.md`'s screens paragraph says a Unit Manager with a nurse profile also has their own roster and month, without requests or swaps, and what a session that ends does. No ADR and no glossary term.

**What was driven, and how.**
- Vitest (the app-level suite, the whole app over a mocked `fetch`): the manager's links with and without a profile, wide and in the Menu, Home's pointers (also with no unit), My roster and My month opened from them; the question naming the month on a Draft and on the roster in force; a 401 on Save going to the login page with no dialog, then signing in back to `/roster?month=2026-06` with nothing unsaved; a 401 on another page (Health, the audit log with a filter in its address) doing the same; the message, its alert and description, its absence after Log out, a first visit and a wrong password; the return, Home for a role that may not open the page, the forced change first, the three addresses outside the app.
- Playwright, ticket 24's checks, no new file:
  - `races.spec.ts`: the deactivated manager's check rewritten. Two cells changed on the approved roster, the System Admin deactivates them, Save: the login page, with the message, focus on Username and no dialog. After the System Admin reactivates them and the CNO gives the unit back, signing in on that same page lands on Roster, on the month, with nothing unsaved.
  - `roles.spec.ts`: Omar (a manager with a nurse profile) opens My roster and My month from the header's links, then reads the seeded month as before. "Every page of the Unit Manager with a nurse profile" now walks the two new links too.

**What was NOT checked:**
- **A screen reader.** The message is an alert and also describes the Username field, so it may be read twice: once as it appears, once with the focused field. Not heard in VoiceOver or NVDA.
- **The 12-hour idle limit and a password changed elsewhere** in a browser. Only deactivation was driven end to end; the frontend sees all three as the same 401 (the backend's tests hold that each ends the session).
- **A dialog open when the session ends** (story 31) was not driven on its own. The dialogs are the page's, so they go with it.
- **A reload of the login page after a session end** keeps the message and the return (they are in its address); not driven.
- Firefox, Safari, a real phone; dark mode.

**Decisions taken here:**
- **Worth your review: the question's words, "Your changes to the roster of June 2026 are not saved yet."** The ticket's example is "June's roster"; the spec also says to use the app's month formatting, which gives "June 2026", and "June 2026's roster" reads badly. "The roster of June 2026" matches the page's own "Solve history of June 2026".
- **Worth your review: the header's order for a manager with a nurse profile: Home, My roster, My month, Roster, Solve history, …** Story 5 asks for the own pages set apart from the unit's ("My roster beside Roster"). They come first, grouped, as a Staff Nurse's come after Home. They are not next to Roster because My roster's heading names the unit as Roster's does ("Roster of ICU" on both), and side by side the two would be easy to mix up. Ticket 24's `go` refuses to step between two pages of the same heading for that reason. My roster comes before My month, the reverse of a Staff Nurse's.
- **Worth your review: the login page learns of the ending from its address** (`/login?ended=true&back=…`), not from memory. It is what the spec offered first, and lets a test start on it. Its cost: a link or bookmark to `/login?ended=true` shows the message on what is really a first visit, and a reload keeps it. The return address copies the page's whole search, which on the audit log can hold a username filter; it was in the page's own address already.
- **Worth your review: if someone else signs in on that login page** (a shared ward computer), they are sent to the page the last user was on, if their role may open it, with their own data. Nothing of the last user's is shown.
- **Worth your review: Home's two lines for the manager are fixed text** ("My roster has your own shifts for each coming month once it is approved." and "Your hours, shifts and leave are under My month."), with no read of whether this month is approved, so Home makes no request more than before.
- **A wrong password after a session end replaces the message** with the refusal, so only one alert shows (story 21).
- **The return goes through `router.history.push`**, since the router's typed `navigate` wants a route, not an address; the address is checked first, so it never leaves the app.
- **`FormField` gained `describedBy`** to tie the message to Username (stories 29 and 30).

**Review.** The `code-review` skill's two axes against `05f2259`.
- **Standards:** no hard violation. Fixed: the manager-nurse's list repeated the manager's (now built from it), and a test helper's name read as if it logged in. Kept: the message's words written out in the tests too, as the suite does for every message; `has_nurse_profile` read in both `roles.ts` and Home.
- **Spec:** no blocking defect. The question's words and the order of the links are above as Worth your review; the message in the address, the return copying the search and the double reading are said above.
- **Found by `e2e/ci.sh`, fixed:** the rewritten race check read the page's alert while the roster page, with its own alerts, was still drawn. It now waits for the login form first. The check stopping there had left the manager deactivated, which failed the two checks after it (`replan.spec`, `solver.spec`).

**Held against `better-writing` and `better-accessibility` by hand:**
- The message says what happened, what it cost and what to do, in the glossary's plain words and the user's agreed text; it names no cause it cannot know.
- The links' names are the pages' names, as for a Staff Nurse; Home's lines say what is there before the link.
- The message is a live alert, above the form in reading order, focus is on the first field, and the field is described by it; nothing depends on colour.

**Things later tickets should know:**
- **The dev stack needs no rebuild:** nothing changed in `deploy/compose.yaml`, the `Dockerfile` or the solver, and no dependency was added. `accounts/api.py` is reloaded by runserver; the frontend is Vite's.
- `Me.has_nurse_profile` is there for any page that needs to know whether someone is on rosters.
- `navigation(user)` in `roles.ts` replaces the exported `NAVIGATION`: a header that depends on more than the role goes there.
- A test that ends a session in `app.test.tsx` can use `untilSignedIn` and `signInAgain`.
- **For a later ticket, not done:** a manager with a nurse profile reads "Roster of ICU" on both Roster and My roster. Story 5's worry is about telling them apart; a heading of its own for My roster would settle it.

**Reviewed by the user (2026-11-07):** all four points marked **Worth your review** are kept as built: "the roster of June 2026" in the question; the header order Home, My roster, My month, Roster, …; the ending read from the login page's address (`?ended=true&back=…`), with its bookmark and search side effects; someone else signing in going to the last page if their role may open it.
