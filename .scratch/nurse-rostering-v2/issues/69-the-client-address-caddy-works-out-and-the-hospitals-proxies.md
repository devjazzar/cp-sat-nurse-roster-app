# 69: The client address Caddy works out, and the hospital's proxies

**What to build:** A hospital that puts a proxy or load balancer in front of the server names its addresses in `.env` (`TRUSTED_PROXIES`, empty by default), so every client behind it keeps its own address in the throttle and the audit log. Caddy trusts only those, reads the client from `X-Forwarded-For` strictly, right to left, and passes the address it worked out to the application in a header of its own that it always sets, replacing any a client sent. `audit.log.client_ip` reads that header, with the peer as the fallback in development; the throttle uses the same function. With the value empty, Caddy trusts no one, as today. Spec: `.scratch/nurse-rostering-v2/specs/hardening.md` (The client address and the proxies); ADR 0015.

**Blocked by:** 62 Audit follow-ups (both edit the Caddyfile); 63 The throttle on failed logins from one address (this changes the address its tests send)

**Status:** ready-for-agent

- [ ] `.env.example` lists `TRUSTED_PROXIES`, empty, with what it is for; compose passes it to Caddy alone
- [ ] The Caddyfile's global options trust those proxies with strict parsing; an empty value starts Caddy without error and trusts no one (the directives' syntax confirmed by `caddy adapt` on the running image, not only from the docs)
- [ ] Caddy always sets its own client-address header to `web`; `client_ip` reads it, and a client-sent `X-Forwarded-For` or a client-sent copy of that header changes nothing
- [ ] `/metrics` is still refused through Caddy and answered inside
- [ ] `deploy/INSTALL.md` says when to set `TRUSTED_PROXIES`, and that without it, behind a proxy, every client shares the proxy's address and its throttle
- [ ] `docs/ARCHITECTURE.md` section 2's configuration list names `TRUSTED_PROXIES`
- [ ] Tests at the agreed seams: the backend API suite (the address the throttle and the audit log see); `deploy/tests/operations.sh` (a client-sent `X-Forwarded-For` does not reach the audit log); both workflows

## Comments

**From ticket 63 (2026-11-11).** The throttle reads the address only through `audit.log.client_ip`, inside
`_address_key` in `backend/accounts/login.py` (which then takes an IPv6 address's /64 and an IPv4-mapped one as IPv4), so
changing `client_ip` changes both. `accounts/tests/test_throttle.py` sends the address as `REMOTE_ADDR` alone, through its
`login()` helper; if the peer stops being the fallback in tests, that one helper is what changes.

**From the user's review of ticket 63 (2026-11-11):** behind Docker Desktop the app sees every client as the bridge
gateway, so on the dev stack fifty failed logins from anyone throttle everyone. Say in this ticket's comment what a Linux
server and Docker Desktop each pass through as the client address once this ticket lands.
