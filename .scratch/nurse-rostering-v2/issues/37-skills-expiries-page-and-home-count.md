# 37: The expiries page and the home count

**What to build:** The CNO and the Deputy CNO see every unit's skills expired or expiring within 90 days, and every nurse with no record of a skill required to work, each row with the nurse, her unit, the skill, its state and date; a unit manager sees the same for his own unit on his Nurses page. Deactivated nurses and those past their end date are left out. The CNO's home shows how many rows the page has, beside the units with no manager. There is no notification; the page is the reminder.

**Blocked by:** 33 A nurse's skills

**Status:** ready-for-agent

- [x] One read endpoint scoped by role: the CNO and Deputy CNO every unit, a unit manager his unit; the System Admin and nurses refused. Rows: expired, expiring within 90 days of today on the hospital's clock, and no record of a required skill, for nurses active and not past their end date, oldest date first.
- [x] An Expiries page for the CNO and Deputy CNO, linked from their pages beside Nurses; the same list on the manager's Nurses page.
- [x] The CNO's home shows the count, worked out when read.
- [x] The horizon is fixed at 90 days; no job, no notification, no export.
- [x] The architecture document's screens-per-role paragraph names the page.
- [x] Tests at the web API seam for each role, the three row kinds, the horizon's edge, a deactivated nurse and one past her end date, and the home count; frontend tests for the page and the count.

## Comments

**From ticket 33 (2026-11-09):** no page says yet that an expiry has passed: the Nurses page, Rostering attributes and My
month show "until 30 Jun 2027" and a Retired badge only, because "expired" needs the hospital's today, which this page will
compute. Records are `nurses.models.NurseSkill.objects.current()`; for a kind whose `expires` is off, ignore the kept date.

**Implemented on 2026-11-09,** on branch `claude/ticket-37-expiries-page-79f9ec`, draft pull request
Nurse-Fold/cp-sat-nurse-roster-app#25, from `main` at `85b6f53`. The commits:
- `8395c70`: the endpoint, its tests and the regenerated client;
- `7cdb6c5`: the page, the manager's list, the home count, their tests and the architecture document;
- `93c8656`: what driving found;
- `6bc5e88`: the review's points;
- then this comment.

The suites ran locally, one at a time under the heavy-run lock, on a throwaway PostgreSQL 18 container of my own:
- the backend: 2901 passed, on `7cdb6c5`;
- the frontend: one `npm test` run, 696 passed, and the build succeeded;
- `makemigrations --check`: "No changes detected";
- the OpenAPI document and the client were regenerated from the export.

After `93c8656` and `6bc5e88` I reran the frontend's route-guard, navigation, home, Nurses and Expiries tests (168 passed).
I also reran the backend's expiries, skills, skills import, `solves` and authorization tests (1059 passed): `6bc5e88` touches
`skills_block`, which `solves` covers. The rest is untouched by those commits. GitHub runs the six parallel frontend runs and
the browser checks. No Playwright file changed.

**What the dev stack needs:** a **rebuild** (`docker compose up -d --build`) for the new endpoint and page. There is no
migration, and no change to compose, the `Dockerfile`, the solver or any dependency.

**What was built, criterion by criterion.**
- **One read endpoint scoped by role:** `GET /api/nurses/expiries` (`listExpiries`) answers `horizon_days`, `count` and
  `rows`. Each row has the nurse (id, hospital ID, full name), her unit, the skill's name, a state (`expired`, `expiring`,
  `no_record`) and the expiry, null for `no_record`.
  - Who reads it: the CNO and the Deputy CNO see every unit; a unit manager sees `membership.on_the_list_of` his unit, with
    no rows if he holds no unit. The System Admin and staff nurses get 403.
  - Who is left out: a nurse whose account is deactivated, or whose end date has passed (`membership.serving`, now shared
    with `belonging_to`).
  - The rules (`nurses.expiries`) read the solve input's code rather than restating it:
    - `nurses.skills.tracked`: a retired skill is no record;
    - `nurses.skills.counted_expiry`: a kind whose `expires` is off has no expiry;
    - `hospital.rules.required_skills()`: which skills are required;
    - `nurses.membership.today()`: the hospital's today.
  - `counted_expiry` moved from the import to `nurses.skills`, and `skills_block` and `as_rows` use it now, so the solve
    input, the Nurses page, the import and this list read a kept date alike.
  - Expired means the expiry is before today. Expiring means today to today + 90, both ends included.
  - Order: the oldest date first, then the `no_record` rows, each by the nurse's name and the skill's.
