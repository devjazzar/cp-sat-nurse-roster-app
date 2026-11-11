# 69: The client address Caddy works out, and the hospital's proxies

**What to build:** A hospital that puts a proxy or load balancer in front of the server names its addresses in `.env` (`TRUSTED_PROXIES`, empty by default), so every client behind it keeps its own address in the throttle and the audit log. Caddy trusts only those, reads the client from `X-Forwarded-For` strictly, right to left, and passes the address it worked out to the application in a header of its own that it always sets, replacing any a client sent. `audit.log.client_ip` reads that header, with the peer as the fallback in development; the throttle uses the same function. With the value empty, Caddy trusts no one, as today. Spec: `.scratch/nurse-rostering-v2/specs/hardening.md` (The client address and the proxies); ADR 0015.

**Blocked by:** 62 Audit follow-ups (both edit the Caddyfile); 63 The throttle on failed logins from one address (this changes the address its tests send)

**Status:** ready-for-agent

- [x] `.env.example` lists `TRUSTED_PROXIES`, empty, with what it is for; compose passes it to Caddy alone
- [x] The Caddyfile's global options trust those proxies with strict parsing; an empty value starts Caddy without error and trusts no one (the directives' syntax confirmed by `caddy adapt` on the running image, not only from the docs)
- [x] Caddy always sets its own client-address header to `web`; `client_ip` reads it, and a client-sent `X-Forwarded-For` or a client-sent copy of that header changes nothing
- [x] `/metrics` is still refused through Caddy and answered inside
- [x] `deploy/INSTALL.md` says when to set `TRUSTED_PROXIES`, and that without it, behind a proxy, every client shares the proxy's address and its throttle
- [x] `docs/ARCHITECTURE.md` section 2's configuration list names `TRUSTED_PROXIES`
- [x] Tests at the agreed seams: the backend API suite (the address the throttle and the audit log see); `deploy/tests/operations.sh` (a client-sent `X-Forwarded-For` does not reach the audit log); both workflows

## Comments

