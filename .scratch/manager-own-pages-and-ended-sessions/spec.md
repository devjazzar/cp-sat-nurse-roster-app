# A manager's own pages, and a session that ends

Status: ready-for-agent
Type: enhancement
Published: 2026-11-07 by /to-spec
Ticket: `.scratch/nurse-rostering-v1/issues/25-manager-own-pages-and-ended-sessions.md`

Spec drawn from ticket 24's two findings and the user's answers when they were grilled on 2026-11-07. Vocabulary:
`GLOSSARY.md`. Decisions and their reasons: `docs/ARCHITECTURE.md` and `docs/adr/`. Where this spec and those documents
disagree, the documents win and this spec is wrong.

## Problem Statement

**A Unit Manager with a nurse profile cannot find their own pages.** The design puts such a manager on their unit's rosters, and lets them read their own roster and their own month (hours, overtime, what is carried, shift counts, leave). The pages already let them in. But nothing in the header or on Home links to My roster or My month, so the manager has to know the address.

**A session that ends behind the user's back is handled badly.** The causes are the 12-hour idle limit, an account deactivated by the System Admin, or a password changed elsewhere.
- **During an edit:** a manager editing the roster who presses Save is first asked "Leave without saving your changes? Your changes to the draft are not saved yet. If you leave, they are lost." That is wrong in three ways:
  - the roster may be **Approved**, not a **Draft**;
  - staying on the page can save nothing, because the session is gone;
  - nothing tells the manager the session ended.
- **On the login page,** which they land on either way, nothing explains why they are there. Users think they did something wrong, or lost work without knowing why.

## Solution

**The manager's own pages.** A Unit Manager with a nurse profile has **My roster** and **My month** among their header's links, on a wide screen and in the phone Menu, and on Home, as a Staff Nurse does. A Unit Manager without a nurse profile sees neither. Nothing else of a Staff Nurse's is added: no request or swap links, since only staff nurses' cells are swapped.

**The unsaved-changes question** on the roster page names the month rather than "the draft", so it is right for a Draft and an Approved roster alike: "Your changes to June's roster are not saved yet. If you leave, they are lost." The other lines on the page that say "the draft" while the roster shown may be Approved are corrected the same way.

**When a session ends behind the user's back**, the app goes straight to the login page, from whatever page the user is on, with no question first. The login page says: "You were signed out. Changes you had not saved are lost. Sign in to carry on."
- **The message:** one message, whatever the cause, since the browser cannot tell which it was. It shows only after such an ending: never after Log out, a wrong password or a first visit. It goes once the user signs in.
- **Unsaved edits:** nothing of them is kept in the browser.
- **Signing in again:** the user goes back to the page they were on, if their role may still open it, otherwise to Home. A plain login still goes to Home.

## User Stories

