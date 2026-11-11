# Hardening against one client's load

Status: ready-for-agent
Type: enhancement
Published: 2026-11-11 by /to-spec

Spec drawn from the grilling of 2026-11-11 (two rounds, 16 questions, every recommendation taken), which acted on the security
audit of that day: `docs/security/2026-11-11-security-audit.md`, its leads 1 to 4, the hardening notes of its `REPORT.md`
section 5 and the restore note of its section 4 (full traces in `NEEDS-VALIDATION.md`). Vocabulary: `GLOSSARY.md`
(**Lockout**, **Throttle**, **Push subscription**, **Push**, **Backup**, **Restore**). Decisions and their reasons:
`docs/ARCHITECTURE.md`, `docs/adr/0015-the-login-limit-per-client-is-the-applications-and-caddy-stays-stock.md` and the ADRs
it rests on (0001, 0006, 0009, 0012). Where this spec and those documents disagree, the documents win and this spec is wrong.

Ticket 62 (`.scratch/nurse-rostering-v2/issues/62-audit-follow-ups.md`) is built beside this and is not part of it: one active
solve a unit, `X-Frame-Options` and `frame-ancestors 'none'`, the file routes refusing `Sec-Fetch-Site: cross-site`, and no
approval once a month is over. This feature's content security policy extends ticket 62's header line, so the ticket that
writes it is blocked by 62.

## Problem Statement

**Nothing limits what one client may ask of the installation.** The audit found it at four places.

- **Anyone may try a password as often as they like, and each try costs half a second of a web worker.** The login is open to
  anyone. Every try at a name that is not locked runs a full password hash (0.5 s measured) on one of three web workers that
  each serve one request at a time, and every signed-in user waits on the same three. The only budget is the lockout, which is
  per username, so a client that sends a different name each time is never held back. A few tries a second keep every worker
  hashing.
- **Every refused login leaves rows that stay for good.** Each refusal writes an audit entry, and each name tried, known or
  not, a login-attempts row that only that name's next successful login removes. While a name is locked, refusals write their
  entry without even a hash, as fast as the workers take them. A name that is no account never logs in, so its row never goes;
  every row is copied into every backup kept, on the one disk the database and the backups share. A password typed into the
  username box is kept in the audit log, where the System Admin reads it.
- **A slow client can hold a web worker for five minutes.** Caddy passes a request on before its body has arrived, and a
  worker waits for that body with nothing to stop it but gunicorn's 300-second timeout, raised that high for the nurse import.
  Three such requests and nobody is served, the health check included. Nothing caps a body's size in front of the application.
- **One user's devices hold everyone's pushes.** A signed-in user may turn pushes on for any number of made-up addresses
  under the push services' domains. The one push job at a time sends to each in turn, waiting up to 10 seconds to connect and
  10 to read, while every other user's push of a thing with a deadline waits behind it.

Beside these, the responses carry no `Strict-Transport-Security` and no content security policy beyond ticket 62's frame rule.
The public health answer calls the solver on every request. And a restore brings back the login attempts of the backup's
moment, while the deactivations, password resets and key rotations done since are silently undone, with nothing telling the
person restoring.

## Solution

**The installation limits what one client can make it do, at the place each cost is paid, with the stock images it has.**

- **A throttle on failed logins from one address, decided before the hash.** Fifty failed logins from one client address in
  fifteen minutes throttle that address for the rest of the window: every login from it is refused at once, before its name's
  row is touched or any password is looked at, with the time it may try again. A wrong password, a refusal while the name is
  locked, and a wrong current password on Change password each count one; a success counts nothing and clears nothing. IPv6
  addresses count by their /64. The audit log records the throttle once, when the address reaches it, and nothing for each
  request refused during it. The lockout per username is unchanged.
- **Login attempts that are no one's record go.** A name's count is forgotten a day after its last failure, unless the name is
  locked; an address's once its window is over. A daily retention job removes both. Audit entries stay. A failed login names
  the typed username only when an account has it.
- **Caddy holds a client's body, and gunicorn no longer serves one request a worker.** Caddy refuses a body over 2 MB, reads
  the whole body before it opens the request to the application, and gives a body 60 seconds to arrive. Gunicorn runs three
  workers of four threads each, so one slow request, or a hash, holds a quarter of one worker and not a third of the pool.
- **The installation knows its own proxies.** A hospital that puts a proxy in front of Caddy names it in `.env`, so each client
  behind it keeps its own address in the throttle and the audit log.
