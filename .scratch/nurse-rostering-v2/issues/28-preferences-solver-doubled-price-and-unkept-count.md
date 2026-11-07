# 28: The solver prices a preference double after an unkept month, and carries what was not kept

**What to build:** The vendored solver's contract gains one optional per-nurse input: how many of her preferences the month before did not keep (a whole number, 0 or more; absent means 0, so every stored solve input and close input still loads). For a nurse whose count is above zero, every entry of hers in the two soft rules, a day asked off and a day asked to work, costs twice the weight, in the model's objective and in the validator's explanation alike, and the explanation's words for such a match say it counted double. The result's carry-over block gains the count for next month: her days asked off that were worked plus her days asked to work that were off, leave days excluded, worked out from the month's facts like every carried value. The solver's own suite and the service contract tests cover it, and the CLI shows it on the sample. Nothing in the app changes in this ticket. Spec: `.scratch/nurse-rostering-v2/specs/preferences.md`; the reasons: ADR 0013.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] The request loader accepts the new nurse field, defaults it to 0 when absent, and refuses a negative, a non-integer or a boolean with the usual `request: <field path>` error; the problem's schema version notes the change
- [ ] With the count above zero a nurse's day-off and working-day preferences cost twice the weight; another nurse's cost once; a solve's cost and a validation of the same grid agree
- [ ] The explanation's match for a doubled preference says it counted double; the per-nurse explanation reflects it
- [ ] The result's carry-over block carries the count of unkept preferences, computed from the month's facts with leave days excluded; a nurse with none carries 0
- [ ] The day-list rules are unchanged: a leave day ignored, a day listed twice or in both lists refused
- [ ] The service contract test's sample request and result carry the field; the solver's suite, the service tests and the contract tests pass
