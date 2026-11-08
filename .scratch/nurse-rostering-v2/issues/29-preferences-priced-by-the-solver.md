# 29: A nurse's preferences, kept by the solver at a price

**What to build:** A unit manager sets the unit's preference cap on Unit rules beside the request cap (0 to 31, default 10; 0 switches preferences off; a window opens when either cap is above zero). During an open request window a staff nurse makes preferences on My month's Preferences card, a day off or a working day of any shift, with no reason, up to the cap; withdraws one; or asks for one as a request instead, under the request cap. A date holds one wish, a request or a preference; a leave date or a date outside her dates is refused at the form. Once the window closes they are fixed. The manager reads each window's preferences beneath its requests and decides nothing. The solve input fills each nurse's two day lists from her live preferences, so a real solve keeps them when it can and the draft's explanation shows what it paid; the draft's "changes since" warning lists changed preferences as it lists pins. The CNO's weights page says what the two weights now price. Only the nurse and her manager read preferences; nothing of them reaches a colleague, a notification or the audit log's detail. The card works on a phone, with a Playwright check beside ticket 23's request check. Spec: `.scratch/nurse-rostering-v2/specs/preferences.md`; the words: `GLOSSARY.md` (Preference); the reasons: ADR 0013.

**Blocked by:** None (can start immediately; runs beside 28, and needs nothing of it)

**Status:** ready-for-agent

- [x] Unit rules: "Preferences per nurse per month", 0 to 31, default 10, audited like the request cap; a window opens when either cap is above zero, and the refusal for a unit with both at zero names both
- [x] A preference record beside requests: nurse, window, date, kind (day off or working day), state (`made`, `withdrawn`, `asked_instead`), who and when; nothing deleted; one live preference a nurse and date
- [x] Staff nurses only, through endpoints taking no nurse: read the month's preferences with the window and the cap, make, withdraw, ask for one as a request instead (the request made under the request cap and the window's rules, the preference ended as `asked_instead`, refused as a whole when the request is)
- [x] One wish a date both ways, with words naming the other; a rejected, withdrawn, cancelled, replaced or expired request frees the date; live preferences count against the cap a month across the month's windows; a cap lowered keeps those made and refuses new ones; counted under the same locks a request's count takes
- [x] A leave date and a date outside her dates refused at the form; a nurse due to join makes them in the new unit's window; a transferred nurse's stay on the old unit's record and reach no solve; a manager with a nurse profile makes none
- [x] The Preferences card on My month: the window's sentence with the count against the cap, the form (date, "A day off" or "A working day", no reason), each preference with its state, Withdraw and "Ask for it as a request" behind a question naming the request cap; thumb-sized at 375 px, no sideways scroll, outcomes announced, buttons named with their dates
- [x] The Requests page lists each window's preferences beneath its requests, read-only
- [x] The solve input fills `undesired_days` and `desired_days` from the nurse's live preferences for the unit's month (a day on leave or outside her dates left in, which the solver ignores); a re-plan's input the same; "changes since" reports changed preferences as "preferences"
- [x] A real solve on a scratch stack keeps a nurse's preferences and the draft's explanation shows the two rules' cost
- [x] The weights page's two descriptions no longer say nothing reaches them and say what they price, doubled for a nurse whose preference last month was not kept
- [x] Audit entries `preference.made`, `preference.withdrawn`, `preference.asked_instead` target the nurse with no date or kind; no notification; a colleague's whole My month, print sheet and roster file unchanged; the authorization walk names every new endpoint
- [x] Tests at the agreed seams: the backend API suite (requesting, two-at-once at the cap, solves' input, units' cap, authorization), the frontend app-level suite (six runs at once), and one Playwright phone check: a day-off preference made, asked for as a request, the request withdrawn, the preference made again and withdrawn, leaving the stack as it was
- [x] `docs/ARCHITECTURE.md` sections 1, 4, 5, 8 and 12 updated; the OpenAPI document and the generated client regenerated

## Comments

**From ticket 28 (2026-11-08),** the solver's side this ticket feeds. The solve input's nurse fields stay `undesired_days`
(her live day-off preferences) and `desired_days` (working-day ones), ISO dates of the month. A day she is on leave is
ignored by the solver; a day listed twice, or in both lists, is refused (`request: nurses[i].desired_days: … is listed
twice`, `request: nurses[i]: … is both desired and undesired`), so one wish a date must hold in the input too. The doubled
price's field, `preferences_not_kept`, is already in every nurse's solve input, passed through the chain from the month
before (`closes/chain.py`, 0 until preferences exist); once this ticket fills the lists, the next month's projection counts
them, and ticket 30 tests and shows it. A doubled match in
the explanation has `amount` 2 and its text ends "counts double, a preference was not kept last month". Ticket 28's comment
has the rest.