- **At most ten push subscriptions a user, and a push job that hands on what it has not sent after 30 seconds.** An eleventh
  device ends the user's earliest; a push job that has sent for 30 seconds sends nothing more and leaves the rest to a new job,
  behind any push already waiting.
- **`Strict-Transport-Security` with a domain, and one content security policy** on every response through Caddy.
- **The public health answer is kept five seconds.**
- **A restore empties the login attempts and says what it undid.** Before it drops the replaced database, `deploy/restore.sh`
  prints each deactivation, password reset, password change and push key rotation recorded after the backup, so whoever
  restores can do them again.

## User Stories

1. As a Staff Nurse, I want to sign in at shift change in my normal time, so that a stranger trying passwords elsewhere on the internet does not keep me waiting.
2. As a Unit Manager, I want my pages to answer while someone is guessing passwords, so that I can work my unit's roster as usual.
3. As a System Admin, I want an address that keeps failing to log in to be refused before any password is checked, so that it cannot keep the web workers busy hashing.
4. As a System Admin, I want an address refused for the rest of a fifteen-minute window after fifty failed logins, so that one client gets at most one password hash every eighteen seconds.
5. As a Staff Nurse who mistyped her password, I want the throttle to need far more failures than a ward's typos at shift change, so that I and my colleagues behind the hospital's Wi-Fi are not refused for a few mistakes.
6. As a Staff Nurse behind a throttled address, I want the login page to say that too many failed logins came from this network and when I may try again, so that I know it is not my password and how long to wait.
7. As a Staff Nurse, I want a throttled login to be refused whatever username and password I type, so that the answer does not tell anyone whether a name or a password was right.
8. As a System Admin, I want a refusal while a name is locked to count toward its address's throttle, so that a locked name cannot be used to write audit entries without limit.
9. As a System Admin, I want a wrong current password on Change password to count toward the address's throttle, so that a stolen session cannot guess its owner's password without limit.
10. As a System Admin, I want Change password refused while its address is throttled, so that the throttle bounds every password check an address can cause.
11. As a System Admin, I want a successful login neither to count toward the throttle nor to clear it, so that an attacker cannot reset their budget by signing in to an account of their own.
12. As a System Admin, I want IPv6 clients counted by their /64, so that a client given a whole range of addresses has one budget, not billions.
13. As a System Admin, I want one audit entry when an address is throttled, with that address, so that I can see an attack in the log.
14. As a System Admin, I want no audit entry for each request refused while an address is throttled, so that the log cannot be filled by a client that is already refused.
15. As a System Admin, I want every login the server did check, failed or not, still recorded in the audit log, so that the log stays the account of who signed in and who tried.
16. As a System Admin, I want a failed login to name the typed username only when an account has it, so that a password typed into the username box is never kept where I can read it.
17. As a System Admin, I want a failed login at a name that is no account still recorded, with its address, so that guessing at made-up names still shows.
18. As a Staff Nurse, I want the lockout of my username to work as before, five failed logins and fifteen minutes, so that someone guessing at my account is still stopped.
19. As a System Admin, I want a name's count of failed logins forgotten a day after its last failure, unless the name is locked, so that names that are no account do not stay in the database for good.
20. As a System Admin, I want an address's count removed once its window is over, so that the throttle keeps nothing it no longer needs.
21. As a System Admin, I want these removals done by a daily retention job beside the others, a day missed caught up by the next, so that they need nothing from me.
22. As a System Admin, I want the audit entries of failed logins kept, so that housekeeping never removes a record of what happened.
23. As hospital IT, I want Caddy to refuse a request body over 2 MB with 413, so that no client can send the application more than its largest import needs.
24. As a CNO, I want a nurse import of up to 1 MB still accepted, so that the body cap never refuses a file the import allows.
25. As hospital IT, I want Caddy to read a request's whole body before it passes the request on, so that no web worker waits on a client's slow body.
26. As hospital IT, I want a body that takes more than 60 seconds to arrive refused by Caddy, so that a client trickling bytes cannot hold even Caddy's side for long.
27. As a CNO on slow ward Wi-Fi, I want a 1 MB import to arrive well inside that minute, so that the limit never refuses a real upload.
28. As a System Admin, I want each web worker to serve several requests at once, so that one hash, one import or one slow request holds a quarter of one worker and not a third of the pool.
29. As a CNO, I want a 500-row nurse import confirmed however long it takes on this server, so that it is never killed halfway at 300 seconds.
30. As hospital IT, I want the install guide's note on the import to say to time it, without a limit to stay under, so that I check the server and do not shrink imports for nothing.
31. As hospital IT with a proxy or load balancer in front of the server, I want to name its addresses in `.env`, so that every client behind it keeps its own address in the throttle and the audit log.
32. As hospital IT without a proxy, I want to leave that setting empty and have Caddy trust no one, so that a client can never name its own address.
33. As a System Admin, I want the address in the audit log and the throttle to be the client Caddy worked out, so that a header a client sends cannot change it.
34. As a Staff Nurse, I want to turn pushes on for my phone, my tablet and my computer as before, so that a limit on devices never gets in my way.
35. As a System Admin, I want one user to hold at most ten push subscriptions, so that one account cannot make the push job send to hundreds of made-up addresses.
36. As a Staff Nurse, I want turning pushes on for an eleventh device to end my earliest one, not refuse the new one, so that the device I hold now is the one that works.
37. As a Staff Nurse, I want a browser renewing my device's subscription not to count as a new device, so that a renewal never ends another of my devices.
38. As a Staff Nurse taking over a shared device, I want it to count among my ten, so that an address moving between users cannot get round the limit.
39. As a System Admin, I want the subscription an eleventh device ends to have no audit entry of its own, since the new device's turning on says enough, so that the log reads as it does for any drop.
40. As a Staff Nurse, I want my push for a swap to answer to arrive within about half a minute of anyone else's job, so that a user with many devices, or a push service that is slow, does not make my deadline pass.
41. As a System Admin, I want a push job to start no new send after 30 seconds and hand the sends it has not made to a new push job, so that no job holds the others back by more than about 30 seconds and one send.
42. As a Staff Nurse, I want the sends a job handed on still made, by the next job, so that the budget delays a push and never drops it.
43. As a System Admin, I want a send the budget handed on to be a first try, not a try again, so that it is not counted as a failure and keeps its tries.
44. As a System Admin, I want the job that takes the handed-on sends to wait behind any push already waiting, so that pushes take turns.
45. As a Staff Nurse, I want a push whose key the browser gave in a form that cannot be stored refused with a clear answer, not an error page, so that turning pushes on fails cleanly.
46. As a System Admin, I want a send that fails in any way the library did not foresee counted as a refusal, so that the push job never stops on one device's error.
47. As a hospital with a domain, I want every response to carry `Strict-Transport-Security` for a year, so that a browser that has been here never asks for the site over plain HTTP.
48. As a hospital without a domain, on Caddy's self-signed certificate, I want no `Strict-Transport-Security`, so that a later certificate warning can still be clicked through.
49. As hospital IT, I want the install guide to say what that header means if the hospital later stops using its name, so that I am not surprised by browsers refusing it.
50. As any user, I want every page served with a content security policy that lets only the app's own scripts, styles, images and connections run, so that injected markup could not load anything from elsewhere.
51. As any user, I want the app to work exactly as before under that policy, so that the policy refuses nothing the app itself does.
52. As a System Admin, I want one content security policy, set by Caddy for every response, so that two layers never send two policies that both apply.
53. As hospital IT, I want the public health answer kept for five seconds, so that anyone polling it cannot make the application call the solver on every request.
54. As hospital IT, I want the health page of the System Admin unaffected by that, so that its answers stay current.
55. As hospital IT restoring a backup, I want the login attempts emptied in the restored database, so that a lockout of the backup's moment does not come back.
56. As hospital IT restoring a backup, I want the throttle's addresses emptied too, so that an address throttled then is not refused now.
57. As hospital IT restoring a backup taken before this feature, I want the restore to work although its database has no throttle table yet, so that every backup kept can still be restored.
58. As hospital IT restoring a backup, I want a list, before the replaced database is dropped, of each deactivation, password reset, password change and push key rotation recorded after the backup, with its account and time, so that I can do them again.
59. As hospital IT, I want that list to say nothing else of anyone, so that what the terminal shows holds no more than it needs.
60. As hospital IT, I want the restore to say when there is nothing to list, so that an empty list is clearly an answer.
61. As hospital IT, I want the restore only to list these, not do them again by itself, so that I decide what a restore should bring back.
62. As hospital IT, I want the install guide's restore section to say what the restore empties and prints, so that I know before I run it.

