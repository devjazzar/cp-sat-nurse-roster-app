# Ramadan and the Eids proposed from the Umm al-Qura calendar

Status: ready-for-agent
Type: enhancement
Published: 2026-11-07 by /to-spec

Spec drawn from the grilling of 2026-11-07 (eleven questions in two rounds, every one answered as recommended; the
decisions and the code facts they rest on are also in the main session's notes as `grill-7-ramadan.md`). Vocabulary:
`GLOSSARY.md`. Decisions and their reasons: `docs/ARCHITECTURE.md` and `docs/adr/`. Where this spec and those documents
disagree, the documents win and this spec is wrong.

## Problem Statement

**Ramadan is confirmed twice, month by month.** The Holidays and Ramadan page already derives every month's Ramadan days
from the Umm al-Qura calendar, and they are in force until the CNO fixes that month after the moon sighting. But the real
unit is the Hijri month, which straddles two Gregorian months, so after the sighting the CNO fixes February and March each
as a range or a list, working out by hand where the shifted Ramadan falls in each. A Ramadan the calendar got right is
never marked as checked: it reads "The calendar" for good, and nobody can tell a confirmed month from one no one looked at.

**The Eids and the national days are typed from scratch every year**, though the calendar knows when they fall: Eid al-Fitr
follows the Ramadan the CNO just confirmed, Eid al-Adha follows Arafah day, National Day and Founding Day never move.

**A change after a solve warns nobody.** An approved roster's cells do not move when the Ramadan days change, and a nurse's
hours owed and the month close already read the days as they stand. But a draft or a submitted roster solved before the
change is never warned of it: the "changed since its solve" check compares nurses only (joined, left, gender, leave, pins,
a close), never the month's Ramadan days or public holidays. A unit manager whose approved month just gained or lost a
Ramadan day learns nothing either.

## Solution

**A card per Ramadan** above the month table on Holidays and Ramadan, for the CNO: "Ramadan 1448: 8 February – 8 March
2027, 29 days. The calendar's." Its first and last day are prefilled from the calendar and editable. **Confirm** writes the
fixed dates of every Gregorian month the confirmed Ramadan touches, in the next or the previous year too, and the card then
reads "The CNO: 9 February – 9 March 2027. The calendar says 8 February – 8 March." in plain text: a difference is the
expected case, not a warning. Confirming the calendar's own dates still fixes the months, so the record says the sighting was
checked. Nothing new is stored: the card reads the months as they stand, fixed or derived, and the month table with "Use the
calendar" stays as it is.

**A holidays card** on the same page, for the CNO, proposing what the calendar knows and the year's holidays do not yet
hold: Eid al-Fitr, four days from the day after the 29th day of the Ramadan **in force** (fixed or derived), so that a
Ramadan the CNO shortened or lengthened moves its Eid with it, and a 30th Ramadan day is a holiday too; Eid al-Adha, four
days from Arafah day (9 Dhu al-Hijjah) by the calendar, since its sighting is its own; National Day (23 September) and
Founding Day (22 February), one line each. Each line's first day and length are editable; **Add** creates the named public
holidays, skipping any date already entered. A line shows until its first day is a public holiday; there is nothing to
dismiss and nothing stored, so a hospital that grants no Eid holidays keeps seeing the line.

**After a solve**, the month's Ramadan days and public holidays join what the draft and the submitted roster are warned of
as changed since, blocking nothing, like a correction to leave; and every unit manager whose unit has a draft, submitted or
approved roster in a month touched is told once, naming the month. Nothing else happens: approved cells stay; the next solve
or re-plan uses the dates as they stand; what a solve used stays stored with it.

Every other role sees the page as today: the tables, no cards.

## User Stories

### The Ramadan cards

1. As the CNO, I want the page to show each Ramadan as one card with its calendar dates and its length, so that I see at a
   glance when the calendar expects it, without reading two months of a table.
2. As the CNO, I want the card's first and last day prefilled with the calendar's, so that confirming a Ramadan the sighting
   agreed with is one press.
3. As the CNO, I want to move the first day, the last day or both by a day or two before confirming, so that the announced
   sighting is recorded without my working out which days fall in which month.
4. As the CNO, I want Confirm to fix every Gregorian month the Ramadan touches, so that a Ramadan across February and March
   is confirmed once, not twice.
5. As the CNO, I want confirming the calendar's own dates to mark the months as fixed by me, so that a Ramadan I checked
   can be told from one nobody looked at.
6. As the CNO, I want the card to show my dates and the calendar's beside each other after confirming, in plain words, so
   that I can check what I entered without being warned about a difference that is the normal case.
7. As the CNO, I want a card to read the months as they stand, so that a month I fixed by hand in the table and a month
   left to the calendar still add up to one Ramadan on the card.
8. As the CNO, I want the page for a year to list every Ramadan with a day in that year, two in a year like 2030 and one
   that begins in December and ends in January, so that none is missed and one across New Year can be confirmed from
   either year.
9. As the CNO, I want to confirm a Ramadan again after a first confirmation, so that a correction overwrites what I entered
   before, in every month touched.
10. As the CNO, I want a Ramadan moved so that a day lands in a month the calendar gave none to be recorded in that month
    too, so that the solver sees every day I confirmed.
11. As the CNO, I want "Use the calendar" on a month to keep working as today, so that I can undo a month by hand when I
    need to.
12. As the CNO, I want a first or last day outside the calendar's range of years, or a last day before the first, refused
    beside the field, so that a slip is caught before anything is written.
13. As the CNO, I want every month a confirmation changes to appear in the audit log as a Ramadan dates change, so that who
    confirmed what, and when, is on record as it is for a month fixed by hand.
14. As the Deputy CNO, a unit manager, a staff nurse or the System Admin, I want the page unchanged, so that nothing I
    cannot act on is put in front of me.

### The holidays card

15. As the CNO, I want the page to propose Eid al-Fitr for the year from the Ramadan in force, so that an Eid follows the
    Ramadan I confirmed and not the calendar's.
16. As the CNO, I want the Eid al-Fitr proposal to start the day after Ramadan's 29th day and run four days, so that a 30th
    day of Ramadan is a holiday as the Labour Law counts it.
17. As the CNO, I want the page to propose Eid al-Adha from Arafah day for four days by the calendar, so that the hajj
    holiday is offered even though its sighting is announced on its own.
18. As the CNO, I want National Day and Founding Day proposed on their fixed dates, so that I never type them.
19. As the CNO, I want to change a proposal's first day and its length before adding, so that the circular the hospital
    follows, which may give more days or start a day later, is what gets entered.
20. As the CNO, I want Add to create the holidays under the proposal's name, one row per day, so that they read like the
    holidays I enter by hand.
21. As the CNO, I want a date already entered as a holiday skipped rather than refused, so that a holiday I entered by hand
    does not block the rest of the Eid.
22. As the CNO, I want a proposal to disappear once its first day is a holiday, so that the card only shows what is still
    to do.
23. As the CNO, I want a proposal I do not want to stay as a line I can ignore, so that nothing else is stored or asked.
24. As the CNO, I want each added holiday in the audit log as a holiday created, so that the record matches a holiday
    entered by hand.
25. As a unit manager, I want an Eid holiday added this way to count for the solver like any public holiday, so that my
    unit's weekend headcounts apply on it.

### After a solve

26. As a unit manager, I want my draft warned that the Ramadan days or the public holidays of its month changed since its
    solve, so that I solve again or submit knowing it.
27. As a unit manager, I want that warning to block nothing, so that I can still submit a draft whose month changed, as I
    can after a correction to leave.
28. As the Deputy CNO or the CNO, I want a submitted roster to show that something changed since it was submitted when the
    Ramadan days or the holidays moved, so that I decide knowing it.
29. As a unit manager, I want one notification naming the month when its Ramadan days or holidays change while my unit has
    a draft, a submitted or an approved roster in it, so that I can re-plan or solve again if the hours have shifted.
30. As a unit manager, I want nothing to happen to an approved roster's cells when the dates change, so that the roster my
    nurses see stays what was approved until I change it.
31. As a unit manager, I want the next solve or re-plan to use the dates as they stand, so that the roster that replaces the
    old one follows the confirmed Ramadan.
32. As a staff nurse, I want the hours my month asks of me to follow the confirmed Ramadan days, as they do today, so that
    the balance I see is right.
33. As the System Admin, I want a solve to keep the Ramadan days and holidays it was given, so that the solve history says
    what the solver used whatever changed later.
34. As a unit manager with no roster in a changed month, I want to be told nothing, so that I am not told of months I am
    not working on.

### Fit with the rest

35. As the hospital's IT, I want the calendar worked out from the package already in the image, offline, so that the web
    container needs no internet any more than the solver does.
36. As a developer, I want the Umm al-Qura package pinned with an upper bound like every other dependency and named among
    the pinned versions, so that a new major version cannot slip in with an update.
37. As a developer, I want the card's derivation to be the solver's own calendar module, so that a card, a month row and a
    solve can never disagree on what the calendar says.

## Implementation Decisions

### Storage

- **Nothing new is stored for the cards.** A Ramadan card is read from the months as they stand: each Gregorian month's
  fixed dates or derived dates, exactly as the month table shows them. A holiday proposal is read from the calendar, the
  Ramadan in force and the year's public holidays. The per-month fixed Ramadan dates and the public holidays stay the only
  records, with no history of their own, as section 9 says: what a solve used is stored with it and the audit log keeps the
  rest.
- **A submission records the month's Ramadan days and public holidays at submit** beside the nurses it records today, so
  that a submitted roster's "changed since" can compare them. This is the one schema change.

### The Ramadan cards

- **Which Ramadans a year's page lists:** every Ramadan of the Hijri calendar with at least one day in the Gregorian year
  shown, by the calendar's dates, in date order. There may be none, one or two. The card is named by its Hijri year.
- **What a card shows:** the days in force, assembled month by month from the months the calendar's Ramadan touches and
  any neighbouring month holding fixed days that continue it, as a first day, a last day and a count; whose they are ("The
  calendar's" when every month touched is derived, "The CNO" when any is fixed); and, when they differ from the calendar's,
  the calendar's first and last day in plain text, no warning colour.
- **Confirming** takes a first and a last day, each a calendar date, refused when the last is before the first, when either
  is outside the years the calendar covers, or when the two are more than about a month apart (a Ramadan is 29 or 30 days;
  a generous bound such as 35 catches a wrong year without second-guessing the sighting). It fixes every Gregorian month
  from the first day's to the last day's: each month's dates are the confirmed days that fall in it, written as that month's
  fixed dates, exactly as fixing the month by hand would, under the same lock, with the same audit entry per month changed
  and no entry for a month whose fixed dates are unchanged. A month the calendar gave Ramadan days to that the confirmed
  range no longer touches is fixed to no days, so the calendar's days there do not survive beside the confirmation.
- **Confirming the calendar's own dates writes fixed rows** for every month touched: the audit's comparison already treats
  derived and fixed as different states, so this follows from fixing by hand.
- **"Use the calendar" per month stays** as it is; a card whose month was returned to the calendar reads the months as they
  then stand.
- **Pinning the package:** the Umm al-Qura package gets an upper bound on its major version, and the session that merges
  the grilling branches names it in the architecture's pinned versions. The derivation stays the solver's calendar module,
  imported read-only by the web container, as today.

### The holidays card

- **Proposals for the year shown**, in date order, each with a name, a first day and a length:
  - **Eid al-Fitr:** first day the day after the 29th Ramadan day **in force** of the Ramadan that ends in or just before
    that Eid, counting the days in force in order (so a Ramadan the CNO fixed to 30 days has its 30th day inside the Eid,
    and one fixed to start a day late moves its Eid a day). Length four. A Ramadan with fewer than 29 days in force (a
    month fixed to none, a short list entered by hand) has no 29th day, and then no Eid al-Fitr is proposed for it: the
    CNO enters the Eid by hand, as today.
  - **Eid al-Adha:** first day Arafah day, 9 Dhu al-Hijjah, by the calendar. Length four.
  - **National Day:** 23 September. **Founding Day:** 22 February. Length one.
- **A proposal is shown while its first day is not a public holiday.** Nothing records a dismissal. A proposal whose days
  all exist already is gone by that rule; one whose first day was entered by hand under another name is gone too, which is
  accepted.
- **Adding** creates one public holiday per day of the proposal, named as the proposal, each audited as a holiday created
  like one entered by hand, skipping dates that are holidays already; the answer says how many were added and which were
  skipped. The first day and the length are editable before adding, bounded to the year shown for the first day and to a
  small count (such as 1 to 14) for the length.
- **A proposal crossing New Year** (an Eid whose days run into January) is listed on the year its first day falls in, and
  adds its later days in the next year, as a confirmation writes a month in the next year.

### After a solve

- **The draft's "changed since its solve"** gains two month-level changes beside the per-nurse ones: the month's Ramadan
  days and its public holidays, each compared as the stored solve input's list against the month as it stands. The API's
  list of changes, today keyed by a nurse, carries a month-level change with no nurse; the page words it as "The Ramadan days
  of March 2027 changed since this draft was solved" and the same for holidays. Nothing blocks: submit goes through with the
  warning, and the check on submit runs on the month as it stands, as it does today.
- **The submitted roster's "changed since it was submitted"** compares the same two lists against what the submission
  recorded at submit, so that the reviewer's flag turns on for them as for a nurse's leave.
- **The notification**, one new kind, goes to the manager of every unit with a roster (draft, submitted or approved) in a
  month whose Ramadan days or public holidays changed, once per change per month, from inside the transaction that makes
  the change, after its audit entry, like every notification. Its payload is the month; its words name the month and say
  the Ramadan days, or the public holidays, changed. A confirmation touching two months with rosters tells the manager twice,
  once per month. The CNO, who made the change, is not a recipient; a manager with no roster in the month is not either.
- **Nothing else moves.** Approved cells, versions and pins stay. The next solve or re-plan assembles its input from the
  dates as they stand, as today. My month and the month close already read them as they stand.

### The page

- **The CNO only** sees the two cards; the page for every other role is as today. The cards are forms like the ones on the
  page: confirm and add refuse beside the field, say what they did in the page's status line, return focus where the user
  was, and fit 375 px with no sideways scroll.

## Testing Decisions

A good test drives a public boundary and checks what a user or a caller sees: the API's answers and the rows they leave,
the audit entries, the notifications a manager reads, the page's words and buttons. No test reads a card's internals or a
proposal's arithmetic except through those answers.

The seams, agreed with the user, all existing:

1. **The hospital API under pytest**, beside the Ramadan months' and the public holidays' tests: the Ramadan cards of a year
   (none, one, two; one across New Year), confirming with the calendar's dates and with shifted ones, the fixed rows and
   audit entries it leaves and the ones it does not, confirming again, a month the shift leaves behind fixed to none, the
   refusals, the derivation matching the solver's; the holiday proposals (Eid al-Fitr following a shortened and a
   lengthened Ramadan, Eid al-Adha, the fixed days), adding with skipped dates, a proposal gone once its first day exists;
   403 for every other role on the writes and the cards hidden or absent for readers.
2. **The roster and notification APIs under pytest**, beside the draft's "changed since" tests and the notification events'
   tests: a draft and a submitted roster warned after a Ramadan change and after a holiday change, unwarned when nothing
   moved, submit going through; the manager of a unit with a draft, a submitted and an approved roster told once per month,
   a manager with no roster not told, the CNO not told.
3. **The frontend's app-level Vitest suite** over the generated client and the stubbed fetch, in its "holidays and Ramadan
   page" block: the cards for the CNO and their absence for a reader, confirming as prefilled, shifting a day, the words
   after confirming, adding a proposal, a refusal beside the field, and the draft page's new warning line.

No new Playwright check: the CNO's journey already opens the page, and the cards are forms like the ones it has. The
backend's and the solver's suites, the frontend's six parallel runs and `e2e/ci.sh` run as for every ticket.

## Out of Scope

- A dismissed or declined proposal remembered; a proposal for any other holiday than the four named; Arabic names.
- A history of Ramadan dates or holidays of their own; both stay removable with no history, as section 9 says.
- Any change to an approved roster, a version or a pin when the dates move; any automatic re-plan.
- A notification to nurses, the Deputy CNO or the System Admin about a date change.
- Fetching the sighting or the government's holiday circular from the internet: the web container stays offline for this.
- Changing how a month is fixed or returned to the calendar in the table.
- The solver and its contract: it already takes the month's Ramadan days and holidays as lists.

## Further Notes

- The Saudi Labour Law's implementing regulation (article 24, as the Ministry of Human Resources' knowledge centre and its
  yearly announcements state it) gives Eid al-Fitr four days from the day after 29 Ramadan and Eid al-Adha four days from
  Arafat Day; the public sector's dates come by circular each year, which is why the first day and the length of a proposal
  are editable rather than fixed.
- The Umm al-Qura data in the package covers 1925 to 2076 and does not need yearly updates; the calendar is fixed tables.
- No ADR and no glossary change came out of the grilling: the "Ramadan days" entry ("Derived from the Umm al-Qura calendar
  unless the CNO fixes them after the moon sighting") and section 4's wording stay true. If an ADR is written after all
  during implementation, its number is 0016: 0010 to 0015 are taken by the grilling sessions running alongside this one.
- The main session merges the grilling branches afterwards; the line in the architecture's pinned versions and any mention
  of the cards under the page in section 8 belong to it.
