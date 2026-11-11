---
status: accepted
date: 2026-11-11
---
# The limit on failed logins per client is the application's, kept in PostgreSQL; Caddy stays the stock image

The security audit of 2026-11-11 found that nothing limits requests per client: each anonymous login costs a full password
hash on one of the web workers, and the only budget, the lockout, is per username, so a client that changes the name each time
is never held back (leads 1 and 2). The usual place for such a limit is the proxy, but the stock `caddy:2.11` image has no
rate-limit handler: that is a third-party module (`caddy-ratelimit`) needing a custom build, and ADR 0001 keeps Caddy and
PostgreSQL on their stock images. The user decided on 2026-11-11 that the limit is the application's. The login reads the
failures recorded for the client's address before it touches the username's row or runs the hash, from a table in the one
database, since the three web processes share nothing else (no Redis, ADR 0006). The address is the one Caddy reports, as the
audit log already reads it.

## Considered options

- **Caddy with `caddy-ratelimit`, in an image of ours.** Refuses before gunicorn is reached at all, but every release ships
  and pins a second image, and the module's upkeep (not an official Caddy repository) becomes ours. If load that never
  reaches the login has to be limited one day, this is the way.
- **Both.** Two limits to tune and explain, for one route.

## Consequences

- Caddy stays stock and does what its stock handlers can: a body size cap, body buffering and server timeouts.
- A client still reaches gunicorn and the database to be refused; what it no longer gets past the limit is the hash.
- The limit is tested in the backend suite like the lockout beside it.
- A throttled request is refused before its password is looked at, so it is not a failed login: the audit log records the
  throttle once, when an address reaches it, and not each request refused during it (the user's decision of 2026-11-11,
  changing section 8's "every failed login"). Otherwise the log would grow without bound again, cheaper than before.
- Everyone behind one address shares its budget. A proxy in front of Caddy would make the whole hospital one address, so the
  installation names its proxies (`TRUSTED_PROXIES`) and Caddy, trusting only those, works out the client the application
  reads.
