# 47: The solver prices full runs above the cap

**What to build:** The vendored solver's contract gains one optional department field, the most full runs a nurse may work in the month (a whole number 0 to 31; absent means no cap, so every stored solve input and close input still loads and gives what it gave), and one soft rule with its weight, a full run above the most (absent means 0). A full run is a run of exactly the longest run, a run being consecutive worked days with a non-worked day, leave included, on each side. Each nurse's full runs beyond the cap cost the weight each, in the model's objective and in the validator's explanation alike; the match names the nurse, her count and the cap, and the per-nurse explanation carries it as it carries weekends above the most. A full run counts in the month that holds its last day: one begun in the history and ended in the month counts; one reaching the month's last day does not. With the longest run at 0 or 1 nothing is priced. The solver's own suite and the service contract tests cover it, and the CLI shows it on the sample. Nothing in the app changes in this ticket. Spec: `.scratch/nurse-rostering-v2/specs/full-runs.md`; the words: `GLOSSARY.md` (Run, Full run).

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] The request loader accepts the new department field and the new weight, treats an absent cap as no cap and an absent weight as 0, and refuses a negative, a non-integer, a boolean or a cap above 31 with the usual `request: <field path>` error; the problem's schema version notes the change
- [ ] On a known grid counted by hand, each full run beyond the cap costs the weight once; a solve's cost and a validation of the same grid agree; a nurse at or under the cap costs nothing
- [ ] Leave ends a run; a run begun in the history and ended in the month counts; a run reaching the month's last day does not; the longest run at 0 or 1, or the weight at 0, prices nothing
- [ ] The explanation's match names the nurse, her count and the cap; the per-nurse explanation carries it
- [ ] With the cap set, a solve of the ER sample gives no nurse more full runs than the cap where the month allows it
- [ ] The service contract test's sample request and result carry the field; the solver's suite, the service tests and the contract tests pass
- [ ] `solver/DESIGN.md` names the rule beside the other run rules; `docs/ARCHITECTURE.md` section 6 names the field

**Worth your review, already known:** a full run that ends exactly on the month's last day is counted by neither month (the
month cannot see it ended, the next cannot change it). Confirm this reading or say why the next month should count it.

## Comments
