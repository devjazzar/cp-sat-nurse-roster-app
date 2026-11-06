# 23: Phones and PWA

**What to build:** A nurse opens the application on her phone: the roster grid scrolls horizontally, requests and swaps are usable with a thumb, and the app installs to the home screen as a progressive web app.

**Blocked by:** 19 Request windows and requests; 20 Swaps

**Status:** ready-for-agent

- [ ] Responsive layout for every nurse screen and the login at phone width; grid scrolls horizontally with the nurse column fixed
- [ ] Web app manifest and service worker for installability (no offline data, no push)
- [ ] Playwright checks at phone size for the roster, a request and a swap

## Comments

**From ticket 18 (2026-11-06).** Nothing may cache a roster version's files: `GET /api/units/{id}/roster/export` (CSV or Excel, by `format`) answers `Cache-Control: no-store`, as the staff list and the nurse import do (ticket 08's comment), and a service worker must honour it. The print sheets, `GET /api/units/{id}/roster/sheet` and `GET /api/rosters/mine/sheet`, are JSON reads like any roster read: keep them out of any cache too, as they hold a unit's names. The print pages (`/roster/print`, `/my-roster/print`) are laid out for A4 landscape; on a phone the table scrolls sideways inside its own region, and printing from a phone was not checked.

**From ticket 22 (2026-11-06).** Two more things a service worker must never cache or serve from a cache: a backup (`GET /api/ops/backups/{name}`, the whole database, answered `Cache-Control: no-store` as an attachment) and the System Admin's `GET /api/ops/health`, which lists them. `/metrics` is not the SPA's at all: it answers only on the internal network, and Caddy refuses it, so keep it out of any route the worker handles. The health page's Backups table scrolls sideways inside its own region at 320 px, with the Download column at the far edge, as the other tables do.
