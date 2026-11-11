# 70: Caddy holds the body

**What to build:** No web worker waits on a client's body. Caddy refuses a request body over 2 MB with 413, reads the whole body before it opens the request to `web`, and drops a body that stalls for a minute or arrives slower than 10 kB/s on average. There is no whole-request read deadline, so a long confirmation or download is never cut off once its body is in. A 1 MB nurse import still goes through. The image stays `caddy:2.11`. Spec: `.scratch/nurse-rostering-v2/specs/hardening.md` (Caddy and gunicorn, Q17's correction in the Caddyfile bullet); ADR 0001, ADR 0015.

**Blocked by:** 69 The client address Caddy works out, and the hospital's proxies (the same global options block)

**Status:** ready-for-agent

- [ ] The site has a request body cap of 2 MB and `reverse_proxy` request buffers of 2 MB
- [ ] The server's stalled-body timeout stays at its 1-minute default and gains a minimum rate of 10 kB/s; no `read_body` (a deadline on the whole request) is set, and the Caddyfile's comment says why
- [ ] The other timeouts stay at Caddy's defaults: no write timeout; the minimum rate's syntax confirmed by `caddy adapt` on the running image
- [ ] A 1 MB import file previews and confirms through Caddy
- [ ] `docs/ARCHITECTURE.md` section 2 says what Caddy limits
- [ ] `docs/security/2026-11-11-security-audit.md`: lead 3 marked fixed at Caddy, with this ticket's commits
- [ ] Tests at the agreed seams: `deploy/tests/operations.sh` checks the running Caddy is 2.11.8 or later, a body over 2 MB is 413, with the test stack's `web` overridden to one worker of one thread for this check (with three, one held request would never show), a login whose body is withheld does not stop `/api/health` answering through Caddy (one connection), and the adapted configuration has the minimum rate and no `read_timeout`; both workflows

## Comments

**From ticket 69 (2026-11-11).** `deploy/Caddyfile` now opens with a global options block, `{ servers { trusted_proxies
static {$TRUSTED_PROXIES}; trusted_proxies_strict; client_ip_headers X-Forwarded-For } }`: `read_body_idle` and the minimum
body rate go in that same `servers` block. `reverse_proxy web:8000` now has a body (`header_up X-Client-IP {client_ip}`), so
`request_buffers` goes beside it. Confirm with `caddy adapt` and `caddy validate` on `caddy:2.11` with `TRUSTED_PROXIES` empty.
