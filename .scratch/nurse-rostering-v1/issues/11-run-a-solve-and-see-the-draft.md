# 11: Run a solve and see the draft

**What to build:** The unit manager picks a month, sees a summary of what the solver will receive (nurses, leave, pins) and the precheck warnings, chooses a time limit up to the cap, and starts a solve. He sees his position in the hospital-wide queue, then the best cost so far and the number of improving rosters as it runs, can stop early and keep the best roster found, and when it finishes sees the draft grid with the penalties per soft rule. Each solve replaces the draft's grid. The hours of a shift an open month uses cannot be changed.

**Blocked by:** 10 Leave

**Status:** ready-for-agent

- [ ] Solve input assembler builds the complete solver JSON from hospital rules, unit rules, Ramadan days, holidays, nurses with opening values or zero carry-over, leave, and credits days outside start and end dates like leave; the input is stored verbatim with the solve
- [ ] Precheck shown before solving via the solver's precheck call
- [ ] Time limit defaults to the unit's and is capped by the technical setting
- [ ] Solve rows go through the queue; the worker runs one at a time under a hospital-wide lock, writes queue position and progress, relays cancellation, retries a failed solve once and records the failure reason
- [ ] The draft roster is created or its grid replaced on success; the result is stored verbatim
- [ ] Draft grid shows the nurse × date cells with shift colours, leave, and the penalties per rule
- [ ] Changing a shift's hours is refused while any open month's roster uses it
- [ ] API tests run the whole flow with the scripted solver fake and once end to end with the real solver service on the four-nurse sample, including cancellation and the queue order across two units
