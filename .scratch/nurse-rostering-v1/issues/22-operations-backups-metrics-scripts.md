# 22: Operations: backups, metrics and scripts

**What to build:** The worker takes a nightly backup at the configured time and keeps the configured number of days; the System Admin sees the backups on the health page with the last backup time and downloads one. A documented restore script and an admin password reset script run on the server. Every container logs JSON to standard output and the web application exposes a Prometheus metrics endpoint on the internal network only.

**Blocked by:** 11 Run a solve

**Status:** ready-for-agent

- [ ] Backup job with retention; health page lists backups with sizes and dates; download
- [ ] Restore script stops the app, restores, starts it; admin reset script; both documented in the install guide
- [ ] JSON logging for web, worker and solver; metrics endpoint unreachable through Caddy
- [ ] API tests cover the backup list and download authorization; a compose-level test runs backup and restore
