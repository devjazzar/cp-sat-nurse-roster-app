# 06: The skills CSV

**What to build:** The CNO imports skills in bulk from a CSV of hospital ID, skill and expiry, beside the nurse import and in the same way: download a template, preview the file row by row with every problem named, confirm by sending it again. A row for a skill a nurse already holds sets its expiry, so renewals come in bulk. The nurse import template and the staff list are unchanged.

**Blocked by:** 03 A nurse's skills

**Status:** ready-for-agent

- [ ] Template, preview and confirm endpoints beside the nurse import's, with the same encodings (UTF-8 or UTF-16 with a byte order mark, others refused), size and row limits, in-memory handling, preview token and re-judging on confirm.
- [ ] Problems named per row: an unknown or inactive hospital ID, an unknown or retired skill, a missing or malformed expiry on an expiring kind, a date on a non-expiring kind, a nurse and skill repeated in the file.
- [ ] Confirm records new skills and sets the expiry of held ones under the nurses' row locks, in one transaction; nothing is saved when any row has a problem or the file no longer means what was previewed.
- [ ] Audit: `nurse.skills_imported` with who and how many rows, nothing from the file; the template is not logged.
- [ ] A Skills import page beside the nurse import, same flow; the nurse import template and the staff list columns unchanged.
- [ ] The architecture document's import section gains the skills CSV.
- [ ] Tests at the web API seam for the template, each problem, a renewal, the token and the audit entry; frontend tests for the page through the app test file.