1. As a Unit Manager with a nurse profile, I want a My roster link in the header, so that I can read the roster in force for me without knowing its address.
2. As a Unit Manager with a nurse profile, I want a My month link in the header, so that I can read my hours, overtime, what is carried, my shift counts and my leave.
3. As a Unit Manager with a nurse profile on a phone, I want My roster and My month in the Menu, so that I reach them with a thumb as a Staff Nurse does.
4. As a Unit Manager with a nurse profile, I want Home to point me to My roster and My month, so that my own schedule is one step from where I land.
5. As a Unit Manager with a nurse profile, I want my own links set apart from my unit's pages in a way I can tell at a glance (My roster beside Roster), so that I do not confuse my own roster with the unit's grid I manage.
6. As a Unit Manager without a nurse profile, I want no My roster or My month links, so that I am not offered pages that have nothing for me.
7. As a Unit Manager with a nurse profile, I want no request or swap links of a Staff Nurse's, so that I am not offered actions the design does not give me.
8. As a Unit Manager given a nurse profile by the CNO while signed in, I want the links to appear when the app next reads who I am, so that I need not ask anyone why they are missing.
9. As a Staff Nurse, I want my header and Home unchanged, so that nothing I know moves.
10. As the CNO, Deputy CNO or System Admin, I want my header unchanged, so that nothing of a nurse's appears for me.
11. As a Unit Manager editing a Draft, I want the unsaved-changes question to name the month, so that I know which roster's changes I would lose.
12. As a Unit Manager editing the Approved roster, I want the question not to call it "the draft", so that I am not misled into thinking my edit is not to the roster in force.
13. As a Unit Manager with unsaved changes who leaves the page on purpose, I want the question still asked, so that I do not lose work by a slip.
14. As a Unit Manager with unsaved changes, I want the line beside Solve to name the roster correctly, so that the page is consistent with itself.
15. As a Unit Manager whose account the System Admin deactivates while I edit, I want to be taken straight to the login page when I save, so that I am not asked to choose between options that can save nothing.
16. As any signed-in user whose session reached the 12-hour idle limit, I want the next thing I do to take me to the login page with a message, so that I know I was signed out and why I am there.
17. As any user whose password was changed elsewhere, I want the same message, so that I am not left wondering why my session stopped.
18. As any user on any page, not just the roster page, I want a session end handled the same way, so that the app behaves the same everywhere.
19. As a user signed out behind my back, I want the message to say that unsaved changes are lost, so that I know to check and redo my last edit.
20. As a user who clicked Log out, I want no "you were signed out" message, so that the login page does not suggest something went wrong.
21. As a user who typed a wrong password, I want only "Wrong username or password.", so that two messages do not confuse me.
22. As a user opening the app for the first time, I want a plain login page, so that I am not told I was signed out when I never signed in.
23. As a user who signs in after the message, I want the message gone, so that it does not linger.
24. As a user signed out behind my back, I want to land back on the page I was on after signing in, so that I carry on where I stopped.
25. As a user whose role can no longer open the page I was on, I want to land on Home instead, so that I am not sent to a page that refuses me.
26. As a user who signs in normally, I want to land on Home, as now, so that the usual login is unchanged.
27. As a user who must change their password, I want the forced password change still to come first after signing in, so that the return to the page never skips it.
28. As a user on a shared ward computer, I want nothing of my unsaved roster edits kept in the browser, so that the next person at the computer cannot see them.
29. As a screen reader user, I want the login page's message announced, so that I learn I was signed out without seeing it.
30. As a keyboard user, I want focus on the login form when I arrive after a session end, so that I can sign in at once.
31. As a user whose session ended while a dialog was open, I want the dialog gone on the login page, so that nothing of the old page is left over it.
32. As a user signed out behind my back, I want nothing of the previous user's data left in the app's memory, so that the next person to sign in never sees it.

## Implementation Decisions

- **The API's `Me` gains `has_nurse_profile` (boolean).**
  - `Me` is the signed-in user as the login, the session check and the current-user read return it.
  - The field is true when the user has a nurse profile, of any role. Only a Unit Manager's header and Home act on it; a Staff Nurse always has one.
  - It is read on the request's user, with no new endpoint and no extra request per page. The OpenAPI export and the generated client are regenerated.
  - No schema change: the nurse profile already exists.
- **The header's links per role** stay one declared list per role. The Unit Manager's list gains My roster and My month only when the current user has a nurse profile. The phone Menu, built from the same list, follows with no change of its own. The pages' own guards are unchanged; the API still enforces what each role may read.
- **Home for a Unit Manager with a nurse profile** adds the Staff Nurse's two pointers (My roster and My month) beneath the manager's own lines. It reuses the Staff Nurse Home's wording where it fits.
- **The roster page's wording** names the month the page shows, through the app's existing month name formatting. Every sentence that says "the draft" while the roster shown may be Approved is corrected. Where the roster is surely a Draft (the Solve button acts only on a Draft), "the draft" may stay. Glossary words only: **Draft**, **Approved**, **Roster version**.
- **The session end** is detected where it is today: a 401 on any query or mutation while a user is cached as signed in.
  - On that, the app clears its query cache and its current user, as now, and goes to the login page.
  - It **bypasses the roster page's navigation guard**, so no unsaved-changes question is asked. The guard keeps asking for every navigation the user makes themself.
  - It passes two things to the login page:
    1. that the session ended, so the message shows;
    2. where the user was (the path and its search), to go back to.

    The login page reads both from its route's search params, or from a router-level state that is not kept across a reload; the implementer picks one. **No personal data and no roster data in the URL:** the path and its search hold only page addresses and months, as they already do.
