# 10b: Make the frontend tests reliable under load

**What to build:** The frontend suite failed when the machine was busy, with `findBy` errors and test timeouts. Find out why, fix the causes without weakening a test, and show how much load it now takes, before ticket 11 adds to the same file.

**Blocked by:** 10a Fixes from the review of tickets 07 to 10

**Status:** ready-for-agent

- [x] The cause is measured, with what was ruled out, and the one real ordering bug that turned up is reported, then fixed in the last comment
- [x] Every page's chunk is imported before the tests, with the code split as in production
- [x] Timeouts are raised only with a stated reason, and a missing element or a hang still fails, and says which
- [x] No test deleted, skipped or retried: 312 before and after, with the same names, and 8 more with the last comment
- [x] From a clean export the suite passes alone and in 3 rounds of 6 copies at once, and the level of load where it stops passing is stated
- [x] The build passes; the backend, the solver, the README's command and CI are unchanged

## Comments

Implemented on 2026-11-05, in the tests alone: `frontend/src/test-setup.ts` and two lines of `frontend/src/app.test.tsx`. Every run below was on an 8-core machine (4 performance, 4 efficiency) with 8 GB of memory, already swapping, with the dev stack and other sessions running, on `git archive` exports after `npm ci`, using one copy of `npx vitest run` per process.

| | alone | 6 copies | 9 copies | 12 copies |
|---|---|---|---|---|
| Before (d515cd8) | 312 of 312 | 11 failures, in all 6 copies | not run | 2 to 7 per copy, measured before this ticket |
| Chunks imported first, old timeouts | 312 of 312 | 0, twice | 68 failures, in all 9 copies | 15 to 22 per copy |
| This commit | 312 of 312 | 0 in each of 3 rounds | 0 in one round | 3 failures in 3 of 12 copies, one round |

**The cause is two waits measuring the machine, and the first page's import was what used them up.** A `findBy` gives up after 1 s and a test after 5 s, while nothing in a test waits on anything real. Each page is a chunk of its own (`autoCodeSplitting`), imported the first time a test visits it, inside that test's `findBy`. So a page's first test paid for the import: alone, the first test's render and find took 870 ms and the same one afterwards 13 ms. Under 6 copies a test cost more than 5 times what it does alone, so the first test (`/ sends a stranger`) and the first visit to the users page ran out of their second. Under 6 copies with very long timeouts, the slowest tests were exactly these first visits (unit rules, users, the first test, holidays, nurses), and all 312 passed in all 6 copies.

**Importing the chunks first is what fixes 6 copies.** With that alone and the old timeouts, 6 copies had no failures. The longest `findBy` was then 630 ms and the longest test 1.7 s, so the margin against 1 s was thin.

**The timeouts are raised to 5 s and 20 s for that margin, and this was measured:** the same tree at 9 copies had 68 failures with the old timeouts and none with the new. A test only ever passes sooner than these limits, because `fetch` is stubbed: `app.test.tsx` has no test that passes by a wait running out, and no `.rejects`. Checked on purpose: a missing element still fails at 5 s with `Unable to find`, a hung test at 20 s, and a chunk that throws fails the whole file before any test runs.

**A real ordering bug, reported and not fixed here; the last comment fixes it.** With the timeouts raised, one copy at 9 still failed "leaves when told to, whatever the answer then says", with the page on Home 5 s after clicking Nurses: a lost click, not slowness. Choosing Leave sets the address before the new page commits, and until the effect that removes it has run, `LeavePageGuard`'s blocker is still registered with `holding` true from before. It blocks the next navigation, and the question never shows, because the guard's page is on its way out. Repeating that test 100 times in each of 10 copies at once with logging in the guard: of 1010 clicks, 24 came while the router was `pending` and 23 of those were blocked as `/ -> /nurses`. None of the 986 made while it was `idle` was. Nine of the 10 copies failed. **Nothing is lost but the click:** the request was already abandoned, no password is at stake, and the window is the few milliseconds after a click on Leave, so a person is unlikely to hit it. The test now waits for the Home page's heading before following the next link, which is what a person can do, and asserts one thing more. After that, 1010 of 1010 clicks came while `idle`, with no failures in the same 10 copies. To fix the page itself, the guard could stop blocking as soon as Leave is chosen; that is a small change of application behaviour, so it is left for your decision.

**12 copies is past what this machine can take reliably.** A test there costs about 19 times what it does alone, against about 4 at 6 copies, and memory is why: each copy holds about 600 MB across Vitest and its worker, and swap-outs jump. The 3 failures hit the 20 s timeout, and each time the following test also took 15 to 19 s against 1 to 4 s for its neighbours, so the machine stalled. 60 repeats of each of those two tests in each of 10 copies had no failures, so they do not hang. An earlier run of the previous tree at 12 copies passed. **9 copies passed once and 12 is sometimes red:** the limit lies between them here, and would differ on a machine with more memory.

