# 49: The solver prices overtime above a nurse's share, and carries her balance

**What to build:** The vendored solver's contract gains the overtime share. The department block gains three optional fields: whether the unit shares its overtime, the tolerance in whole hours and the limit on the carry in whole hours (0 to 744 each); the weights gain the hour of overtime above the share; each nurse gains one optional carried value, her overtime balance in hours. Absent means the rule off, a weight of 0 and a balance of 0, so every stored solve input and close input still loads and gives what it gave. A nurse's share is the unit's overtime in the month times the hours she owes over the hours all the nurses in the input owe; her target is her share less her carried balance (held within plus or minus the limit) when the unit carries fairness between months; her priced hours are her overtime above the target, beyond the tolerance, and never more than her overtime, so a nurse with no overtime costs nothing and hours below a share are never priced. The cost is the weight per priced hour, in the model's objective and in the validator's explanation alike; the match names the nurse, her overtime, her share and the hours priced. The result's carry-over block gains her balance for next month: her balance in, plus her overtime, minus her share, moving while the unit's switch is on whether or not it carries fairness, and handed on unchanged with the switch or the hospital's hours rule off. The existing price per hour of overtime, the unit's soft cap and the hard per-nurse caps are unchanged. The solver's own suite and the service contract tests cover it, and the CLI shows it on a sample. Nothing a user sees changes in this ticket. Spec: `.scratch/nurse-rostering-v2/specs/overtime-share.md`; the words: `GLOSSARY.md` (Overtime share).

**Blocked by:** 47 The solver prices full runs above the cap (both change the solver's input, so they go one after the other)

**Status:** ready-for-agent

- [ ] The request loader accepts the three department fields, the weight and the nurse's balance, treats each absent one as off or 0, and refuses a bad value (a negative or non-integer number of hours, a boolean, hours above 744, a balance beyond the solver's bound) with the usual `request: <field path>` error; the problem's schema version notes the change
- [ ] One soft rule in the registry with its weight, active when the unit's switch is on, the weight is above 0 and the hours rule is on; model, validator and explain follow the registry
- [ ] On a small month whose headcounts force a known amount of overtime, with the rule on no nurse holds a second extra shift while another holds none; the cost of a hand-built uneven grid is the weight times the hours counted by hand; a solve's cost and a validation of the same grid agree
- [ ] A nurse with no overtime costs nothing whatever she carries; hours below a share cost nothing; with the rule on the month's total overtime is never above what it is with the rule off
- [ ] A share follows the hours owed: lower for a nurse on leave and one on reduced hours, none for a nurse who owes none
- [ ] A carried balance moves the target, is held within the limit, and is ignored when the unit does not carry fairness between months
- [ ] The carry-over block's balance, counted by hand: moving with the carry off, unchanged with the switch off and with the hours rule off
- [ ] The hard monthly and yearly caps still bind; in a re-plan the elapsed days count; the weight at 0, the switch off and the hours rule off each price nothing
- [ ] The explanation's match names the nurse, her overtime, her share and the hours priced; the per-nurse explanation carries it
- [ ] The service contract test's sample request and result carry the fields; the solver's suite, the service tests and the contract tests pass
- [ ] The backend suite stays green: the balance passes through the carry-over chain with a default of 0, and the tests that hold the app's blocks to every field of the solver's leave out a named set of the new fields, with a comment that tickets 50 and 51 remove it (as tickets 28 and 31 did)
- [ ] `solver/DESIGN.md` names the rule beside the other fairness rules and the contract change; `docs/ARCHITECTURE.md` section 6 names the fields

**Worth your review, already known:** a share is a fraction of an hour (51 hours among 24 nurses is about 2.1 each). Choose the whole-number unit the model works in and how a fraction rounds, the same in the model and the validator, and say what you chose and why.

## Comments