- **The login page** shows the message in an alert region above the form when told the session ended, with focus on the username field.
  - On success it goes to the remembered page, else to Home.
  - The signed-in layout's forced password change still takes precedence.
  - A remembered page the role may not open is redirected to Home by that page's existing role guard, so no separate check is needed.
  - The remembered page must be an address inside the app, never a full URL, so a crafted link cannot send a user off-site after signing in.
- **Log out**, a wrong password and a first visit pass neither the message nor a page to return to.
- **No browser storage** of roster edits or of the message (no localStorage, no sessionStorage).
- **`docs/ARCHITECTURE.md`'s screens paragraph** says that a Unit Manager with a nurse profile also has My roster and My month, and what a session that ends behind the user's back does. No ADR: nothing here reverses a recorded decision. No new glossary term.

## Testing Decisions

- **What a good test is here:** it drives the app as a user does and checks what the user sees: links by their accessible names, headings, alert text, the address, focus. It does not check component state, router internals or how the redirect is wired.
- **Seam 1, the API:** the backend's existing login and session tests assert `has_nurse_profile` on `Me` the way they assert `must_change_password`:
  - true for a Unit Manager with a nurse profile and for a Staff Nurse;
  - false for a Unit Manager without one and for the CNO, Deputy CNO and System Admin;
  - the OpenAPI export matching the committed copy.
- **Seam 2, the frontend's app-level Vitest suite** (the whole app rendered at an address over a mocked API, as the roster, header and session tests already are). This is the main seam. It covers:
  - the Unit Manager's links with and without a nurse profile, on a wide screen and in the phone Menu, and no request or swap links;
  - Home's two pointers for a manager with a nurse profile, and none without;
  - the unsaved-changes question naming the month on a Draft and on an Approved roster, and still asked when the user leaves on purpose;
  - a 401 during an edit going straight to the login page with no question;
  - a 401 on another page doing the same;
  - the login message: shown after a session end; not after Log out, a wrong password or a first visit; gone after signing in; announced as an alert;
  - the return to the remembered page after signing in, to Home when the role can no longer open it, and the forced password change still first;
  - a remembered address outside the app ignored.
- **Seam 3, ticket 24's Playwright checks:**
  - **The race check rewritten:** "a manager deactivated while editing is asked, on saving, whether to leave…" today asserts the old behaviour. It now asserts that after the save the manager is on the login page with the message and no question. After the System Admin reactivates the account and the CNO gives the unit back, signing in returns to the Roster page.
  - **One step added to the journey or a desktop check:** the manager with a nurse profile opens My roster and My month from the header's links, rather than by address.
  - No new spec file. Run with `e2e/ci.sh`.
- **Prior art:** the header and phone Menu tests and the roster editing tests in the frontend's app-level suite; the session-end handling's existing tests there; the backend's login and session tests in `accounts`; ticket 24's race and journey checks in `e2e/`.

## Out of Scope

- Telling the user *why* the session ended (idle, deactivated, password changed). The browser cannot know, and the server would have to remember an ended session's cause to say.
- Keeping unsaved roster edits across a session end, or warning before the idle limit is reached.
- Requests or swaps for a Unit Manager with a nurse profile. The design gives them neither.
- Changing the 12-hour idle limit, or how a deactivation or a password change ends sessions.
- Any change to what the API lets a Unit Manager read; only the links and `Me` change.
- Dark mode, and anything else ticket 24 listed as not checked.

## Further Notes

- `e2e/support.ts`'s `signIn` and `go`, and the deactivation check's way of ending a session, already exist. The check that makes a manager with a nurse profile can follow the journey's own people.
- CI has never run on GitHub (no remote), so "passes in CI" means `e2e/ci.sh` passing locally, as for ticket 24.
- The dev stack will need a restart of `web` after the API change (runserver reloads, but the generated client is the frontend's), and no rebuild unless a dependency is added.
