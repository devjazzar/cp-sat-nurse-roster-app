# 42: The System Admin and the hospital's IT see pushes working

**What to build:** The System Admin's health page says how many pushes were sent and how many failed in the last 24 hours and, in fixed words, why the last one failed (unreachable, refused, gone), and the metrics endpoint carries the same two numbers for the hospital's monitoring. Attempts older than seven days are removed by the daily retention. The install guide names the push services' hosts the server must let the worker reach, and says that a hospital that blocks them loses pushes and nothing else. The architecture says pushes are in, who sends them and through which network, what a device opts into and what housekeeping removes.

Spec: `.scratch/nurse-rostering-v2/specs/web-push-for-deadlines.md`.

**Blocked by:** 41 A push reaches the device and a tap opens the page

**Status:** ready-for-agent

- [ ] The health answer and page gain a push block: sent and failed in the last 24 hours (attempts, never jobs), and the last failure's reason as `unreachable`, `refused`, `gone` or none; the OpenAPI document and the client regenerated
- [ ] `/metrics` gains the two counts as gauges worked out at scrape, as its others are
- [ ] The daily retention removes attempts older than seven days, under a lock of its own name like the others; the health page's counts are unaffected
- [ ] `deploy/INSTALL.md`: a section on pushes naming `*.push.apple.com`, `fcm.googleapis.com`, `*.push.services.mozilla.com` and `*.notify.windows.com` over HTTPS from the worker; what a blocked firewall loses; the health line as the check; an item on the install checklist
- [ ] `docs/ARCHITECTURE.md`: sections 1 and 12 no longer list push as out of scope or to revisit; section 2's table gives the worker `egress`; section 7 adds the push job and the attempts' retention; section 8 says what is pushed, how a device opts in, what Log out and deactivation do and what the health page shows; section 9's housekeeping lists attempts after seven days
- [ ] `deploy/tests/operations.sh`: the worker is on a network that is not internal and `web`, the database and the solver are on none; the health answer carries the push block; `prepare` logged the key pair
- [ ] Tests at the agreed seams: the backend suite (the health block's counts and last reason from scripted attempts, the two metrics, the retention's what goes and what stays); the operations check above