## Implementation Decisions

### The throttle

- **A new model in `accounts`, beside `LoginAttempts`: the failed logins of one client address in its current window.** Keyed
  by the address's key: an IPv4 address as itself, an IPv6 address as its /64 network. It holds when its window started and
  how many failures it has counted. A request with no address (development without Caddy) is never throttled.
- **One small interface, used by the login and Change password:** whether an address is throttled now and until when, and
  record one failure for it. A failure in a window older than fifteen minutes starts a new window at that failure, counting
  one. The failure that brings the count to fifty writes the one audit entry `auth.login_throttled`: no actor, no target, the
  request's address as its IP, and the window's end. The constants (fifty, fifteen minutes) live in code, beside
  `MAX_FAILURES` and `LOCK_DURATION`, not in the technical settings.
- **The check comes first.** `attempt_login` asks whether the address is throttled before it takes the name's row lock: a
  throttled login touches no `LoginAttempts` row, calls neither `authenticate` nor the hasher, and writes nothing. Otherwise
  the login goes on as today, and each refusal it makes, wrong credentials or locked, also records one failure for the
  address. The address's row is not held across the hash: a burst of parallel tries may pass the fifty by at most the number of
  requests the web pool serves at once, which is bounded.
- **The API.** `POST /api/auth/login` gains a 429 answer: a detail saying too many failed logins came from this network, and
  the time it may try again; with a `Retry-After` header. `POST /api/auth/change-password` refuses with the same 429 while the
  address is throttled, before the current password is checked, and a wrong current password records one failure for the
  address. The OpenAPI schema and the generated client change with them.
