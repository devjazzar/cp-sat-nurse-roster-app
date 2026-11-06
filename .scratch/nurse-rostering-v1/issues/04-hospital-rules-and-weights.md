# 04: Hospital rules and weights

**What to build:** The CNO opens the hospital rules and sees every rule the solver knows (hours per day, Ramadan and breastfeeding reductions, weekend days, forbidden successions, the hours and overtime switches and caps) and every weight, each explained in plain words, pre-filled with the reviewed defaults and flagged "defaults, review before the first solve" until saved. Saving validates every field, is audited, and feeds every later solve input.

**Blocked by:** 03 Management accounts

**Status:** ready-for-agent

- [x] Hospital settings row seeded on first start with the reviewed defaults and a review flag
- [x] Rules form with every field of the solver's hospital-wide block and explanations; validation errors name the field
- [x] Weights form with every weight explained (what one unit of violation costs); zero switches a rule off
- [x] Saving clears the review flag and writes an audit entry with before and after
- [x] Only the CNO can read or change them (Deputy CNO read-only, others 403)
- [x] API tests cover defaults, validation, saving and authorization

## Comments

Implemented on 2026-11-05. Backend under pytest on real PostgreSQL 18, frontend under Vitest with the real routes and generated client over a stubbed `fetch`.

Driven on the dev overlay in the built-in browser: the CNO's page with the flag, a refused 25 hours beside its field with focus on it, a save clearing the flag and surviving a reload, a weekend day, removing and adding a pair with focus following, no sideways scroll at 375 px, and the Deputy CNO's read-only page with no input on it. Over the API on the same stack: the audit entry as the System Admin reads it, 403 for the Deputy CNO's write and for the System Admin's read, and the saved rules surviving a `web` restart (so `bootstrap` left them alone).

"Feeds every later solve input" is proven only at the seam, because no solve exists yet: `hospital.rules.general_block` is called from tests alone, where its output passes the vendored solver's own `load_request`, at the limits of what the API accepts as well as at the defaults.

What was not checked:

- **The production compose file through Caddy.** Only the dev overlay ran this time. Both files run `bootstrap`, and ticket 02's reason still keeps the browser off Caddy.
- **The Deputy CNO's page and a stale 422 at phone width.** The width check was the CNO's form only. A refusal from the API is a stubbed test, since the form's own checks stop those values first.

Decisions this ticket took:

- **`shift_hours` is not a hospital rule here.** It belongs to ticket 05's catalogue; the API refuses it. Every other field of the solver's `general` block keeps the solver's own name, such as `dept_overtime_cap`, so the block crosses to a solve input as it is. The page calls it "Unit overtime cap".
- **Saving is the review.** Save stays open while the flag is up, even with nothing changed, and that save is audited as `needs_review: true → false`. Saving again with no change writes nothing, as technical settings do.
- **Audit entries hold only what changed**, with weights as `weights.<name>`, so the audit page reads field by field. The System Admin therefore sees rule values in the log while getting 403 on the rules themselves. Hospital rules are neither a roster nor a rostering attribute, so this is within ticket 03's restriction. Say so if it should be otherwise.
- **The Deputy CNO's read is a row of its own** in `docs/ARCHITECTURE.md` section 3, from this ticket's criterion, and the page is a plain list for them rather than disabled inputs, which would dim what they came to read.
- **`undesired_day` and `desired_day` are shown and say they do nothing for now**: the solver requires them, and ADR 0005 keeps soft requests out of v1.
- **Not added:** the row's name, time zone and request cap default from `docs/ARCHITECTURE.md` section 4. No ticket reads them yet; time zone is still `TIME_ZONE` from the environment and ticket 09 gives the request cap to the unit.

Things a later ticket should know:

- **Shift catalogue (05):** `SHIFT_CODES` in `hospital/rules.py` stands in for the catalogue; replace it with the catalogue's codes, which the page's selects get through `shift_codes`. Three traps. `HospitalRulesState.rules` re-validates stored rules on every answer, so **a retired or renamed code still named in a saved pair would make GET fail** and lock the CNO out of the page that fixes it: refuse the retirement, carry the rename through the pairs, or stop validating that answer. A select also shows only `shift_codes`, so a pair naming anything else would display wrongly. And the catalogue's seeded codes must stay D, N, A, B, C or the seeded pairs break.
- **Solve input (11):** read the block with `general_block(HospitalSettings.load(), shift_hours=...)`. Nothing refuses a solve while `rules_need_review` is up, and no ticket asks for it; the spec's flag only says "review". Ticket 11 could show it beside the precheck warnings.
- **Unit rules (06, 09):** the same shape should do: a JSON block in the solver's names, `StrictSchema` from `hospital/api.py`, and `field_validator`s rather than a model validator so a refusal names its field. Strict matters: Pydantic would otherwise turn `"8"` and `true` into numbers.
- **Seeding:** `bootstrap` calls `HospitalSettings.load()` before its early return, so an installation that already has a System Admin gets the row too. `load` also creates the row if it is ever missing.
- **Frontend:** `CheckboxField` is in `form-field.tsx`. A refusal from the API's field validators opens with Pydantic's "Value error, "; `serverErrors` in `hospital-rules.tsx` strips it and maps `loc` to a form path. Move it somewhere shared when a second page needs it.
- **A new weight** means editing `DEFAULT_RULES`, `Weights` in `hospital/api.py` and `WEIGHTS` in the page. The backend tests compare the first two with the solver, but nothing but the page's test fixture checks the third.

**Review (2026-11-05).** The `code-review` skill's two axes found a wrong explanation (weekend fairness also has a tolerance, which `solver/how-to.md` section 2.2 omits too), the design doc's screen list contradicting the new row, "unit" used as a measure, API refusals on weekend days showing nowhere, Pydantic's prefix, and `role="group"` replacing list items. All fixed, and "Add a pair" now starts from two different shifts, since forbidding a shift after itself is a far stronger rule to add by accident. Left as judgement calls: the form and the read-only list each spell out the five sections, and `HospitalSettings` repeats `TechnicalSettings`' one-row pattern. The `interface-review` skill itself was not run, because it cannot be invoked by an agent; the page was held to the `better-*` rules by hand and by that review.

**Reviewed by the user (2026-11-05), and kept as built:** what the System Admin sees in the log, rule values included. The review flag gets a warning beside the precheck with no block (ticket 11's last comment).

**Reviewed by the user (2026-11-06).** From the review of every unsettled item across tickets 01–20, answered as recommended. Kept as built: a save with no change clears the review flag (L32); the Deputy CNO's plain list (L34); `undesired_day` and `desired_day` shown, doing nothing (L35). Decided: `docs/ARCHITECTURE.md` section 4 now matches what was built ("Not added", L36): hospital settings hold the rules only, the time zone comes from the environment and each unit holds its own request cap, default 3.