**Implemented on 2026-11-08,** on branch `claude/ticket-29-preferences-25ac2b`, pull request
MoustafaJazzar/cp-sat-nurse-roster-app#3, from `main` at `9435902` (`80a5558`, `02dcf5b`, `b7826f5`, `aec95da`, `7e3f2dd`,
`4216ab7`, then this comment, `b8ec8ff` and after). The suites, locally:
- the backend under pytest on a throwaway PostgreSQL 18 container of my own: 2539 passed on `b8ec8ff` (the code of this head; only this comment changed since); `requesting` and
  `solves/tests/test_input.py` again after the review's fixes, 131 passed; `makemigrations --check` clean (two new migrations:
  `units/0003_unit_preference_cap`, `requesting/0003_preferences`);
- the frontend: `npm test` 608 passed (again on the head after the review), `npm run build` clean, `tsc -b` clean;
- the OpenAPI document and the generated client regenerated, and matching the export after the last change;
- Playwright on my scratch stack `nr-t29`: `preference.spec.ts` and ticket 23's `request.spec.ts`, at 360 and 320 px, 4 passed,
  twice in a row (the second run shows the stack was left as it was);
- the solver untouched, so its suite was not run; `e2e/ci.sh` and the six parallel frontend runs are GitHub's, on the pull
  request.

**What the dev stack needs:** a **rebuild** of `web` and `worker` (`docker compose up -d --build`): backend code and two
migrations (the preference table, the unit's preference cap, default 10 for every existing unit), which `web` runs at start.
No change to `deploy/compose.yaml`, the `Dockerfile`, the solver or any dependency.

**What was built, criterion by criterion.**
- **The cap.** `Unit.preference_cap` (0 to 31, default 10) on Unit rules beside the request cap, in the form and the read-only
  view, "Preferences per nurse per month", audited in `unit_rules.changed` with its before and after like the request cap
  (`test_an_entry_holds_only_what_changed_with_its_values`). The body now requires it (`StrictSchema`); the five tests that
  PUT rules send it. A window opens while either cap is above 0; with both at 0 the refusal names both ("This unit's request
  cap and preference cap are both 0, …"), on the open and on the manager's page.
- **The record.** `requesting.Preference`: window, nurse, date, kind (`day_off`, `working_day`), state (`made`,
  `withdrawn`, `asked_instead`), `made_at`, `ended_at`, `ended_by`, and for one asked instead the `request` made in its place;
  a unique constraint holds one `made` a nurse and date; check constraints say an ended one says when, and only an
  `asked_instead` one names a request. Nothing is deleted.
- **The endpoints,** staff nurses only, none taking a nurse: `GET/POST /api/preferences/mine`,
  `POST /api/preferences/mine/{id}/withdraw`, `POST /api/preferences/mine/{id}/ask-as-request` (body `shift`), and the
  manager's `GET /api/units/{unit}/request-windows/{window}/preferences`. The read carries the window, both caps, the count,
  the refusal, her days and the shifts she may ask for. Ask instead ends the preference, then makes the request through the
  request's own `make` (its cap, its window, its refusals), all in one transaction: a refused request leaves the preference
  `made` and writes no audit entry (tested at the cap, and with a shift she does not work).
- **The rules.** One wish a date both ways, in any unit's window, with words naming the other ("You have a request on 3 June
  2026, and a date holds one wish. Withdraw the request to make a preference instead." and "You have a preference on …
  Withdraw it, or ask for it as a request instead."); withdrawn, rejected and cancelled requests free the date (tested);
  replaced and expired are not live, by the same `LIVE` set. Live preferences count against the cap across the month's windows
  of the unit, under the nurse's `FOR NO KEY UPDATE` lock a request takes (two at once at the cap, and a request and a
  preference on one date at once, in `test_two_at_once.py`). A lowered cap keeps those made. Leave and outside-dates refused at
  the form ("… nothing to prefer that day"); leave recorded later leaves it `made`. A nurse due to join makes them in the new
  unit's window; a transferred nurse's stay on the old unit's record, counted against its cap only, and reach no solve (the
  assembler reads only the unit's windows, and she is not in its month). A manager with a nurse profile gets 403.
- **The card,** on My month beside Requests: the window's sentence ("Preferences for December 2026 are open until the end of
  20 Nov 2026. You have 2 of 10 preferences."), the form (a date field labelled "Day", "A day off" / "A working day" as
  radios, no reason), each preference with its state, and Withdraw and "Ask for it as a request" each behind a question; the
  second names the request cap ("It counts against your unit's 3 requests a month, pending or accepted") and, for a working
  day, asks for the shift. Outcomes are announced in the card's status line, which takes focus; buttons are named with their
  dates ("Withdraw your preference for 3 Dec 2026"). Thumb-sized and no sideways scroll, checked by Playwright at 360 and
  320 px (the narrowest the app holds to; 375 lies between).