- **The login page** shows the 429's words and its time in the hospital's clock, as it shows a lockout's. Change password
  shows the same.
- **The failed login's target.** `auth.login_failed` names the typed username as its target only when an account has that
  username; otherwise the target is empty. Its address and its reason stay. The `AuditEntry` docstring and architecture
  section 8 say so. The `LoginAttempts` key is still the name typed, so an unknown name still locks like a real one.
- **Section 8's rule changes**, by the user's decision (ADR 0015): every login the server checked, failed or not, is in the
  log, and so is each throttle; a request refused by a throttle is not.

### Housekeeping

- `LoginAttempts` gains the time of its last failure, set at every failure it counts. Rows written before have none.
- A daily retention job, at a fixed UTC time after the others and under its own lock (ADR 0009), removes every
  `LoginAttempts` row that is not locked now and whose last failure is more than 24 hours old or unknown, and every address row
  whose window ended. A day missed is caught up by the next, like the other retention jobs.
- Architecture sections 7 (the retention list) and 9 (what housekeeping removes, "no one's record") name both.

### The client address and the proxies

- `.env` gains `TRUSTED_PROXIES`, empty by default, listed in `.env.example` and passed to Caddy alone. Caddy's global options
  trust those addresses and read the client from `X-Forwarded-For` strictly, right to left, so only a trusted proxy's word is
  taken. With the value empty, Caddy trusts no one, as today.
- Caddy passes the client address it worked out to the application in a header of its own that it always sets, replacing any
  a client sent. `audit.log.client_ip` reads it, with the peer address as the fallback in development; the throttle uses the
  same function. The `/metrics` refusal of anything Caddy passed on keeps working.
- The install guide says when to set `TRUSTED_PROXIES`, and that without it, behind a proxy, every client shares the proxy's
  address and its throttle.

### Caddy and gunicorn

- **Caddyfile.** A global options block with the server's `read_body` timeout at 60 seconds and the trusted proxies; the other
  timeouts stay at Caddy's defaults (headers 1 minute, idle 5 minutes, a stalled body 1 minute since 2.11.5, no write timeout,
  since a backup download may be large). In the site: a request body cap of 2 MB (413, refused from `Content-Length` before
  reading since Caddy 2.11.8), and `reverse_proxy` with request buffers of 2 MB, so Caddy holds the whole body before it opens
  the request to `web`. The image stays `caddy:2.11` (ADR 0001); the compose-level test checks the running Caddy is 2.11.8 or
  later.
- **The 2 MB cap sits above the import's 1 MB file limit** (`nurses.importing.MAX_BYTES`) and its multipart overhead, and below
  Django's own default upload limits.
- **Gunicorn** runs `--worker-class gthread --threads 4 --workers 3`, with `--timeout` at gunicorn's default: under `gthread` it
  is only how long a worker's main loop may go silent, and no request is killed for its length. The comment above the command,
  which sized 300 s for the import, is rewritten. Web's database connections go from at most 3 to at most 12, beside the
  worker's 9, against PostgreSQL's 100; ADR 0009's count in the architecture is updated. The application holds no mutable
  module-level state; the nurse import's own pool of password hashes runs inside one request thread as before (the hash
  releases Python's lock, so threads hash on several cores).