- **The page:** `/expiries` for the CNO and the Deputy CNO, titled "Expiries".
  - In the header it sits beside Nurses for the CNO, and beside Rostering attributes for the Deputy, who has no Nurses page.
  - Its columns are Name, Hospital ID, Unit, Skill, State and Expiry. The state is a badge, red for Expired. A no-record
    row's Expiry reads "Required to work".
  - A unit manager has the same list without the Unit column, as an "Expiries" section above his nurse list on the Nurses
    page. A manager with no unit has no section. The CNO's Nurses page has none, since she has the page.
- **The CNO's home** shows, after the units with no manager, either "N entries are on the Expiries page: skills that have
  expired or expire within 90 days, and skills required to work that a nurse has no record of." or "Nothing is on the
  Expiries page: …". The words link to the page. The count is the same answer's `count`, read when the home is.
- **Fixed at 90 days**, with no job, no notification and no export. `nurses.expiries.HORIZON` is the one place it is set;
  the API states it, and the pages read it from there.
- **The architecture document:**
  - section 3's table gains the row "Read the expiries";
  - section 4's Nurse skill paragraph says what the list holds;
  - the screens-per-role paragraph names it for the CNO, the Deputy and the manager's Nurses page.
- **Tests:**
  - `nurses/tests/test_expiries.py`, 19 tests at the web API seam:
    - every role;
    - the three kinds, in order;
    - expired from the day after the expiry;
    - the horizon's last day in and the next out;
    - a skill not required (listed when it expires, never as missing);
    - a kind that no longer expires, and a retired skill: no rows;
    - a renewal and a removal;
    - a deactivated nurse, one past her end date, one ending today, and one not yet started;
    - a manager's isolation, and a nurse due to join on both managers' lists;
    - the count, worked out when read.
  - `src/app.test.tsx`:
    - the page for the CNO, in the API's order;
    - the Deputy reaching it from the header;
    - the empty list and an unreadable one;
    - a manager sent home from it;
    - the route guards;
    - the manager's section, above his nurses and without a Unit column, and its absence from the CNO's Nurses page;
    - the home count: plural, singular, zero and unreadable;
    - the navigation lists.

**What was driven, and how.** On my own scratch stack `t37` (`e2e/stack.sh up`, ports 18737 and 18773), in the app's own
browser, with skills loaded into that stack's database (today was 9 November 2026):
- BLS, which expires and is required to work, and ACLS, which expires, are held until 2028 by everyone except:
  - Amal: BLS expired on 31 October;
  - Badr: no BLS;
  - icu01: BLS on the horizon's last day, 7 February, and ACLS on 15 January;
  - icu02: BLS on 8 February, one day past the horizon;
  - Emad: deactivated, with BLS expired;
  - icu03: past her end date with her account still active, and no BLS.
- As Carla (CNO), the home read "4 entries are on the Expiries page…". The link opened the page with exactly four rows, in
  this order:
  - Amal, ER, BLS, Expired, 31 Oct 2026;
  - icu01, ICU, ACLS, Expiring, 15 Jan 2027;
  - icu01, ICU, BLS, Expiring, 7 Feb 2027;
  - Badr, ER, BLS, No record.

  Emad, icu02 and icu03 were nowhere.