- **The Requests page** lists each window's preferences beneath its requests: nurse, date, what is preferred, state, no
  button; the windows table counts them, and the page's sentences name both caps.
- **The solve input** fills `undesired_days` and `desired_days`, in date order, from the nurse's `made` preferences of the
  unit's windows for the month, only when a list has a day (as `pinned`); one on leave or outside her dates is left in, and the
  solver accepts it. A re-plan's input the same (`assemble_replan` calls `assemble`), and so does a close's, which stores
  them as it stores leave. The solver's four-nurse sample now passes with Dana's two preferences made in the app, instead of
  being dropped from the comparison. "Changes since" reports `preferences` for a nurse whose lists differ; an input stored
  before this has none, and changes only where one is made. The roster pages say "preferences changed".
- **A real solve** on `nr-t29`, January 2027 (the seed's open window), through the API as the nurses and Mona: Amal off on the
  5th and 6th and working the 9th, Badr off the 7th, Emad working the 8th: all five kept, and the two rules cost nothing. Then
  all four ER nurses preferred the 15th off: the solver kept Dana's and Emad's and paid `undesired_day` 4 (weight 2, amount
  2), the explanation listing "Amal: works 2027-01-15 (asked off)" and Badr's.
- **The weights page:** "Each day a nurse preferred to have off but works; twice that for a nurse whose preference last month
  was not kept." and its mirror; "Nothing reaches this for now" is gone. Labels unchanged.
- **Privacy and audit:** `preference.made`, `preference.withdrawn`, `preference.asked_instead`, the nurse acting and her
  hospital ID as target, no before or after, no date or kind (tested); no notification for any of it (the request made instead
  tells nobody either, as any request made); a colleague's My month, print sheet, requests and the roster file unchanged
  byte for byte after Amal's preferences; another unit's manager gets 403 and 404. The authorization walk names all five
  endpoints (`PREFERENCE_ROLES`).
- **Docs:** `docs/ARCHITECTURE.md` sections 1, 4, 5, 8 and 12, and also 3 (the roles table's two rows), 8's audit paragraph
  and 9 (the default); the OpenAPI document and the client regenerated.

**What was driven, and how.** Scratch stack `nr-t29` (`E2E_PORT=18290`), built from this branch at `7e3f2dd`: the Playwright
check on a phone at 360 and 320 px, with ticket 23's request check beside it, twice; the real solve above through the API as
Amal, Badr, Dana, Emad and Mona. After the review's fixes the stack was rebuilt from this branch (`stack.sh rebuild`) and the
two phone checks passed again, 4 of 4.

**What was found, and fixed.**
- Two forms on My month gave their date inputs one id, `field-date`, so the Preferences label pointed at the Requests input.
  `FormField` now takes an `id`; the preference's field is `preference-date`, labelled "Day" (Playwright's `getByLabel("Date")`
  matches substrings, and three existing browser checks use it).
- The dialog's buttons measured 42.3 px: Playwright measured during the dialog's 95%-to-100% zoom. The check now waits for the
  dialog's own animations to finish, not for time.
- (Review) Asking for a preference as a request after a transfer would have put the request in the new unit's window while
  ending a preference on the old unit's record: refused now ("You are no longer on this unit's roster for June 2026, …"),
  tested.

**Findings for you, not fixed.** The solver's explanation says a broken day off is a "requested-off day worked" (its
`counted_in`), words from before preferences that the glossary would now call a preference. It is the solver's text, not this
ticket's.