- **The install guide** drops the import's 300-second limit: the 500-row import is still timed at the first real install, with
  no limit to stay under.

### Push subscriptions and the push job

- **The cap.** `notifications.subscriptions.turn_on`, under the user's row lock it already takes, ends the user's earliest
  subscriptions by the time they were turned on until the user holds ten, after a new address is stored or an address moves to
  this user. A renewal (`replaces`) adds none and ends none. No entry is written for a subscription ended this way.
- **The budget.** `notifications.pushes.deliver` is given the job's start and a budget of 30 seconds. Before each send it reads
  the time; once the budget is spent it makes no more sends and returns, beside the sends to try again, the sends it did not
  make. The push job defers those as a new push job at the normal priority, with the same try number, so they are first tries
  if they were first tries, queued behind any push job already waiting; a try again stays at priority −1 as today. The clock is
  one the tests can move.
- **The `auth` key's length.** The API accepts a key no longer than the model's column, so a longer one is refused with 422
  instead of failing on the database.
- **`pushing.send` never raises**, as its docstring says: any exception the library raises that is not already sorted is a
  refusal.
- Architecture section 7 (`push`) and the glossary's **Push subscription** gain the cap and the budget; ADR 0012's list of how
  a subscription ends gains the eleventh device (a consequence line, not a change of the decision).

### Headers

- **Content security policy.** Caddy sets one `Content-Security-Policy` on every response it passes on, replacing any the
  application sent, extending ticket 62's `frame-ancestors 'none'` line. It starts from `default-src 'self'; script-src 'self';
  style-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'`, and is
  widened only where the browser checks show the built SPA needs it, each widening named and explained in the ticket's
  comment. Caddy's own error pages (the 502 while a restore runs) carry no policy, which is acceptable.
- **HSTS.** `Strict-Transport-Security: max-age=31536000`, without `includeSubDomains` or `preload`, set in the Caddyfile
  snippet the `DOMAIN` mode imports, so a self-signed installation never sends it. The Caddyfile's comment on that snippet
  changes, and the install guide says what the header means if the hospital stops using its name, and adds HSTS to the first
  real install's checks.

### The public health answer

- `GET /api/health` keeps its answer for five seconds in each web process; the compose health check reads it as before. The
  System Admin's health page is not cached.

### Restore

- After the restored database is renamed in and before the replaced one is dropped, `deploy/restore.sh`:
  1. empties the login attempts and the throttle's addresses in the restored database; a table the restored backup does not
     have yet (a backup from before this feature) is skipped, and `web` creates it empty when it migrates;
  2. prints, from the replaced database, every `user.deactivated`, `user.password_reset`, `auth.password_changed` and
     `push.keys_rotated` entry whose id is above the restored database's newest audit entry (ids are sequential, so this is
     "after the backup", whatever the file's name): its action, its target account and its time on the hospital's clock, and
     nothing else, then one line saying to do them again; or one line saying none were recorded.
- It does not re-apply any of them. The hourly job deactivates again any staff nurse whose end date has passed anyway.
- If printing fails, the restore still completes: the list is advice, and the backup of the database as it stood before is
  kept and holds the same entries.
- The install guide's restore section and the glossary's **Restore** say what a restore empties and prints.

### The audit document

- `docs/security/2026-11-11-security-audit.md`: leads 1 to 4, the restore note and the notes taken here marked fixed, with
  the commits.

## Testing Decisions

A good test here drives the installation from outside, as a client does, and asserts what a client or an operator sees: a
status, a header, a row the System Admin reads, a line the script prints. None reaches into the throttle's table or a module's
internals to assert how it is done. Four seams, all of them existing.

