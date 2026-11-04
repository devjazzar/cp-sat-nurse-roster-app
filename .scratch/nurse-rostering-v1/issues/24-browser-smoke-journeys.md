# 24: Browser smoke journeys

**What to build:** The compose stack is exercised in CI the way the hospital will use it: the System Admin logs in and creates the CNO; the CNO sets up a unit and nurses; the unit manager generates and submits a roster; the Deputy CNO approves it; a nurse sees it, makes a request and proposes a swap a colleague and the manager accept; on desktop and phone sizes.

**Blocked by:** 21 Month close; 22 Operations; 23 Phones and PWA

**Status:** ready-for-agent

- [ ] Playwright journeys per role against the compose stack with the real solver on a small unit
- [ ] CI job builds the image, starts the stack, runs the journeys, and fails the build on any failure
- [ ] Journeys run at desktop and phone sizes
