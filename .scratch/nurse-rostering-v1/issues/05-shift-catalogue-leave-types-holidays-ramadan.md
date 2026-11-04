# 05: Shift catalogue, leave types, public holidays and Ramadan dates

**What to build:** The CNO maintains the shift catalogue (code, display name, hours, start and end time, colour, active), the leave types, the public holidays per year, and for each month either fixes the Ramadan dates after the moon sighting or leaves them derived from the Umm al-Qura calendar. Renaming a display name is free; renaming a code is recorded so histories can follow later.

**Blocked by:** 03 Management accounts

**Status:** ready-for-agent

- [x] Shift catalogue list and form with code, display name, hours, start and end time, colour, active; seeded with the default shifts
- [x] A code rename is recorded (old name, new name, date) for later history mapping
- [x] Leave types list and form, seeded with common types
- [x] Public holidays per year; a date cannot be entered twice
- [x] Ramadan dates per month: derived and shown, or fixed by the CNO as a range or a list
- [x] All changes audited; only the CNO may change them; every role may read the catalogue
- [x] API tests cover each resource and the derived Ramadan days for a sample month

## Comments

Implemented on 2026-11-05. Backend under pytest on real PostgreSQL 18, frontend under Vitest with the real routes and generated client over a stubbed `fetch`.

Driven on the dev overlay in the built-in browser as the CNO: the seeded shifts and leave types, a code rename (recorded on the row, focus back on its button) and the hospital rules page opening afterwards with the new code in its pairs and selects, retiring a shift a pair names (refused beside the switch, with focus on it), a holiday and the same date refused, the derived Ramadan days, fixing a month as a range and as a list, the questions before removing a holiday and returning a month to the calendar with focus where it should land, and no sideways page scroll at 375 px. Over the API on the same stack: 200 on all four reads and 403 on a write and on the rules for the System Admin and a Unit Manager, and the audit entries as the System Admin reads them.

What was not checked:

- **The production compose file through Caddy.** Only the dev overlay ran, as in ticket 04.
- **Deputy CNO, Staff Nurse and System Admin pages in a browser.** Route tests for the read-only pages; the role checks are API tests and the walking test.
- **Two people saving at once.** The rule lock and the unique constraints are there by design; no test races them.

Decisions this ticket took:

- **"Every role may read the catalogue" covers all four lists and includes the System Admin.** `docs/ARCHITECTURE.md` says they see "no roster and no rostering attribute", and a shift, a leave type's name, a holiday or a Ramadan date is neither: it is hospital reference data. That applies to the lists only: a nurse's allowed shifts stay a rostering attribute. Section 3 has a row for this now. The pages open for them, but they get no navigation link, because section 8 gives them technical screens and nothing in their work calls for these. Say so if they should have one, or should not read these at all.
- **Ticket 04's trap, resolved by keeping one rule: a forbidden succession only ever names an active shift.** A rename carries through the saved pairs in the same transaction, audited as `hospital_rules.changed` as well as `shift.changed`, and leaves the review flag alone. Retiring a shift a pair names is refused with a message naming the rules. Saving the rules refuses an unknown or retired code, checked under the same row lock as every catalogue write, so the two cannot interleave. `HospitalRules` no longer checks codes when it validates, so `GET /api/hospital/rules` cannot fail on them whatever a row holds. The location of a refusal is still `forbidden_successions, i, j`, but it now arrives after the schema's other refusals rather than with them.
- **A code another shift used to hold cannot be taken.** The record says what an old name in a history means, so it cannot start to mean something else. A shift may return to a code of its own. This is a rule the ticket did not state; it makes the rename record unambiguous.
- **Codes:** at most 8 characters, because they sit in a grid's cells (the solver allows 100), starting with a letter or digit. `L` is reserved by the solver for leave, and `l` is refused too because codes are unique in any case.
- **Seeded names, times and colours are ours, not reviewed.** Only codes and hours come from `er_request_2026-03.json`: Day 07:00 to 19:00, Night 19:00 to 07:00, Morning 07:00 to 15:00, Evening 15:00 to 23:00, Late night 23:00 to 07:00. The CNO should correct them. They carry no review flag. Seeded leave types are Annual, Compassionate, Educational, Emergency, Maternity, Sick, with no "Unpaid", since every type counts the same for hours.
- **Hours are not checked against the times.** A shift's hours are what it counts for a nurse, which a break can make shorter than the clock says, so 12 hours at 07:00 to 15:00 is accepted. Nothing reads the times yet.
- **Holidays and fixed Ramadan months can be removed**, against section 9's "nothing is hard-deleted", which now names them as exceptions. Neither has an active flag to retire with, a mistaken entry has to go somewhere, a solve stores its own input, and the audit log keeps the rest. Both ask first.
- **Fixed Ramadan dates are stored as a list of dates, one row per month.** A range is a way of entering them and must lie within the month: a Ramadan across two months is fixed twice. An empty list means no Ramadan days that month, which is different from no row.
- **The derivation is the solver's own** (`nurse_roster.calendar`), imported read-only, so `backend/pyproject.toml` now declares the workspace package. That module needs only `hijridate`; `web` still runs no solve. Dates and years are limited to 1925 to 2076, the whole years its data covers.
- **Refusals that need the database are 422s in the schema's own shape** (`hospital.api.refuse`), so a page treats them all alike. That includes "already in use", where ticket 03's users API answers 409 with its own body. The exception is a month outside the calendar in a path, a plain 422 no page can reach.
- **On the holidays page a row's actions are not sticky**, against ticket 03's advice for tables: at 375 px two sticky buttons covered the dates, which are what the row is for. The shifts and leave types tables keep theirs.
- **Left as judgement calls after the review:** the three forms repeat one create-or-update shape, with different fields and messages; `_differing` and `hospital.rules.changes` share a tail; `catalogue_api.py` holds four resources; the page's default year is the browser's, not the hospital's, so it can be a year off for a few hours at New Year.