- **The backend API suite** (Django's test client over the API, as `accounts/tests/test_login.py`, `test_users.py` and
  `notifications/tests/test_pushes.py` do now, with the scripted push service and the moved clock they already use):
  - the throttle: fifty failures from one address throttle it, the fifty-first login is 429 with its time and `Retry-After`,
    with no hash (the hasher-call counting the audit's harness did) and no `LoginAttempts` row touched; a different address is
    not affected; the window's end lifts it; a success neither counts nor clears; locked refusals and wrong current passwords
    count; Change password is refused while throttled; two IPv6 addresses in one /64 share a budget, two /64s do not; one
    `auth.login_throttled` entry and no entry for refusals during the throttle;
  - a failed login at an unknown name has an empty target and its address; at a real name, the name;
  - the lockout's existing tests pass unchanged;
  - the retention job removes an unlocked count a day old and keeps a locked one and a fresh one, removes an ended window and
    keeps the current one (prior art: the retention jobs' tests of ticket 22 and 42);
  - the client address is the header Caddy sets, and a client-sent `X-Forwarded-For` does not change it;
  - an eleventh device ends the earliest turned on, a renewal ends none, an address moving from another user counts;
  - a push job past its budget makes no more sends and the next job makes them as first tries, behind a push already waiting,
    with nothing dropped; try-again behaviour is unchanged;
  - a 101-character `auth` key is 422; a library exception of an unforeseen kind is a refusal and the job goes on;
  - the public health answer calls the solver once within five seconds and again after.
- **`deploy/tests/operations.sh`, the compose-level test on its own stack:** the running Caddy's version is 2.11.8 or later;
  a page and an API answer carry the one content security policy; no `Strict-Transport-Security` without `DOMAIN` (and, in
  the adapted configuration, the header in the `DOMAIN` snippet); a body over 2 MB is 413; a login whose body is withheld does
  not stop `/api/health` answering through Caddy (the audit's one-connection check, kept to one connection); a client-sent
  `X-Forwarded-For` does not reach the audit log; gunicorn runs threaded; the restore check, which already restores and finds
  later writes gone, also finds the login attempts emptied and the list printed for a deactivation, a reset, a change and a
  key rotation written after the backup. This stack has no proxy, so `TRUSTED_PROXIES` beyond empty is the backend suite's
  and the install guide's.
- **The frontend's app-level Vitest suite** (`frontend/src/app.test.tsx`, its mocked API): the login page shows the throttle's
  words and time on a 429, and Change password does too.
- **The Playwright browser checks:** the shared support file listens for content security policy violations on every page and
  fails the test that sees one; every existing journey, the push journey and the print page among them, passes with none. No
  new journey.
- The usual full suites and both GitHub workflows, on the pull request, before the merge.

## Out of Scope

- A limit on any route but the login and Change password, or a limit in total across addresses; a custom Caddy image with a
  rate-limit module (ADR 0015 says when to revisit).
- A change to the lockout per username: five failures, fifteen minutes, unknown names alike, and the known lever of keeping a
  named account locked, already accepted.
- The throttle's numbers as a technical setting.
- With `DOMAIN` empty, Caddy issuing a certificate for any name a client sends: the install guide already says to set `DOMAIN`
  on a server reachable from the internet.
- `/metrics`' second gate, sessions' absolute lifetime, push subscriptions left by a password reset,
  `INITIAL_ADMIN_PASSWORD`'s policy, generated passwords' expiry, the request-time end date, row locks taken before the scope
  check and a `lock_timeout` for web, a CNO's cancel of a solve, `Solve.error`'s text and the re-validation of a solver result:
  hardening notes the user left out.
- **Later, each its own feature:** a non-superuser database role with the audit table append-only in the database; container
  and supply-chain hardening (`cap_drop`, `no-new-privileges`, `read_only`, digest pins for images and actions, `npx playwright`
  in the lockfile, `.dockerignore`'s `.env` rule, the test settings in the image).
- Everything ticket 62 does.

## Further Notes

- The facts this spec rests on were read from primary sources on 2026-11-11: Caddy v2.11.9's source (body streaming unless
  request buffers are set, no default `read_body` deadline, the 1-minute stalled-body default from 2.11.5, the 413 from
  `Content-Length` from 2.11.8, a client-sent `X-Forwarded-For` replaced unless the peer is trusted, an empty trusted-proxy
  list accepted, a deferred `header` replacing the upstream's field), gunicorn 26.2.0's `gthread` (a connection is handed to a
  thread once a byte arrives; the main loop's heartbeat keeps a long request from being killed) and CPython 3.14's
  `pbkdf2_hmac` (it releases the interpreter's lock).
- The throttle bounds one address. A client with many addresses is bounded only by the pool, now twelve threads; that is what
  ADR 0015 accepted.
- The owner's read-only checks in `NEEDS-VALIDATION.md` (the size of the audit table, the largest number of subscriptions one
  account holds, the hash time on the real server) are still worth making on the installation; they no longer decide whether
  these are findings.
