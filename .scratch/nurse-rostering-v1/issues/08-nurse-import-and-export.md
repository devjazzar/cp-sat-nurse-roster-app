# 08: Nurse import and export

**What to build:** The CNO downloads a CSV template, uploads a filled one, sees a preview that reports every row's problem (unknown unit, duplicate hospital ID, bad date) before anything is saved, confirms, and receives the generated passwords as a sheet shown once. The CNO exports the current staff list at any time.

**Blocked by:** 07 Nurses; 07a Correct a nurse's details

**Status:** ready-for-agent

- [ ] Template download with the exact columns (hospital ID, full name, gender, unit, start date)
- [ ] Preview reports per-row problems and saves nothing until confirmed; a file with any error cannot be confirmed
- [ ] Confirmation creates nurses and accounts in one transaction and returns a password sheet once
- [ ] Staff list export as CSV with the profile fields a CNO may see
- [ ] API tests cover template, preview errors, confirm, and export