Ruled out, by measurement:

- **Expensive `getByRole`:** not the cause. Testing Library queries take about 30% of the busy time alone, and `getByRole` about 1 ms on the login page. The suite passes under load with every query as it was. `defaultHidden` would save about 6% and stop a hidden element being treated as hidden, so it was not used. Time per query on the largest page, 282 elements, was not measured on its own.
- **Leaks between tests slowing them down:** the same small test took 12 ms at the start and at the end of the file. The DOM is empty between tests. Nothing held open by `hold` reaches module state: the only module variable that changes is `onSessionEnded`, which each router replaces.
- **Leaks that exist but do no harm, left as they are:** query clients keep their garbage-collection timers, 811 by the end of the file. Clearing them leaves 85, and neither heap nor peak memory changes. Base UI's scroll lock is still on `body` at the start of 22 tests, after one that ended with a dialog open, and no test reads it.
- **A pool setting:** `threads` peaks at 585 MB against 611 MB, which changes nothing.
- **Splitting the file:** not done. Nothing leaks across it, a split would import the chunks once per file and add a worker of about 280 MB per file, and memory is the limit. It may still be wanted for reading it.

Choices worth your review:

- **The timeouts are in `test-setup.ts`, not `vite.config.ts`,** where the rest of the test settings are, because changing that file restarts a running dev server, which was in use while this was done. Moving them is one line each.
- **The chunks are imported, rather than turning `autoCodeSplitting` off under test,** so the tests keep the same code split as production. The hook has a 60 s limit of its own.
- **The hook's router briefly owns `onSessionEnded`,** until a test builds its own. Every test does, so this is noted and left.

What was not checked:

- CI on Linux; only `npm test` here. Neither the README nor the workflow names the test file, and neither changed.
- 9 and 12 copies were each run once on the final tree. The bar was alone and 3 rounds of 6.
- The lost click in a real browser. It is shown under Vitest only.

Things a later ticket should know:

- **The address changes before the page does.** `waitFor` on `router.state.location` can pass before the next page has rendered. Before acting on the next page, wait for something on it, with `findBy`.
- **A new route needs nothing in the setup:** `routesById` includes it. Do not import pages in a test to speed it up.
- **Do not raise a timeout in a single test.** Find out what it is waiting for first.
- **To see whether a test is reliable,** run it from an export, with a few copies at once, and with `{ repeats: 100 }` in the suspect test. That raised the rate of the lost click from 1 in 9 copies to 9 in 10.

**Review (2026-11-05).** The `code-review` skill's two axes. Standards: no hard violations; the setup comment gave a weak reason for not using `vite.config.ts` and an odd word, both fixed; plain numbers for the timeouts and the throwaway router left as they are. Spec: nothing showed the raised timeouts mattered, so the 9-copy comparison above was run; and the note on ticket 11 suggested fake time, which would stall `findBy` and `user`, so it was corrected. The review came before the lost click was found, so it did not see the two-line test change.

**The lost click after Leave, fixed on 2026-11-05, because you chose to.** This changes application code, so "in the tests alone" above holds only for the first commit. `LeavePageGuard` now blocks only from its own page: `holding && current.routeId === page && next.routeId !== page`, with `page` from `useMatch`. Once Leave has moved the address on, the page that is still mounted catches nothing, whatever its `holding` says. Asking, Stay, the reload warning and releasing the request are as they were.

**The window is longer than the comment above says.** On the Nurses and Users pages it is a few milliseconds, but on the Import page `holding` includes the sheet, so it stays true until the old page unmounts, and on a first visit that should include loading the next page's chunk, which is read from the code and not measured.

**The first two fixes were wrong, and the review found both.**

- **A `left` ref set on Leave** passed all the tests of the time, but it stayed set if a click in the window returned to the same page, which then stayed mounted. The guard was off for good, on Import with a sheet on screen.
- **Comparing paths** kept no state, but `match.pathname` is the route's own path and the blocker's is the address as typed. On `/nurses/import/` or `/NURSES`, which the backend serves and the router keeps as they are, the guard never asked, and a sheet could be lost.

Route ids have neither problem: moving within a page keeps its route id, and any address for a page has the same one.

**Tests:** the two lines the commit above added to "leaves when told to, whatever the answer then says" are out again, so that test follows its link at once and exercises the fix. It is back to what it was at d515cd8. Eight new tests. Seven use `leaveThen`, which clicks Leave and lets only microtasks pass until the address changes, so they land in the window every time and need no repeats.

