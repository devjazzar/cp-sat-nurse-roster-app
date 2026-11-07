# 01: The Ramadan cards: confirm or shift a whole Ramadan

**What to build:** On Holidays and Ramadan the CNO sees, above the month table, one card per Ramadan with a day in the year shown ("Ramadan 1448: 8 February – 8 March 2027, 29 days. The calendar's."), its first and last day prefilled from the Umm al-Qura calendar and editable. Confirm fixes every Gregorian month the confirmed Ramadan touches, in the next or the previous year too, exactly as fixing each month by hand would, and the card then reads "The CNO: 9 February – 9 March 2027. The calendar says 8 February – 8 March." in plain text. Confirming the calendar's own dates still fixes the months. The month table and "Use the calendar" stay; every other role sees the page as today. Spec: `.scratch/ramadan-and-eid-from-the-calendar/spec.md`.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] The hospital API answers the Ramadans of a year: every Ramadan with at least one day in that Gregorian year, in date order, named by its Hijri year; none, one or two, and one across New Year listed on both years
- [ ] Each card carries the days in force assembled month by month (first day, last day, count), whose they are ("the calendar's" when every month touched is derived, "the CNO" when any is fixed), and the calendar's first and last day
- [ ] Confirming takes a first and a last day and fixes every month from the first day's to the last day's with the confirmed days that fall in it, through the existing per-month fix, under its lock, with one `ramadan_dates.changed` audit entry per month whose fixed dates change and none for a month unchanged
- [ ] A month the calendar gave Ramadan days to that the confirmed range no longer touches is fixed to no days
- [ ] Confirming the calendar's own dates writes fixed rows for every month touched; confirming again overwrites the earlier confirmation in every month touched
- [ ] Refused beside the field: a last day before the first, a day outside the years the calendar covers, more than about 35 days between the two
- [ ] Only the CNO may confirm (403 for every other role); the cards are read by the CNO only and the page for every other role is unchanged
- [ ] The card's derivation is the solver's own calendar module, imported read-only as the month derivation is today
- [ ] `hijridate` gets an upper bound on its major version in the solver's dependencies and the lock file, and a line in `docs/ARCHITECTURE.md` section 11
- [ ] The page: the cards for the CNO with confirm as prefilled, shifting a day, the words after confirming, a refusal beside the field, the status line and focus after confirming, no sideways scroll at 375 px
- [ ] API tests under pytest beside the Ramadan months' tests; the frontend's app-level suite in its "holidays and Ramadan page" block; the usual full suites and `e2e/ci.sh`
