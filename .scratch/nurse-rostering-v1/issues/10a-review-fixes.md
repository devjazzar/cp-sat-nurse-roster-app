# 10a: Fixes from the review of tickets 07 to 10

**What to build:** An adversarial review of tickets 07 to 10 found four bugs, each of which could lose a password or act on an answer that was already out of date. Fix them, test-first, and check each claim on the way.

**Blocked by:** 10 Leave

**Status:** ready-for-agent

- [x] A check and an import cannot overlap in either order, and a running import is never reset
- [x] No way out of the page, a form or a dialog silently loses a password on its way, for all five requests that answer with one; reloading gets the browser's question, as far as a browser allows
- [x] The hourly job decides on values read after it holds the locks, and still reads the sessions once
- [x] A password reset checks the unit and resets under the nurse's lock, in one transaction, with the same 403, 404 and refusal as before
- [x] The choice about `set_end_date`'s early return is made and recorded
- [x] Route tests hold a request open while the other action is tried; backend tests race real transactions on PostgreSQL

## Comments

Implemented on 2026-11-05. All four claims were checked on the unfixed code and were right. Backend under pytest on real PostgreSQL 18, frontend under Vitest with the real routes and generated client over a stubbed `fetch`. The OpenAPI document and the generated client did not change. The solver was not touched.

**The backend tests are real races, not a change made at the deciding moment.** `nurses/tests/test_two_at_once.py` holds one transaction open with its change made, starts the other on its own connection, sees it waiting for a lock in `pg_stat_activity`, and only then commits, so the order is forced rather than timed. Before the fixes the job deactivated the nurse, and the manager got a 200 with a password. The file's seven tests passed all 45 repeat runs on the fixed code, the last 20 in their final form, on a scratch PostgreSQL 18. The module's transactions use `django_db(transaction=True)`, as `test_two_at_the_same_moment_make_one` already did, and pytest-django runs those last.

The route tests were first run on the unfixed code. A check answering during an import lost the sheet. Cancel, Give a unit manager a nurse profile, Correct details, Transfer, Set end date and the Users page's Correct name each lost the password. "Add a nurse" and a row's Reset password lost nothing by themselves: the form stays, or a dialog opens. They are held back because a second password answer would replace the first in the one dialog.

Driven in the built-in browser, **not on the dev overlay**: a scratch PostgreSQL 18 container with a throwaway CNO and System Admin, `runserver` on its own port and Vite on `127.0.0.1:5183`, so as not to touch the dev stack's cookies on `localhost`. It is removed. Requests were held open by wrapping `fetch` in the page. As the CNO, a new nurse held open: Cancel and another panel did nothing; Home asked; the answer arriving during the question closed it and showed the password; focus went back to Add a nurse after Done. A reset held open: Cancel and Escape did not close it; a real back within the app asked, Stay restored the address, and the password came. An import: a held check kept Add back and the answer freed it; during the import Check file and Log out were held back, and the sheet came with two passwords. As the System Admin: a new Deputy CNO held open, with Correct name doing nothing and the question and password as above; a held reset at 375 px, where the question fits with no sideways scroll, focus starts on Stay and Escape stays; Leave, after which Log out and the Users page were free and the late answer changed nothing.

What was not checked:

- **The browser's own prompt on a reload.** Dispatching `beforeunload` in the page showed it being refused while a password is on its way, and the route tests' memory history has no such event. The prompt itself never appeared, because going back to an earlier full page load in the built-in browser left without one. That may be the pane's or the browser's rule, as browsers can skip the prompt. Chrome, Safari and Firefox were not tried. **A page can only ask here.**
- **A session ending during a create.** Any request answering 401 clears the client and goes to the login page (`sessionCheck` in `router.tsx`), with nothing asked. The session is over by then, so the answer to a create in flight may well be a 401 too. Left as it is.
- **The two-transaction order the other way round for a reset.** A reset that holds its locks first, with a transfer waiting, is by design and not raced.
- **The dev overlay and the production compose file.** See above. **The dev stack's worker has to be restarted to pick up the job's fix,** as the README says of tasks. Its `web` and Vite reload.
- **Dark mode, and browsers other than the built-in one.**

