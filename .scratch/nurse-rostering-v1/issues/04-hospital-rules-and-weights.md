# 04: Hospital rules and weights

**What to build:** The CNO opens the hospital rules and sees every rule the solver knows (hours per day, Ramadan and breastfeeding reductions, weekend days, forbidden successions, the hours and overtime switches and caps) and every weight, each explained in plain words, pre-filled with the reviewed defaults and flagged "defaults, review before the first solve" until saved. Saving validates every field, is audited, and feeds every later solve input.

**Blocked by:** 03 Management accounts

**Status:** ready-for-agent

- [ ] Hospital settings row seeded on first start with the reviewed defaults and a review flag
- [ ] Rules form with every field of the solver's hospital-wide block and explanations; validation errors name the field
- [ ] Weights form with every weight explained (what one unit of violation costs); zero switches a rule off
- [ ] Saving clears the review flag and writes an audit entry with before and after
- [ ] Only the CNO can read or change them (Deputy CNO read-only, others 403)
- [ ] API tests cover defaults, validation, saving and authorization
