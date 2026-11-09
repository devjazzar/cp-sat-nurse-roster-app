# 56: Probation: what everyone sees

**What to build:** Wherever the unit's roster is read, a nurse on probation's row sits below the counted nurses under an "On probation" heading, with her preceptor's name: the manager's grid, My roster for every nurse of the unit, the print page, the Excel file and the CSV. The totals those pages and files show (nurses on a shift each day, headcounts) leave her out. My month names her preceptor and her probation's last day for her, and names the nurse on probation for her preceptor. Each month reads by its own state: she is under the heading in a month she is on probation in, and among the counted nurses from the month after it ends. Spec: `.scratch/nurse-rostering-v2/specs/probation.md`; the words: `GLOSSARY.md` (Nurse on probation, Preceptor).

**Blocked by:** 55 Probation: the preceptor, and the solve

**Status:** ready-for-agent

- [ ] The roster reads (the manager's grid, My roster, the print page) carry, per row, whether she is on probation in that month and her preceptor's name, and order her rows last under the heading
- [ ] The Excel file and the CSV show the same heading and order; their totals and the pages' totals leave her out
- [ ] A version in force planned before a probation changed (an end or extension not yet re-planned) is shown as it was planned, with the roster page's line from ticket 55
- [ ] My month for a nurse on probation: her preceptor (or that none is assigned yet) and her probation's last day; for a preceptor: the nurse on probation she is paired with; nothing of either for anyone else
- [ ] A colleague reads no more of her than the heading, her preceptor's name and her cells, as My roster shows any row; her leave is still the same empty cell as a day off
- [ ] The heading and the preceptor's name read well on a phone and to a screen reader (a row group with its own name), held against `better-interface`, `better-writing` and `better-accessibility` by hand
- [ ] Tests at the web API seam (the reads and both files, month by month across a probation's end, each role) and the frontend app-level suite (the heading on the grid, My roster and the print page; My month for both nurses); six runs at once
- [ ] `docs/ARCHITECTURE.md`'s exports and roles sections say so; the OpenAPI document and the generated client regenerated

## Comments
