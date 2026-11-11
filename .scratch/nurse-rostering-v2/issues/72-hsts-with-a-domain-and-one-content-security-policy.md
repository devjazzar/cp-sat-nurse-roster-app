# 72: HSTS with a domain, and one content security policy

**What to build:** Every response through Caddy carries one `Content-Security-Policy`, replacing any `web` sent and extending ticket 62's `frame-ancestors 'none'` line: `default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'`, widened only where the browser checks prove the built SPA needs it. With `DOMAIN` set, every response carries `Strict-Transport-Security: max-age=31536000`, without `includeSubDomains` or `preload`; a self-signed installation never sends it. Caddy's own error pages (the 502 while a restore runs) carry neither, which is accepted. Spec: `.scratch/nurse-rostering-v2/specs/hardening.md` (Headers).

**Blocked by:** 62 Audit follow-ups (its `frame-ancestors` line); 71 Gunicorn runs threaded workers (the Caddyfile, `operations.sh` and the install guide), after 70

**Status:** ready-for-agent

- [ ] One `Content-Security-Policy` header on a page, a static file and an API answer, set deferred so it replaces any the application sent, never two
- [ ] The Playwright support file listens for content security policy violations on every page and fails the test that sees one; every existing journey, the push journey and the print page among them, passes with none
- [ ] Each widening of the policy, if any, is named in the ticket comment with what needed it
- [ ] HSTS in the Caddyfile snippet the `DOMAIN` mode imports, whose comment changes; no HSTS without `DOMAIN`
- [ ] `deploy/INSTALL.md` says what HSTS means if the hospital later stops using its name, and the first real install's checks include it
- [ ] `docs/ARCHITECTURE.md` section 8's Security names both headers
- [ ] `docs/security/2026-11-11-security-audit.md`: the HSTS and CSP hardening note marked fixed, with this ticket's commits
- [ ] Tests at the agreed seams: the Playwright browser checks; `deploy/tests/operations.sh` (the policy on a page and an API answer, no HSTS without `DOMAIN`, the header in the adapted configuration's `DOMAIN` snippet); both workflows

## Comments

**From ticket 69 (2026-11-11).** `deploy/Caddyfile` now has a global options block first, and the site's `reverse_proxy` has a
body. Ticket 62's `header Content-Security-Policy` line is unchanged, above `@metrics`; the compose-level check of ticket 69
sits right after `operations.sh`'s framing check.

**From ticket 70's review (2026-11-11):** the user chose to add a line here to `deploy/INSTALL.md`'s install checklist: at the first install with a `DOMAIN`, confirm a nurse import (or another request) that takes longer than a minute from a browser, which likely speaks HTTP/3 to Caddy, and see it complete. Ticket 70 drove HTTP/1.1 and HTTP/2 only (99 s and 94 s confirmations, both completed).
