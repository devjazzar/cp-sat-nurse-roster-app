# 05: Shift catalogue, leave types, public holidays and Ramadan dates

**What to build:** The CNO maintains the shift catalogue (code, display name, hours, start and end time, colour, active), the leave types, the public holidays per year, and for each month either fixes the Ramadan dates after the moon sighting or leaves them derived from the Umm al-Qura calendar. Renaming a display name is free; renaming a code is recorded so histories can follow later.

**Blocked by:** 03 Management accounts

**Status:** ready-for-agent

- [ ] Shift catalogue list and form with code, display name, hours, start and end time, colour, active; seeded with the default shifts
- [ ] A code rename is recorded (old name, new name, date) for later history mapping
- [ ] Leave types list and form, seeded with common types
- [ ] Public holidays per year; a date cannot be entered twice
- [ ] Ramadan dates per month: derived and shown, or fixed by the CNO as a range or a list
- [ ] All changes audited; only the CNO may change them; every role may read the catalogue
- [ ] API tests cover each resource and the derived Ramadan days for a sample month