- As Hala (Deputy CNO): the same four rows, reached from the header.
- As Omar (ICU's manager), on his Nurses page: only icu01's two rows, with icu03 not among them though she is on his nurse
  list. As Mona (ER): only Amal and Badr, with deactivated Emad not among them.
- At phone width (375 px), the manager's table scrolls sideways inside its labelled region.

The stack is down and its volumes gone.

**What was found, and fixed.**
- Driving showed the manager's list below 64 nurses, where nobody would see it before a solve. It now sits above them, and
  a test holds that.
- The first home sentence read "4 skills are on Expiries, expired, …", which counted a missing record as "a skill on" the
  page. It is reworded with the spec's word, "entries".

**Findings for you, not fixed:** none.

**What was NOT checked.**
- A screen reader, beyond reading the accessibility tree: the table's region is named, the headers are column headers, and
  the state is text in a badge.
- The six parallel frontend runs and the browser checks, locally: they are GitHub's, on the pull request.
- The whole backend suite after `6bc5e88`, locally: the files it touches were rerun, and GitHub runs the whole suite.

**Decisions taken here, and Worth your review.**
- **Worth your review, 1: a nurse due to join is on the joining unit's manager's list,** named under his unit, as his Nurses
  page lists her and he reads her skills (architecture section 3). The CNO's and the Deputy's rows name her unit today.
- **Worth your review, 2: rows with no record come last,** after every dated row, since "oldest date first" says nothing of
  rows without a date.
- **Worth your review, 3: the horizon's ends are both in.** An expiry today is "Expiring", since its last day still counts,
  and one 90 days away is in.
- **Worth your review, 4: a nurse whose end date is today is still listed,** since today is still one of her days.
- **Worth your review, 5: the count comes with the list,** as `count` on the same answer. No "home data" endpoint exists to
  carry it, and that way the home always matches the page. The home reads the whole list to show one number, which is cheap
  at a hospital's size.
- **Worth your review, 6: the Deputy's link sits beside Rostering attributes,** because the Deputy has no Nurses page.
- A skill that is not required to work is listed when it expires, but never as missing. Story 74 says "every skill expired
  or expiring", and story 75 says "no record of a required skill".
- A nurse who has not started yet is listed: she is active and her end date has not passed.

**Review:** `code-review` against `85b6f53`, both axes.
- **Standards:** no hard violation. Fixed:
  - the 90 days was written in four places; the API now states `horizon_days` and the pages read it;
  - what the list holds was said three ways; it is one pair of phrases now;
  - the skills API's docstring now names the expiries it serves.

  Kept:
  - `ExpiryRow` carries the skill's name and no id: names are unique, and nothing here acts on a skill;
  - the endpoint lives in `skills_api.py` beside `my-skills`, since it reads nurses' skills;
  - "Expiries" (a page) and `serving` are not added to the glossary: the glossary names domain terms, not pages, and
    `serving` sits beside `no_longer_serving`;
  - the `showUnit` flag, with two callers;
  - the test that the CNO's Nurses page reads no expiries asserts after the page has loaded; it waits for nothing.
- **Spec:** nothing missing, and nothing wrong. Fixed:
  - "a retired skill is no record" was written twice; it is `nurses.skills.tracked` now, used by the solve input and the
    list;
  - a stale test name.

  Kept:
  - expired as `expiry < today`, inline: `solves.input.barred_from` reads per month and cannot be called here, and the
    module's docstring points to it;
  - the count on the list's answer (point 5).

**Things later tickets should know.**
- **Anyone changing what "expired", "required" or "a record" means:** `nurses.expiries` reads `tracked`, `counted_expiry`
  and `required_skills`, as the solve input does. The day-after rule is restated there beside `solves.input.barred_from`
  and the solver's `barred_days`, so change all three together.
- **Ticket 38** (barred pins and requests): nothing here touches it.
- **An export of the list** is out of scope (spec). If one comes, write it through `nurses.spreadsheets.csv_response`
  (ticket 36).

**Reviewed by the user (2026-11-09):** all six points kept as recommended.
- A joining nurse is on her joining unit's manager's list.
- No-record rows come last.
- Both ends of the 90 days are in.
- A nurse whose end date is today is listed.
- The count comes with the list.
- The Deputy's link sits beside Rostering attributes.