| Test | Unfixed | `left` ref | Paths | This fix |
|---|---|---|---|---|
| Follows a link straight after Leave: Nurses, Users, Import from the sheet, Import with a confirmation on its way (4) | fail | pass | pass | pass |
| Still guards the page after coming back: Nurses, Users (2) | fail | fail | pass | pass |
| Still guards a sheet that going back keeps on screen: Import (1) | pass | fail | pass | pass |
| Still asks about a sheet on `/nurses/import/`: Import (1) | pass | not run | fail | pass |

The first two rows fail on the unfixed guard because the click is lost. The last two pass there because they only pin what those two wrong fixes broke. In the third, the back in memory history never reaches the guard; it is the click on Home afterwards that has to ask.

| "leaves when told to" 100 times over, in each of 6 copies at once | Clicks | While `pending` | Blocked | Copies failing |
|---|---|---|---|---|
| Unfixed | 606 | 5 | 4 | 4 |
| Comparing paths | 606 | 2 | 0, of 2 that reached the guard | 0 |
| This fix | 606 | 0 | 0 | 0 |

The window is rare at this load, and that last run did not hit it at all, so the deterministic tests are the evidence for this fix, and this table only shows the test no longer fails. The earlier measure at 10 copies, with the unfixed guard, was 23 blocked of 1010 and 9 copies failing. This fix was not run at 10, to spare the machine during manual checks.

From a clean export of this commit: 320 of 320 alone, 320 of 320 in each of 6 copies at once (one round, longest test 3.4 s, with the machine swapping), and the build passes. The 312 earlier test names are all still there. 12 copies was not run, to spare the machine during manual checks.

**In the built-in browser,** on a scratch PostgreSQL 18 with throwaway accounts, `runserver` on its own port and Vite on `127.0.0.1:5183`, all removed afterwards, with the requests held open by wrapping `fetch` in the page. The dev stack was not touched. **On the Users page only**, a script in the page clicked Leave and followed a link as soon as the address changed, because a person cannot be timed into that window.

- **Unfixed, from `/users`:** it ended on Technical settings with no question, and the click on Change password was lost.
- **This fix, from `/users/`:** the guard asked, Stay stayed, it asked again, and Leave followed by the link ended on Change password.
- **Comparing paths, from `/users`, and not repeated on this fix:** following Users instead stayed on the page, and a reset held open there asked again on the way out. The tests cover this on this fix.

**The other direction, by following a link at the same moment, 31 times each on each page:**

| Right after | Nurses, Users | Import |
|---|---|---|
| The answer with the password | Blocked, and the password shows | Blocked, the sheet shows, and it asks |
| A refusal | Blocked with no question, and the click is lost | The same |
| Done, or Close passwords on Import | The link is followed | The link is followed |

- **Blocking after a password's answer protects it.** On Nurses and Users, `PasswordDialog`'s own blocker may not be registered yet, so letting the link through could lose the password.
- **After a refusal it is the same out-of-date `holding` and a lost click, left for your decision.** The guard cannot tell a refusal from a password at that moment, and telling them apart risks the case above. Nothing is lost but the click, for the few milliseconds before the page catches up.
- **Done is a click,** so React applies the change and removes the blocker before anything else can run.

Not checked: a person's hand in the window; the browser on the Nurses and Import pages; going back in a browser rather than memory history. The other-direction table was run on the comparing-paths version, and neither the answer nor Done depends on what changed after it.

**Review (2026-11-05).** The `code-review` skill's two axes, on this change and on the two lines above, which it had not seen. Two rounds, because the second reviewed the replacement for the first. Spec: the flaws of the `left` ref and of comparing paths above, fixed; test setup with no purpose, removed; this ticket's false lines, corrected here. Standards: earlier comments rewritten in place, so they are restored apart from one pointer and the ticked lines, as `docs/agents/issue-tracker.md` appends comments; a helper parameter that promised more than it did, a weak name and no reason given for not using `user`, all fixed. Nothing in ticket 10a or 11 is now false: 10a's Leave still takes the request and asks as it says.

**Accepted by the user on 2026-11-05, and not to be reopened as a bug.** A link followed in the few milliseconds after a refused save is blocked with no question, so the click is lost and clicking again works. The guard cannot tell a refusal from an arriving password at that moment, and letting the link through could lose a password.

**Reviewed by the user (2026-11-06).** From the review of every unsettled item across tickets 01–20, answered as recommended. Kept as built: the three test choices (L44–48).