Decisions this ticket took:

- **`set_end_date`'s early return stays.** Saving what is already saved writes nothing, and it does not bring back an inactive staff nurse with no passed end date. With this fix the job cannot leave anyone in that state, and nothing else deactivates a staff nurse without an end date. Someone left there comes back by setting a later date, which is a change and reactivates them, and then clearing it (`test_a_nurse_left_inactive_with_no_end_date_comes_back_through_a_later_date_and_not_through_saving_nothing`). **Worth your review:** healing on a no-op would be a small change, but a save that changes nothing would then write an audit entry and open an account.
- **Leaving is asked about, not blocked,** as the import does: "Leave without the password?", Stay or Leave. A silent block, as `PasswordDialog` has once the password is on screen, would trap someone behind a request that hangs. Choosing Leave takes the request out of the mutation cache, or the next page would hold still for an answer that can never reach it. The request still runs on the server. **Worth your review:** a nurse saved that way has no known password until someone resets it, and the list may not show them until it is next read.
- **Moving within the page asks nothing:** narrowing the Nurses list unmounts no form.
- **Log out is held back rather than asked about while a password is on its way,** because it ends the session before anything can ask. To get out from behind a hung request, leave the page by a link and choose Leave.
- **A manager taken off the unit at that moment gets no password.** The reset also takes the unit's row lock, which `update_unit`, `archive_unit` and `release_managed_unit` hold while changing the manager, so the check sees the outcome: a 403. A CNO's reset takes it too, for one code path and no other reason. **Worth your review:** the unit stays locked through the hash, about half a second, which keeps nurses from joining that unit for that moment. `reset_password` hashes inside its transaction as it always did, so the nurse's lock is also held through it.
- **Cancel waits for a save on its way on every form of the Nurses page and the Users page's name form,** since it never could stop the save and only lost what the answer said. Those forms return no password, so this is for honesty rather than safety. Other pages' forms keep their Cancel as it is. The other panels are held back only for a password, so a transfer's answer can still be lost by opening another panel: its refusal goes unseen, and the save stands.
- **The import page keeps one `checking` state of its own.** Ticket 08's review removed mutation state mirrored into the page; this one is not a mirror, because it starts before the mutation does, covering validating and reading the file, where an Add would otherwise slip in. That gap was real and has its own test.
- **`LeaveDialog` is now `LeavePageDialog`,** with `LeavePageGuard`, now that they are shared, because Leave is a word for something else in this app (`GLOSSARY.md`).

Things a later ticket should know:

- **A new request that answers with a generated password** goes in `ANSWERED_WITH_A_PASSWORD` in `lib/use-awaiting-password.ts`. Nothing checks this for you. A form that sends one should sit on a page with a `LeavePageGuard` and hold back whatever could unmount it.
- **`deactivate_many(users)` asks its queryset twice,** once to lock and once to decide. Whatever the queryset filters on must be written under the user's lock.
- **Tests that race:** `alongside` in `test_two_at_once.py` is the helper. Within a transaction `pg_stat_activity` answers from its first read unless `pg_stat_clear_snapshot()` runs first.
- **The app's `Button` stays focusable when disabled,** so tests look for `aria-disabled`, and `toBeDisabled` fails on it.

**Review (2026-11-05).** The `code-review` skill's two axes found an abandoned request still holding the next page after Leave, with a question that was no longer true and Log out held back; no test of a check tried during an import; `LeaveGuard` colliding with the glossary's Leave; `Cancel` waiting on the end date form and not the name form; a race test whose order was hoped for rather than seen; test helpers copied from sibling modules; and a word the glossary avoids. All fixed. Left as they are and noted above: the session ending during a create, the list after Leave, and the `checking` state. `better-accessibility` and `better-writing` were held to the new question and held-back buttons; the question's wording was tightened. `better-layout`, `better-typography`, `better-colors` and `better-ui` were not loaded, as this adds no new surface: the question is the existing alert dialog, measured at 375 px.
