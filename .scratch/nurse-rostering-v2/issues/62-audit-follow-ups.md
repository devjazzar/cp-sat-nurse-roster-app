# 62: Audit follow-ups: no late approval, one solve a unit, no framing, no cross-site downloads

**What to build:** Four small changes the user decided on 2026-11-11, from the security audit of that day
(`docs/security/2026-11-11-security-audit.md`; the leads' full traces are in its `NEEDS-VALIDATION.md`, the late approval
in section 4).

1. **No approval once the month is over.** Submitting already refuses a month that is over
   (`rosters.review.why_not_submit`: "This month is over, so its draft cannot be submitted."). Approving does not
   (`why_not_approve`). So a roster left submitted past its month can be approved later. If the month after it has closed by
   then, every later close of the unit is refused for good, because `closes.making.why_not_close` finds an approved earlier
   month that is not closed, and the hourly close fails for that unit every hour. Reproduced in the audit, not fixed. The
   user's choice (option A): approving refuses a month that is over, the way submitting does; rejecting stays allowed. A month
   with no approved roster is skipped by the close, as section 5 of the architecture already says.
2. **One active solve a unit (audit lead 5).** Today at most one solve is active per unit and month (`solves.api`, line 76;
   `solves.replans.why_not`). One manager can queue a solve for every future month and hold the hospital-wide queue ahead of
   every other unit. The user's choice: at most one solve or re-plan of a unit is queued or running at a time, across all its
   months. A start while one is active is refused, naming the month that is active.
3. **No framing (audit lead 6).** No response carries `X-Frame-Options` or a `frame-ancestors` policy. Add Django's
   `XFrameOptionsMiddleware` with `DENY`, and `Content-Security-Policy: frame-ancestors 'none'` on every response Caddy
   serves (`deploy/Caddyfile`).
4. **No cross-site downloads (audit lead 7).** The file routes are plain GETs a page on another site can make a signed-in
   user's browser take: the staff list (`exportStaffList`, audited), a roster version's file (`exportRosterVersion`,
   audited), the two import templates, and the System Admin's backup download (`ops.api.download_backup`, whose names are
   predictable). Refuse each with 403 when the request says `Sec-Fetch-Site: cross-site`; a request without the header (an
   older browser, a script) is served as today.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] Approving a submitted roster of a month that is over is refused (409), in words like submit's, and nothing changes: the
      roster stays submitted, no version is made, no one is told. Rejecting it still works
- [ ] The approver's page for such a roster says the month is over and offers no Approve (or shows the refusal beside it;
      **Worth your review** which)
- [ ] A test of the audit's scenario: a roster submitted for May, June approved and closed, then approving May is refused and
      July's close is not blocked by May
- [ ] Starting a solve or a re-plan while another of the same unit is queued or running, for any month, is refused (409),
      naming that month; a different unit's solve is not blocked; the month's own refusals stay as they are
- [ ] Every response from `web` carries `X-Frame-Options: DENY`, and every response through Caddy carries
      `Content-Security-Policy: frame-ancestors 'none'` (checked on a scratch stack, and in `deploy/tests/operations.sh` if it
      fits there)
- [ ] The five file routes answer 403 to `Sec-Fetch-Site: cross-site`, and serve `same-origin`, `same-site`, `none` and no
      header as today; the audit entries of the staff list and the roster file are written only for a file served
- [ ] `docs/ARCHITECTURE.md`: section 5's approval paragraph says a month that is over can no longer be approved; section 4's
      Solve says one active solve a unit; section 8's Security says the framing and download rules
- [ ] `docs/security/2026-11-11-security-audit.md`: the late approval and leads 5 to 7 marked fixed, with this ticket's commits
- [ ] Tests at the existing seams: the backend API suite (review, solves, the file routes, the middleware), the frontend's
      app-level suite for the approver's page, the Playwright files touched; the usual full suites and both workflows

## Comments