Things a later ticket should know:

- **Solve input (11):** build `general_block(HospitalSettings.load(), shift_hours={shift.code: shift.hours for shift in Shift.objects.filter(active=True)})`. Every code a pair names is active, so the solver's check passes; a test proves this at the seed. But the unit's `shifts` and a nurse's allowed shifts must then be active too, which tickets 09 and 11 have to hold. Send `public_holidays` from `PublicHoliday.objects.filter(date__year=..., date__month=...)` and `ramadan_days` from `hospital.catalogue.ramadan_dates("YYYY-MM")`, as ISO dates: a list, possibly empty, so the stored solve input says what was used rather than leaving the solver to derive it. The solver refuses a range with no day in the month, and a list has no such case.
- **Renames in a solve (11, 21):** `renamed_shifts` is `{rename.old_code: rename.shift.code for rename in ShiftRename.objects.select_related("shift") if rename.old_code != rename.shift.code}`. Following the current code rather than `new_code` collapses a chain, and the filter matters because a shift that went back to an old code must not be listed: the solver refuses an old name that is still a shift. Only `previous` is mapped by the solver. `ShiftRename` records nothing else: a pinned cell, a request, an allowed-shifts list or a roster grid that stores a code has to be carried in the rename itself or stored by shift id, and `update_shift` in `catalogue_api.py` is where.
- **Guards still to add (09, 11, 13):** section 4's "a shift a unit still uses cannot be retired" and "hours cannot change while an open month's roster uses the shift". Add them to `update_shift`, as `refuse((("active",), ...))` and `refuse((("hours",), ...))`, under its lock. Retiring a leave type has no guard, and ticket 10 should offer only active ones while keeping retired ones readable on recorded leave.
- **Lock order:** every shift write takes `HospitalSettings.load(for_update=True)` first. Keep that order in new code that touches both.
- **Lists include retired rows.** A picker must filter on `active`.
- **`SHIFT_CODES` is gone:** `shift_codes` in `GET /api/hospital/rules` is the active codes, oldest first.
- **Frontend:** `serverErrors` and `showServerErrors` are in `lib/server-errors.ts`; the second puts refusals on a form with focus on the first, including a checkbox, which `setError`'s own focus cannot reach. `useEditing` in `lib/use-editing.ts` returns focus to the row's button after editing. `scrollableRegion` in `lib/utils.ts` is a read-only table's container. A native colour input ignores React Hook Form's default and shows black, so it needs `value={form.watch(...)}`, as on the shifts page: saving would otherwise turn the shift black.
- **Audit actions added:** `shift.created`, `shift.changed`, `leave_type.created`, `leave_type.changed`, `public_holiday.created`, `public_holiday.changed`, `public_holiday.removed`, `ramadan_dates.changed`, all named in `ACTION_NAMES`. None is a roster or a rostering attribute, so ticket 03's restriction on what the System Admin reads in the log holds.

**Review (2026-11-05).** The `code-review` skill's two axes found the design doc stale on who reads the catalogue and on deletes, removals with no confirmation, focus lost after them, `hospital-rules.tsx` keeping its own copy of the refusal loop, `public_holiday.added` out of step with the other actions, and a month fixed to no days reopening as an empty range. All fixed. The `interface-review` skill itself was not run; the pages were held to the `better-*` rules by hand and by that review.
