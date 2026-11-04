# 18: Exports and print

**What to build:** Any roster version downloads as CSV and as an Excel workbook (one row per nurse, one column per date, then hours and shift counts) and opens as a print-friendly page the browser saves as PDF. Managers export their unit; the CNO and Deputy CNO any unit.

**Blocked by:** 16 Changes after approval

**Status:** ready-for-agent

- [ ] CSV and Excel export of a chosen version with the agreed columns
- [ ] Print page for a version, styled for paper
- [ ] Authorization: unit-scoped for managers, hospital-wide for approvers, none for nurses beyond their own unit's print page
- [ ] API tests cover both exports' content and authorization