**From ticket 63 (2026-11-11).** The throttle reads the address only through `audit.log.client_ip`, inside
`_address_key` in `backend/accounts/login.py` (which then takes an IPv6 address's /64 and an IPv4-mapped one as IPv4), so
changing `client_ip` changes both. `accounts/tests/test_throttle.py` sends the address as `REMOTE_ADDR` alone, through its
`login()` helper; if the peer stops being the fallback in tests, that one helper is what changes.

**From the user's review of ticket 63 (2026-11-11):** behind Docker Desktop the app sees every client as the bridge
gateway, so on the dev stack fifty failed logins from anyone throttle everyone. Say in this ticket's comment what a Linux
server and Docker Desktop each pass through as the client address once this ticket lands.

**Implemented on 2026-11-11,** on branch `claude/ticket-69-client-address-457fa5` (`4bb0cc3`, `31d3b19`, then this comment),
from `main` at `e2ae502`. Draft pull request
[devjazzar/cp-sat-nurse-roster-app#11](https://github.com/devjazzar/cp-sat-nurse-roster-app/pull/11).

The suites ran locally under the heavy-run lock:
- the backend on `31d3b19`, on a throwaway PostgreSQL 18 container of my own: 3168 passed;
- the solver's `service_tests/test_logs.py` (its access-line test changed): 5 passed;
- `makemigrations --check`: "No changes detected". No migration, no API change, so no OpenAPI or client to regenerate;
- `deploy/tests/operations.sh nr-t69`: all checks passed, the new one included;
- no frontend or Playwright file changed;
- GitHub's two workflows were green on `31d3b19` and `b4732aa`: backend, frontend, image, solver and browser checks
  (`operations.sh` among them);
- `main` then gained ticket 64 (`accounts/login.py`, `test_login.py`). It merged without conflict (`d81bfcd`), and the
  `accounts` and `audit` suites with the two log-test files ran again on it: 1009 passed.

**What the dev stack needs:** `docker compose up -d --build`. That is enough: `compose.yaml` gives `caddy` a new variable, so
`up -d` recreates `caddy`, which then reads the new Caddyfile. Checked for the dev stack's own change: `docker compose config
--hash caddy` differs between `e2ae502`'s `compose.yaml` and this one with the variable empty both times, and on the scratch
stack a change of the value recreated the container. `docker compose restart caddy` after it is harmless and makes sure: a
new `web` behind a Caddy still on the old Caddyfile would get no `X-Client-IP` from Caddy and believe one a client sent. The user's `deploy/.env` needs nothing: with no `TRUSTED_PROXIES` line, compose passes it
empty, as today. The `web` rebuild is for `audit/log.py` and the access line.

**What was built, criterion by criterion.**
- **`.env.example` and compose.** `TRUSTED_PROXIES=` is listed under the optional values. It says what it is for, that it is
  space separated, and to name the proxies only. `compose.yaml` passes `TRUSTED_PROXIES: ${TRUSTED_PROXIES:-}` to `caddy`
  alone; on the scratch stack `web` had no such variable.
- **The Caddyfile's global options.** It is the first block, above the snippets:
  `servers { trusted_proxies static {$TRUSTED_PROXIES}; trusted_proxies_strict; client_ip_headers X-Forwarded-For }`.
  - It was confirmed with `caddy adapt` and `caddy validate` on `caddy:2.11` (v2.11.9). That covered `DOMAIN` set and unset,
    with `TRUSTED_PROXIES` empty and with `10.0.0.5 10.0.0.0/29`.
  - An empty value adapts to `{"source": "static"}` with no ranges, and the stack starts with it (`operations.sh`). Two
    space-separated values become two ranges. `private_ranges` also works (see Decisions for why the guide warns against it).
  - A comma-separated value stops Caddy from starting ("invalid IP address"). The install guide says so.
- **Caddy's own header.** `reverse_proxy web:8000 { header_up X-Client-IP {client_ip} }` sets the header, replacing any a
  client sent (adapted: `headers.request.set`).
  - `audit.log.client_ip` reads `X-Client-IP`, then the peer, and no longer reads `X-Forwarded-For` at all: behind a
    trusted proxy, Caddy passes on the chain a client began. The throttle's `_address_key` calls it, unchanged.
  - Backend tests (`test_login.py` `TestAudit`): the header wins over the peer; a client-sent `X-Forwarded-For` changes
    nothing, with Caddy's header or without it; a nonsense header falls back to the peer.
  - Backend tests (`test_throttle.py` `TestTheAddress`): two clients behind one Caddy peer have a throttle each; a changing
    `X-Forwarded-For` does not move a client out of its throttle.
  - `operations.sh`: a login that sends `X-Forwarded-For`, `X-Client-IP` and `X_Client_IP` records the same address as a
    login that sends none, and that address is not empty. `X_Client_IP` maps to the same WSGI key; gunicorn 26.2 drops it,
    since its `header_map` default is `drop`.
- **`/metrics`.** It is still refused through Caddy (404 for `/metrics` and `/metrics/`) and answered inside, as
  `operations.sh` checks. Caddy's `reverse_proxy` still adds `X-Forwarded-For`, which `ops/metrics.py` refuses. It was also
  404 through the front proxy of the drive below.
- **`deploy/INSTALL.md`** has a new "Behind the hospital's proxy" under Install. It says when to set the variable, with
  examples, and that without it, behind a proxy, every client shares the proxy's address and throttle, and the audit log
  shows the proxy. It says to name the proxies only, never a client range or `private_ranges`; that the proxy must say
  `https`; what Linux (as documented) and Docker Desktop pass through; and what a bad value does. The install checklist
  gains a login from another computer, its address read in the audit log.
- **`docs/ARCHITECTURE.md`.** Section 2's configuration list names `TRUSTED_PROXIES`. Section 8's throttle paragraph says
  how Caddy works out the address and that `client_ip` reads Caddy's header and never `X-Forwarded-For`.
- **Tests at the seams:** the backend API suite and `operations.sh`, as above. Both workflows were green.

**What a Linux server and Docker Desktop pass through, once this lands.**
- **Docker Desktop (the dev stack).** Every connection reaches Caddy from Docker's gateway of the `public` network. The
  scratch stack recorded `172.24.0.1` for every login, and ticket 63 saw `172.27.0.1`. So on the dev stack everyone still
  shares one address and one throttle. `TRUSTED_PROXIES` cannot help: no proxy sends an `X-Forwarded-For`, and trusting the
  gateway would let every client name its own address.
- **A Linux server, a client on another machine.** Docker's published ports go through iptables NAT, which keeps the
  client's source address, so Caddy sees each client as itself. That is Docker's documented behaviour. **I have not seen it**:
  no Linux server with a remote client was driven.
- **A Linux server, a client on the server itself** (`curl https://localhost`). It arrives from the gateway through Docker's
  userland proxy: GitHub's Ubuntu runner recorded `172.19.0.1` in `operations.sh`'s new check.
- **Behind a hospital proxy, on either.** Without `TRUSTED_PROXIES` every client is the proxy; with it, each client is the
  address the proxy saw (driven below).

**What was driven, and how.** I used my own scratch stack, `operations.sh nr-t69 --keep` on port 18691, on 11 November 2026,
on Docker Desktop. A second `caddy:2.11` played the hospital's proxy on the stack's `public` network (`172.24.0.3`), in front
of the stack's Caddy (`172.24.0.2`). The proxy was published on 127.0.0.1:18692, and curl was the client (seen as
`172.24.0.1`). The address read was the `remote` of `web`'s access line for each request, which now reads the same header
as the audit log.
- **`TRUSTED_PROXIES` empty:**
  - straight to Caddy with `X-Forwarded-For: 1.2.3.4`: `172.24.0.1`, the peer;
  - through the proxy: `172.24.0.3`, so every client is the proxy. This is the case the install guide warns of.
- **`TRUSTED_PROXIES=172.24.0.3`,** written to the env file, then `docker compose up -d`, which recreated `caddy`:
  - through the proxy, the client sending `X-Forwarded-For: 1.2.3.4`: `172.24.0.1`, the address the proxy saw;
  - through a proxy that itself trusts everyone, so it passes on `1.2.3.4, 172.24.0.1`: `172.24.0.1`. Caddy read from the
    right and stopped at the first untrusted hop, so the client's `1.2.3.4` was not taken;
  - the same, with `X-Client-IP: 5.6.7.8` too: `172.24.0.1`;
  - straight to Caddy with `X-Forwarded-For: 1.2.3.4`, from a peer that is not trusted: `172.24.0.1`;
  - `/metrics` through the proxy: 404.

The stack, its volumes, image and env file, and the proxy container are gone. My PostgreSQL container `t69-pg` is removed.

**What was found, and fixed.**
- `operations.sh`'s first version checked only that the address was none of those a client claimed, while its pass line
  said "Caddy's peer". It now compares against a login that claims nothing (`31d3b19`, from the review).

**Findings for you, not fixed.**
- **On the dev stack the throttle is still everyone's.** Docker Desktop gives every client the gateway address, as above. A
  stack run on Docker Desktop for real users would let fifty failed logins by anyone refuse everyone's logins for fifteen
  minutes. This ticket cannot change that; a Linux server with a remote client is what the throttle is for.
- **"budget" for the throttle predates this ticket.** `test_throttle.py`'s `TestIPv6` ("share a budget") and section 8 ("shares
  its budget") use the word the glossary keeps for a push job's 30 seconds. I renamed only my own tests.

**What was NOT checked.**
- A remote client on a Linux server: whether Caddy sees its own address, as Docker documents (above).
- IPv6 through Caddy or through a proxy: the scratch stack is IPv4 only. The backend suite covers the /64 rule on whatever
  address the header carries.
- A real hospital proxy or load balancer, and one that sends `X-Real-IP` or `Forwarded` (RFC 7239) instead of
  `X-Forwarded-For`: Caddy reads `X-Forwarded-For` alone here.
- The audit log's address through the front proxy: the drive read `web`'s access line, which reads the same header
  `client_ip` does. The audit log's address through Caddy alone is `operations.sh`'s check.
- `operations.sh`'s new check seen red: by reading, without `header_up` the login that claims `X-Client-IP: 203.0.113.8`
  records that address and the check fails, but I did not run it so.
- A login through a trusted proxy: the drive sent `GET /api/health`. Beside it, three throwaway `caddy:2.11` containers showed
  that a trusted proxy's `X-Forwarded-Proto` is passed on as it is (`https` from the proxy reached the upstream, where an
  untrusted peer's became `http`). Django reads it (`SECURE_PROXY_SSL_HEADER`), so a proxy that said `http` would make every
  login a CSRF refusal. The install guide says the proxy must say `https`; that refusal itself was not driven.
- The six parallel frontend runs and the browser suite: GitHub's, green.

**Decisions taken here.**
- **`client_ip_headers X-Forwarded-For` is written out,** although it is Caddy's default, so that `X-Real-IP` is never
  read: a proxy that sends one is believed only for `X-Forwarded-For`. The spec names `X-Forwarded-For` alone.
- **`client_ip` no longer reads `X-Forwarded-For` at all,** not even as a second choice. With a trusted proxy, its value is a
  chain a client began, and with Caddy always setting its own header there is nothing for it to add.
- **The access line's `remote` reads `X-Client-IP` too** (`solver_service/logs.py`), else the peer. The ticket does not ask for
  it. But behind a trusted proxy, the old `X-Forwarded-For` would have logged a partly client-written chain, and the access
  line would have disagreed with the audit log. The solver's own lines, with no Caddy in front, keep the peer.
- **The install guide warns against `private_ranges` and the Docker gateway,** since anyone at a trusted address can claim
  any address.

**Worth your review.**
- **A trusted proxy is believed on the scheme too,** not only the address (`X-Forwarded-Proto`, above). The install guide asks
  for a proxy that reaches the server over HTTPS and says `https`. The alternative, Caddy always setting its own
  `X-Forwarded-Proto` (`header_up X-Forwarded-Proto https`), would make the proxy's word irrelevant; I left Caddy's
  behaviour as it is, since the spec does not ask.
- **The header's name, `X-Client-IP`.** The spec says only "a header of its own". I chose a name nothing else in the stack
  sets or reads (Django, gunicorn and Caddy's own client-address list ignore it). The other usual name, `X-Real-IP`, is one
  Caddy would read from a trusted proxy by default.
- **The access line's `remote` now follows Caddy's header** (Decisions above): keep it, or keep the access line on the raw
  `X-Forwarded-For`.
- **Only `X-Forwarded-For` from a trusted proxy:** a hospital whose load balancer sends only `Forwarded` or `X-Real-IP` would
  need a change to the Caddyfile. Nothing tells us what hospitals use.

**Review.** `code-review` against `e2ae502`, both axes in fresh sub-agents.
- Standards: one hard point, "budget" in my test names (glossary), renamed to "throttle". Judgement calls, all fixed in
  `31d3b19`:
  - the audit tests' expected value repeated the code's fallback, so they are now two tests with literal addresses;
  - the throttle tests' second login helper became a `headers=` parameter on `login()` and `fail()`;
  - `caddys` is renamed `client_address`;
  - a long line in section 8 was rewrapped.

  Not changed: the access-line tests sit below the agreed seams, but they are existing tests updated, not new ones.
- Spec: no defect found. The missing ticket comment is this one. The loose `operations.sh` check is fixed (above). The
  access line is a justified side change, recorded in Decisions.

**Things later tickets should know.**
- **70:** the Caddyfile now has a global options block with a `servers` block. `read_body_idle` and the minimum body rate go
  in that same `servers` block. `reverse_proxy web:8000` now has a body, `{ header_up X-Client-IP {client_ip} }`, so
  `request_buffers` goes beside `header_up`. `operations.sh`'s ticket 69 check is right after the framing check.
- **71:** gunicorn's access line reads `X-Client-IP` for `remote` (`solver_service/logs.py`). The threaded workers change
  nothing here; `client_ip` keeps no state.
- **72:** the site block still has ticket 62's `header Content-Security-Policy` line above `@metrics`. Any server-wide option goes in the global options
  block's `servers` block.
- **All three:** `TRUSTED_PROXIES` changes the env of `caddy`, so `up -d` recreates it. A Caddyfile-only change still needs
  `docker compose restart caddy` (ticket 62's finding).
