# 02: The holidays card: the Eids and the national days proposed

**What to build:** On Holidays and Ramadan the CNO sees a card proposing, for the year shown, what the calendar knows and the year's public holidays do not yet hold: Eid al-Fitr, four days from the day after the 29th day of the Ramadan in force; Eid al-Adha, four days from Arafat Day by the calendar; National Day (23 September) and Founding Day (22 February), one day each. Each line's first day and length are editable; Add creates the named public holidays, skipping any date already entered, and the line is gone once its first day is a holiday. Nothing is stored for a proposal and nothing is dismissed. Every other role sees the page as today. Spec: `.scratch/ramadan-and-eid-from-the-calendar/spec.md`.

**Blocked by:** 01 The Ramadan cards (the Ramadan in force, assembled across months)

**Status:** ready-for-agent

- [ ] The hospital API answers the proposals of a year in date order, each with a name, a first day and a length, only while its first day is not a public holiday
- [ ] Eid al-Fitr's first day is the day after the 29th Ramadan day in force, counting the days in force in order, so a Ramadan fixed to 30 days has its 30th day inside the Eid and one fixed to start a day late moves its Eid a day; a Ramadan with fewer than 29 days in force proposes no Eid al-Fitr
- [ ] Eid al-Adha's first day is Arafat Day (9 Dhu al-Hijjah) by the calendar; National Day and Founding Day fall on their fixed dates; the lengths are four, four, one and one
- [ ] Adding takes a name, a first day in the year shown and a length from 1 to 14, creates one public holiday per day under that name through the existing holiday create, each audited as `public_holiday.created`, skips dates that are holidays already, and answers how many were added and which were skipped
- [ ] A proposal whose days run into January is listed on the year its first day falls in and adds its later days in the next year
- [ ] Only the CNO may add (403 for every other role); the card is read by the CNO only and the page for every other role is unchanged
- [ ] An added holiday reaches the solver like any public holiday (a solve input test)
- [ ] The page: the card for the CNO with each line's first day and length editable, Add with its status line naming what was added and skipped, a refusal beside the field, focus after adding, the line gone afterwards, no sideways scroll at 375 px
- [ ] API tests under pytest beside the public holidays' tests, including Eid al-Fitr after a shortened and a lengthened Ramadan; the frontend's app-level suite in its "holidays and Ramadan page" block; the usual full suites and `e2e/ci.sh`