**What was NOT checked:**
- The cards and pages at 375 px literally (360 and 320 were), and in a desktop browser by hand: no screen-reader run.
- The six frontend runs at once: GitHub's.
- A close storing preferences, and the next month's projected count: ticket 30's.
- `better-interface`, `better-writing`, `better-accessibility` were held by hand against the card and the manager's list
  (names, focus, announcements, words), not run as skills.

**Decisions taken here:**
- **Worth your review: a working-day preference asked for as a request asks for the shift.** A request names a shift or a day
  off, and the spec says only "ask for one as a request instead". The question shows a shift picker for a working day; the
  endpoint refuses one without a shift ("Choose the shift you ask for.") and a day off with one. The other reading was to
  allow asking only for a day off.
- **Worth your review: "the same refusal on an open window" on Unit rules.** The request cap has no refusal while a window is
  open (only the open itself is refused when it is 0), so the preference cap has none either; a cap changed mid-window keeps
  what was made and refuses new ones above it, as the spec says. I took the spec's line to mean the "both at 0" refusal.
- **Worth your review: words the spec does not give.** A window opened on one cap alone refuses the other: "The ER unit takes no
  requests, only preferences." and "… takes no preferences, only requests."; the closed window: "… has closed, so your
  preferences are fixed. The solver keeps them when it can."; the states "Made", "Withdrawn", "Asked for as a request".
- **Worth your review: one live preference a date in any unit,** as the spec's unique constraint has it, so one a transfer left
  on the old unit holds that date in the new unit until withdrawn there while its window is open (as a request left behind
  does). The card lists every preference of hers for the month, the old unit's included; its count is the current unit's.
- **Worth your review: the doubled price starts with this ticket, before ticket 30 tests or shows it.** Once the lists reach
  the solve input, the carry-over block counts unkept preferences, and the chain ticket 28 built passes that count on: a
  nurse one of whose preferences the roster in force of a month did not keep pays double in every solve of the next month,
  on your dev stack too after the merge, while My month says nothing of it until ticket 30. Not tested here, by the split
  between the two tickets.
- **Small additions:** the link from an `asked_instead` preference to its request; a preference count column on the manager's
  windows table; the request cap's place in the Preferences question. The `withdraw` of a preference is behind a question
  too, as the spec's Seam 3 has it, though a request's withdraw is not.
- **Labels kept:** the weights are still "Working a day asked off" and "Off on a day asked to work"; only their descriptions
  changed, as the spec asks.

**Review:** `code-review` against `9435902`, both axes; no adversarial review, by the user's call.
- *Spec:* nothing missing; the transfer edge of ask-instead fixed (above). The extras and the open-window reading are under
  Worth your review.
- *Standards:* no hard breach. Fixed: "wish" used as a synonym in three docstrings (the glossary's Avoid list); `_end`'s unused
  parameter; the live-request check shared (`live_request_on`) beside `live_preference_on`; the kind and state literals beside
  `RequestStateText` in `requesting/api.py`; `PREFERS` and `PREFERENCE_STATE` moved to `lib/request-words.ts`, so the route no
  longer imports from a component; the model's choice labels made consistent, which fixes "This preference is asked instead,
  so …" to "asked for as a request"; a 200-character docstring line. Kept: `my_preferences` mirrors `my_requests` (two
  reads of one window, short, each with its own refusals); `nurse_refusal`'s `verb` (one word of one sentence);
  `MAX_REQUESTS` bounding both caps (its comment says so); `solves/tests/test_input.py` writing preference rows through the ORM,
  since the assembler is the seam under test and the API path is tested in `requesting`.

**Things later tickets should know.**
- **30:** the read is `GET /api/preferences/mine` (`requesting/preferences_api.py`, `MyPreferences`, `MyPreferenceRow`);
  add the outcome, the counts kept and keepable and the doubled line there, as new fields. The card is
  `frontend/src/components/my-preferences.tsx` (`MyPreferencesCard`); its heading is "Preferences" and a sentence above the
  table, where "4 of 5 kept" and "No roster yet" will sit. The solve input already carries the lists (`solves/input.py`,
  `_preferred`) for solves, re-plans and closes, so the chain's projection and a close now count unkept preferences for
  real: from the first month with preferences, `preferences_not_kept` can be above 0 and the next month's solves double. A
  preference on leave stays `made`; the outcome's On leave is read from leave, as the spec says. Live preferences are
  `state="made"` of the unit's windows for the month (`window__unit`).
