# Frontend stack research (2026-11-04)

Scope: facts for choosing the React + TypeScript + Vite stack of the nurse-rostering SPA (shadcn/ui + Tailwind already chosen; the brief asked to explore TanStack Form, Query, Table, Store, Charts and Pacer). Pure web research against primary sources; no local code was read.

How to read the numbers:

- "latest" = npm `dist-tags.latest` on 2026-11-04 (registry.npmjs.org). Release dates come from GitHub Releases (`published_at`) or the npm `time` field, as cited.
- "weekly downloads" = api.npmjs.org `last-week` for 2026-10-28..2026-11-03.
- "open issues" = GitHub API `open_issues_count`, which counts issues **and** pull requests.
- "commit activity" = a sample: either the GitHub commits API since 2026-08-04 (only the first ~15-22 commits were readable) or the first page (35 commits) of the repo's commits view. Bot accounts excluded. Treat author counts as indicative, not exact.

---

## 1. shadcn/ui

**CLI and registry**

- npm `shadcn` latest **4.23.0**; GitHub release `shadcn@4.23.0` published **2026-10-27**. Release cadence is high: 35 `shadcn@` releases are visible between 2026-07-17 (4.13.1) and 2026-10-27 (4.21.2 → 4.23.0 in October alone). Weekly downloads: 17,253,807.
- Repo `shadcn-ui/ui`: 127,358 stars, **1,766 open issues+PRs**, last push 2026-11-04. Of the 16 most recent commits (2026-10-30..11-04), 11 are dependabot, 3 are `shadcn`, 2 are community one-offs. Effectively one core maintainer.
- Changelog milestones (ui.shadcn.com/docs/changelog): Feb 2025 Tailwind v4; Aug 2025 CLI 3.0 + MCP server; Dec 2025 `npx shadcn create`; Jan 2026 Base UI documentation; Feb 2026 unified `radix-ui` package; **Mar 2026 shadcn/cli v4**; Apr 2026 presets / `shadcn apply`; May 2026 `shadcn eject`; Jun/Aug 2026 GitHub (private) registries; **Jul 2026 "Base UI as the Default"** and "React Aria"; Sep 2026 `cn` migration; Oct 2026 Trace / Code Block / AI Elements.

**Tailwind CSS version**

- Targets **Tailwind v4 + React 19** (docs page "Tailwind v4": "How to use shadcn/ui with Tailwind v4 and React 19"). Non-breaking: "Your existing apps with Tailwind v3 and React 18 will still work"; only new projects start on v4/React 19. Dark-mode palette revision 2025-03-12; `tw-animate-css` replaced `tailwindcss-animate` 2025-03-19.
- Tailwind itself: `tailwindcss` latest **4.3.4** (released 2026-11-02).

**Radix UI vs Base UI vs React Aria**

- You choose. CLI: `shadcn init -b|--base <base|radix|aria>`; `shadcn docs -b` picks the docs base. Component docs live under `/docs/components/base/...` (Radix and Aria variants exist). The Jan 2026 entry states components "look and behave the same way. Only the underlying implementation changes."
- Date the default changed: changelog entry **"July 2026 - Base UI as the Default"**: "Starting today, Base UI is the default component library in shadcn/ui." "Radix is not being deprecated." Existing projects: "You do not need to migrate." Keep Radix on new projects with `shadcn init -b radix` (add it to non-interactive CI scripts). Stated reasons: Base UI stable at 1.6.0 with >6M weekly downloads; shadcn/create users pick Base UI over Radix ~2:1. The page gives month only; third-party posts date it 3 July 2026 (unverified).
- Base UI today: npm **`@base-ui/react` 1.9.0** (GitHub release v1.9.0 **2026-10-09**; stable v1.0.0 2025-12-11; monthly minors 1.5→1.9 May–Oct 2026). Weekly downloads 27,113,868. Repo `mui/base-ui`: 11,301 stars, 452 open issues+PRs, pushed 2026-11-04. The older package name `@base-ui-components/react` is frozen at `1.0.0-rc.0` (798,109 weekly downloads) - use the new name.
- Radix today: umbrella package **`radix-ui` 1.8.1** (published 2026-10-12; `next` 1.8.2-rc). Weekly downloads 25,993,119. Repo `radix-ui/primitives` (maintained by WorkOS): 19.5k stars, 134 open issues, 132 open PRs; it does not use GitHub Releases.

**How upgrades of copied components work**

- There is no automatic upgrade. Components are copied into your repo; the CLI offers `add --diff [path]` (diff local component vs registry), `add --dry-run`, `add --overwrite`, `init --reinstall` (re-installs existing UI components), and `migrate` subcommands (`cn`, `icons`, `base-color`, `rtl`, `radix`). The CLI v4 entry recommends letting a coding agent "check for updates from @shadcn and merge with my local changes." Re-adding a component overwrites your local copy (Tailwind v4 docs page).

**Charts and Data Table docs**

- Charts: "We use Recharts under the hood." The `chart` component "now uses Recharts v3" (`shadcn add chart`); v3 migration notes include `var(--chart-1)` instead of `hsl(var(--chart-1))` and giving `ChartContainer` an explicit height.
- Data Table: "This guide uses TanStack Table v9" (`pnpm add @tanstack/react-table`); the v8 `flexRender` helper "still works too."
- Forms: `/docs/forms` documents React Hook Form, TanStack Form and Formisch (React `useActionState` "Coming Soon"), all built on the `Field` component family.

**Risks**

- Very fast-moving: three interchangeable base libraries, 35+ CLI releases in 3.5 months, 1,766 open issues+PRs, one core maintainer. Most third-party examples online still assume Radix. Base UI itself is < 1 year past 1.0. Copied code means you own every upgrade.

**Recommendation.** Start on shadcn CLI 4.x + Tailwind 4.3 + **Base UI** (the current default, `init -b base` pinned explicitly in scripts). Treat `components/ui` as owned code and run `add --diff` at planned intervals rather than ad hoc. Use shadcn's `chart` (Recharts 3) and `data-table` (TanStack Table 9) docs as the starting points.

---

## 2. TanStack libraries

**TanStack Query** - `@tanstack/react-query` **5.106.0**, released 2026-11-04 (monorepo release `release-2026-11-04`). Peer `react ^18 || ^19`. Weekly downloads 80,741,444. Repo `TanStack/query`: 50,525 stars, 113 open issues+PRs, pushed 2026-11-04; 40+ package releases on 2026-11-02..04 alone. Sampled commits (2026-11-02..04): sukvvon 11, TkDodo 5, tannerlinsley 1. No v6 tag for the React package (`previous` = 4.44.0); Vue/Svelte adapters are on 6.x. Mature and the obvious server-state choice.

**TanStack Table** - `@tanstack/react-table` **9.3.1**, released 2026-10-12. **v9.0.0 shipped 2026-08-04** (blog by Kevin Van Cott): tree-shakable plugin architecture (`tableFeatures()` opt-in), state "backed by TanStack Store" (alien-signals), React 18+ incl. React Compiler, 10 adapters, new cell selection / cell spanning, full package 14 kB → 25 kB but unused features drop out. Per-framework migration guides exist; the post does not state a v8 support policy. Weekly downloads 34,465,097. Repo: 28,546 stars, 80 open issues+PRs, pushed 2026-11-02, 42 releases in October 2026; KevinVandy authored 9 of 21 sampled commits (2026-10-01..21). shadcn's Data Table doc is already on v9.

**TanStack Virtual** - `@tanstack/react-virtual` **3.14.26**, released 2026-11-03 ("Headless UI for virtualizing scrollable elements in React"; peer React 16.8–19). Weekly downloads 40,563,529. Repo: 7,187 stars, 84 open issues+PRs, pushed 2026-11-03, 43 releases since 2026-10-16; 12 distinct authors in 22 sampled commits (2026-10-15..11-03). For a 60 × 31 grid (1,860 cells) virtualization is optional; Virtual is there if row/column windowing becomes necessary (grid-virtualization specifics not re-verified in this pass).

**TanStack Form** - `@tanstack/react-form` **1.33.5**, released **2026-08-11** (depends on `@tanstack/form-core` 1.33.5, `@tanstack/react-store` ^0.11). **v1 is stable**: announced 2025-03-03 ("the first stable version of TanStack Form is live and ready for usage in production!"). Validation: Standard Schema is native ("we support Standard Schema out of the box; no other packages needed") - Zod, Valibot, ArkType, Effect Schema passed straight into `validators`; field- and form-level validators; async validation with `asyncDebounceMs` / `onChangeAsyncDebounceMs`; schema validation "will not provide you with transformed values". **v2 is in alpha**: announced 2026-08-06 (core rewrite: validator pipeline with triggers and `when`, `strictSchema`/`looseSchema`, shared SSR options); `2.0.0-alpha.3` on 2026-10-23; no release date given. Note: no 1.x release since 2026-08-11 while v2 alphas ship. Weekly downloads 6,257,176. Repo: 6,762 stars, 230 open issues+PRs, pushed 2026-11-03; 35 commits 2026-07-09..11-02 by ~18 human authors. shadcn has a TanStack Form guide (Field + Zod v3).

**TanStack Store** - `@tanstack/react-store` **0.11.2** (2026-09-29; wraps `@tanstack/store` 0.11.2 + `use-sync-external-store`). `1.0.0-alpha.0` published 2026-10-10; tanstack.com/libraries labels it **alpha**. Docs: "TanStack Store is primarily used for state management internally for most framework agnostic TanStack libraries. It can also be used as a standalone library." Weekly downloads 33,469,342 (pulled in transitively by Form, Table v9, Pacer, Router). Repo: 911 stars, 38 open issues+PRs, pushed 2026-11-03; 35 commits 2026-05-21..10-12 by 10 humans. Verdict: an internal primitive, not an app-state product.

**TanStack Pacer** - `@tanstack/react-pacer` **0.24.1** (2026-10-05; core `@tanstack/pacer` 0.23.1). "Utilities for debouncing, throttling, rate-limiting, queuing, and more": debouncer, throttler, rate limiter, queuer, batcher, each with sync and async variants, cancellation and renderable pending state; `pacer-lite` for library authors; adapters for React, Preact, Solid, Angular, Vue, Svelte, Lit, Alpine, Ember, Octane. Docs: **"TanStack Pacer is currently in beta and its API is still subject to change."** Repo created 2025-03-04; 793 stars, 37 open issues+PRs, pushed 2026-11-01; 35 commits 2026-08-06..10-25 by 10 humans (KevinVandy dominant, sukvvon). Weekly downloads 895,642. TanStack DB's 1.0 RC depends on `@tanstack/pacer-lite`. Production-ready: usable, but beta by its own statement - expect API churn.

**TanStack Router** - `@tanstack/react-router` **1.170.46** (2026-10-22; peer React ≥18). Docs: "supports both file-based and code-based routing at the same time" (route tree generated by the Vite plugin or CLI); search params "Automatically parsed and serialized as JSON" and "Validated and typed"; loaders with a built-in cache "loosely based on TanStack Query"; "Designed for client-side data caches (TanStack Query, SWR, etc.)". A v2 RC exists only for the Solid adapter (`solid-router 2.0.0-rc.10`, 2026-10-31). Weekly downloads 22,634,824. Repo: 15,281 stars, **811 open issues+PRs**, pushed 2026-11-04, 35 releases 2026-10-22..31; Sheraff authored 12 of 15 sampled commits (2026-11-03..04). Versus React Router: `react-router` **8.5.1** (2026-10-27; v8.0.0 2026-06-17, yearly majors, peer React ≥19.2.7), 7.18.5 still released 2026-10-27; 74,080,116 weekly downloads. TanStack Router is mature on the 1.x line and is the better fit when you want typed search params for grid/unit/date state in the URL.

**TanStack DB** - `@tanstack/react-db` **1.0.0-rc.1.3** (2026-11-03). "A reactive client store for building super fast apps on sync"; it "extends TanStack Query with collections, live queries and optimistic mutations"; collections: QueryCollection (REST via TanStack Query), Electric, TrailBase, RxDB, PowerSync, IndexedDB, LocalStorage, LocalOnly. 1.0 RC1 announced 2026-10-29 (Kyle Mathews): "After eighteen months of development, beta testing, and user feedback, the API is powerful, production-ready, and stable." tanstack.com/libraries still badges it **beta**. Repo created 2025-03-11; 3,976 stars, 148 open issues+PRs, pushed 2026-11-04; KyleAMathews authored nearly all of 35 commits 2026-10-28..11-04. Weekly downloads 1,429,812. Not needed for this app (no sync engine; Query alone covers the API).

**TanStack Charts - yes, one now exists.** `@tanstack/charts` **1.3.0** (GitHub release v1.3.0 2026-11-04; **v1.0.0 2026-10-03**; "TanStack Charts 1.0" blog 2026-10-05 by Tanner Linsley). "A small, framework-agnostic chart grammar for TypeScript and JavaScript" built around marks (lines, points, bars), scales and axes; "renders accessible SVG by default, with Canvas available as an opt-in surface"; React adapter at `@tanstack/charts/react` (React 18/19), companion package `@tanstack/react-charts` 1.3.0 depends on `@tanstack/charts` 1.3.0. Site: "Charts 1.0 has a stable API"; basic React line chart ≈32.1 kB gzipped. Repo `TanStack/charts`: 862 stars, 36 open issues, 498 commits. Weekly downloads: `@tanstack/charts` 1,141,368; `@tanstack/react-charts` 101,771. It is one month past 1.0 and mainly one author. The old **`react-charts`** package (unscoped) is dead: latest tag 2.0.0-beta.7 published 2020-05-29, last publish 3.0.0-beta.57 on 2023-11-02, repo `TanStack/react-charts` **archived 2026-05-13** ("This project is no longer actively maintained"), 66,353 weekly downloads.

**Recommendation.** Adopt Query 5, Table 9 and (if the grid ever needs windowing) Virtual 3 - all stable with strong signals. Form v1 is production-stable but a v2 rewrite is in alpha; see §4. Pacer is beta: fine for a thin debounce of validation calls, but keep its usage behind one small hook so it can be swapped. Store is an internal primitive (alpha) - do not build app state on it. Router 1.x is a reasonable choice over React Router 8 for typed URL state; either works. Skip DB. Skip TanStack Charts for now (1.0 is four weeks old); revisit in 2027.

---

## 3. Charts alternatives

- **Recharts** - **3.10.1** (2026-07-25); 3.11 canaries weekly (canary.9 2026-11-03); 5 stable releases since 2026-05-04; peer React 16.8–19. Repo: 27,685 stars, 460 open issues+PRs, pushed 2026-11-04; 10 distinct authors in 22 sampled commits (2026-10-30..11-04). Weekly downloads 62,538,705. This is what shadcn `chart` wraps.
- **visx** - `@visx/visx` **4.0.0** (2026-06-11; requires React 18/19). Repo: 21,097 stars, 160 open issues+PRs, last commit 2026-06-22, effectively one maintainer (hshoff); it added "a shadcn-compatible chart registry" (2026-06-17). Weekly downloads 134,990 (umbrella). Low-level D3-style primitives; more code per chart.
- **Apache ECharts via echarts-for-react** - `echarts` **6.1.0** (2026-05-19); `echarts-for-react` **3.0.6** (2026-01-21; peer `echarts ^3–^6`). Repo `hustcc/echarts-for-react`: 5,011 stars, 52 open, last commit 2026-01-21, single maintainer. Weekly downloads 2,218,696. Canvas, large and powerful; overkill for three bar/line charts.
- **Nivo** - `@nivo/core` **0.99.0** (2025-05-23; no release in 17 months). Repo: 14,129 stars, 72 open, last commit 2026-07-21, mostly plouc. Weekly downloads 2,031,197.
- **Chart.js via react-chartjs-2** - `chart.js` **4.6.1** (2026-10-22); `react-chartjs-2` **5.3.1** (2025-10-27; peer `chart.js ^4.1.1`). Repo `reactchartjs/react-chartjs-2`: 6,937 stars, 111 open, one maintainer (dangreen), last commit 2026-05-26 (docs). Weekly downloads 5,727,001. Canvas; fine but no shadcn integration.

**Recommendation.** **Recharts 3 through shadcn's `chart` component.** It is the only option that is both actively maintained (multi-author, weekly canaries) and first-party-integrated with shadcn theming; the charts here are simple bars/lines.

---

## 4. Forms: TanStack Form vs React Hook Form

- **React Hook Form** - **7.91.0** (2026-10-23); `8.0.0-beta.5` (2026-10-23; betas 1–5 since mid-2026); 21 releases since 2026-05-04; peer React 16.8–19. Repo: 44,901 stars, **9 open issues+PRs**, pushed 2026-11-04; 35 commits 2026-10-21..11-03 by 11 humans (bluebill1049 primary). Weekly downloads 60,305,948. shadcn guide (`/docs/forms/react-hook-form`): `Field*` components + RHF `Controller` + `zodResolver` from `@hookform/resolvers/zod`; "This example uses `zod v3`"; other Standard Schema resolvers can be substituted.
- **TanStack Form** - 1.33.5 (2026-08-11), v1 stable since 2025-03-03, v2 alpha since 2026-08-06; 230 open issues+PRs; 6,257,176 weekly downloads (≈1/10 of RHF). Native Standard Schema (Zod directly in `validators`), built-in async debounce. shadcn guide (`/docs/forms/tanstack-form`): `Field*` components + Zod v3 via the validators API.
- shadcn/ui's docs integrate with **both** (plus Formisch) as of today; neither is marked as preferred.

**Recommendation.** **React Hook Form 7 + Zod + shadcn `Field`** for the settings/account/request forms. Reasons: an order of magnitude more usage, a near-empty issue tracker, a stable 7.x line (v8 is beta, not forced), and first-class shadcn docs. TanStack Form is a legitimate alternative if you want one ecosystem and its built-in async-debounced validation, but its 1.x line has not shipped since August while v2 (breaking) is in alpha.

---

## 5. App state

- **TanStack Store** - 0.11.2 / 1.0.0-alpha.0; "primarily used ... internally"; alpha badge. Not meant as the app-state layer.
- **Zustand** - **5.0.16** (2026-10-22); 4 releases since 2026-05-04; peer React ≥18. Repo: 58,896 stars, **5 open issues+PRs**, pushed 2026-11-03; dai-shi authors most commits (12 humans in 35 commits 2026-05-13..10-22). Weekly downloads 89,687,623.
- **Plain React context** - built in (React 19.3.1); zero dependencies; re-renders every consumer on any change unless you split contexts.

**Recommendation.** Server state in TanStack Query. For the little client state (current unit, grid selection, pending edits) use **Zustand** - a single small store with selectors avoids context re-render fan-out across ~1,860 editable cells, and it is the most stable library in this whole list. Context alone is acceptable only if pending-edit state ends up living in Query's cache instead. Do not use TanStack Store directly.

---

## 6. OpenAPI client generation (Django Ninja schema → TanStack Query)

- **@hey-api/openapi-ts** - **0.99.0**, released **2026-06-22** (4 breaking changes); no release since (`next` nightly dated 2026-09-30). MIT; Node ≥22.18; peer TypeScript ≥5.5.3 / 6 / 7. Docs say the package is "in initial development" (pin exact versions). Plugin **`@tanstack/react-query`** ("TanStack Query v5 support") generates `queryOptions`, `infiniteQueryOptions`, `mutationOptions` and `queryKeys` from the SDK. Repo moved to `hey-api/hey-api` (monorepo): 5.6k stars, 545–660 open issues+PRs, pushed 2026-10-31, last commit on `main` 2026-09-30; mrlubos authored 30 of the last 35 commits. Weekly downloads 6,886,537. Signal: polished output but a single maintainer and a 4.5-month release gap.
- **orval** - **8.46.0** (2026-10-30); 22 releases since 2026-08-21; MIT. Repo `orval-labs/orval`: 6,587 stars, **28 open issues+PRs**, pushed 2026-11-04; 35 commits 2026-10-25..11-04 by 14 humans (melloware lead). Generates one hook per operation (`useShowPetById`), query-key getters, infinite queries, `queryOptions` with `skipToken` (a TanStack Query v5 API), suspense queries, `setQueryData`/`getQueryData` helpers, plus Zod/Valibot/Effect schemas, MSW mocks and a fetch (default) or axios client. Weekly downloads 3,602,695.
- **openapi-typescript + openapi-fetch + openapi-react-query** - **7.13.0 / 0.17.0 / 0.5.4**, all released **2026-02-11**; nothing since. `openapi-react-query` is a "type-safe tiny wrapper (1 kb) around @tanstack/react-query" (peer `@tanstack/react-query ^5.80`, `openapi-fetch ^0.17`). Repo `openapi-ts/openapi-typescript`: 8,423 stars, 287 open issues+PRs, pushed 2026-09-25; the entire first page of commits (2026-04-15..09-25) is `renovate[bot]` - **no human commits in that window**. Weekly downloads 14,695,173 / 15,798,164 / 740,825.

**Recommendation.** **orval 8** with `client: 'react-query'`, the fetch client and Zod output: it is the only one of the three with recent multi-author activity, a small issue backlog and weekly releases. Keep hey-api as the fallback (better `queryOptions`-style output) if its release cadence resumes. Avoid openapi-typescript/openapi-react-query for new work until human maintenance returns.

---

## 7. Tooling versions

| Tool | Latest | Released | Notes |
|---|---|---|---|
| Vite | **8.3.5** | 2026-10-21 | Vite 8.0 announced 2026-03-12: Rolldown as the single Rust bundler, ESM-only, "requires Node.js 20.19+, 22.12+"; `@vitejs/plugin-react` 6 drops Babel. 6.4.5 / 7.3.7 still patched (Oct 2026). |
| Vitest | **5.1.0** | 2026-11-02 | 5.0.0 on 2026-09-03; engines `^22.12.0 \|\| ^24.0.0 \|\| >=26.0.0`; peer `vite ^6.4 \|\| ^7 \|\| ^8`. |
| Playwright | **1.64.1** | 2026-10-14 | 8 releases since 2026-05-04; Node ≥20. |
| TypeScript | **7.0.2** | 2026-08-20 | The native Go compiler (7.0 announced 2026-07-08): strict on by default, deprecated options now errors, **no programmatic API until 7.1** (7.1 beta 2026-10-20), editor plugins for embedded languages lag. 6.0.3 (2026-04-16) is the last JS line; `@typescript/typescript6` for side-by-side. |
| React | **19.3.1** | 2026-10-14 | 19.3.0 2026-09-09; patch lines 19.2.9 / 19.1.10 / 19.0.9 same day. |
| Tailwind CSS | **4.3.4** | 2026-11-02 | 4.3.0 2026-05-08. |
| Node.js | **26 "Lithium"** = Active LTS | LTS since **2026-10-28** | Released 2026-05-05; Maintenance from 2027-10-20; **EOL 2029-04-30**. Node 24 "Krypton" moved to Maintenance 2026-10-20 (EOL 2028-04-30); Node 22 EOL 2027-04-30. |
| Docker image | `node:26` → 26.13.0 (Debian trixie) | - | Variants `node:26-slim`, `node:26-bookworm`, `node:26-alpine` (alpine 3.24); `lts`, `lts-alpine` and `latest` all point at 26.13.0. |

**Recommendation.** Vite 8 + Vitest 5 + Playwright 1.64 + React 19.3 + Tailwind 4.3 on Node 26 (`node:26-alpine` or `node:26-slim` in Docker). TypeScript: use **7.0.2** for `tsc`/CI type-checks, and verify your ESLint/typescript-eslint and editor setup works, otherwise pin 6.0.3 with `@typescript/typescript6` until 7.1 ships its API.

---

## Sources

shadcn/ui
- https://registry.npmjs.org/shadcn/latest
- https://api.github.com/repos/shadcn-ui/ui and https://api.github.com/repos/shadcn-ui/ui/releases?per_page=100
- https://api.github.com/repos/shadcn-ui/ui/commits?since=2026-08-04T00:00:00Z&per_page=100
- https://ui.shadcn.com/docs/changelog
- https://ui.shadcn.com/docs/changelog/2026-07-base-ui-default
- https://ui.shadcn.com/docs/changelog/2026-03-cli-v4
- https://ui.shadcn.com/docs/changelog/2026-02-radix-ui
- https://ui.shadcn.com/docs/changelog/2026-01-base-ui
- https://ui.shadcn.com/docs/cli
- https://ui.shadcn.com/docs/tailwind-v4
- https://ui.shadcn.com/docs/components
- https://ui.shadcn.com/docs/components/chart
- https://ui.shadcn.com/docs/components/data-table
- https://ui.shadcn.com/docs/forms , https://ui.shadcn.com/docs/forms/react-hook-form , https://ui.shadcn.com/docs/forms/tanstack-form
- https://registry.npmjs.org/@base-ui/react/latest , https://registry.npmjs.org/@base-ui-components/react
- https://api.github.com/repos/mui/base-ui and https://api.github.com/repos/mui/base-ui/releases?per_page=30
- https://registry.npmjs.org/radix-ui , https://github.com/radix-ui/primitives

TanStack
- https://registry.npmjs.org/@tanstack/react-query/latest , https://registry.npmjs.org/@tanstack/react-query (dist-tags)
- https://api.github.com/repos/TanStack/query , .../releases?per_page=100 , .../commits?since=2026-08-04T00:00:00Z&per_page=100
- https://registry.npmjs.org/@tanstack/react-table/latest , https://registry.npmjs.org/@tanstack/react-table (dist-tags)
- https://api.github.com/repos/TanStack/table , .../releases?per_page=100 , .../commits?since=2026-08-04T00:00:00Z&per_page=100
- https://tanstack.com/blog/announcing-tanstack-table-v9 , https://tanstack.com/table/latest/docs/overview
- https://registry.npmjs.org/@tanstack/react-virtual/latest ; https://api.github.com/repos/TanStack/virtual , .../releases , .../commits
- https://registry.npmjs.org/@tanstack/react-form/latest ; https://api.github.com/repos/TanStack/form , .../releases?per_page=100 ; https://github.com/TanStack/form/commits/main
- https://tanstack.com/form/latest/docs/overview , https://tanstack.com/form/latest/docs/framework/react/guides/validation
- https://tanstack.com/blog/announcing-tanstack-form-v1 , https://tanstack.com/blog/announcing-tanstack-form-v2-alpha
- https://registry.npmjs.org/@tanstack/react-store/latest ; https://api.github.com/repos/TanStack/store , .../releases ; https://github.com/TanStack/store/commits/main ; https://tanstack.com/store/latest/docs/overview
- https://registry.npmjs.org/@tanstack/react-pacer/latest , https://registry.npmjs.org/@tanstack/pacer/latest ; https://api.github.com/repos/TanStack/pacer , .../releases ; https://github.com/TanStack/pacer/commits/main ; https://tanstack.com/pacer/latest/docs/overview
- https://registry.npmjs.org/@tanstack/react-router/latest , https://registry.npmjs.org/@tanstack/react-router (dist-tags) ; https://api.github.com/repos/TanStack/router , .../releases , .../commits ; https://tanstack.com/router/latest/docs/framework/react/overview
- https://registry.npmjs.org/@tanstack/react-db/latest , https://registry.npmjs.org/@tanstack/db/latest ; https://api.github.com/repos/TanStack/db , .../releases ; https://github.com/TanStack/db/commits/main ; https://tanstack.com/db/latest/docs/overview ; https://tanstack.com/blog/tanstack-db-1.0-rc1-going-all-in-on-oracles
- https://tanstack.com/libraries ; https://tanstack.com/charts ; https://tanstack.com/charts/latest/docs/overview ; https://tanstack.com/charts/latest/docs/installation ; https://tanstack.com/blog/tanstack-charts-1-0 ; https://github.com/TanStack/charts ; https://github.com/TanStack/charts/releases ; https://registry.npmjs.org/@tanstack/charts/latest ; https://registry.npmjs.org/@tanstack/react-charts/latest
- https://registry.npmjs.org/react-charts (dist-tags and time) ; https://api.github.com/repos/TanStack/react-charts , .../releases ; https://github.com/TanStack/react-charts (archive notice)

Charts alternatives
- https://registry.npmjs.org/recharts/latest ; https://api.github.com/repos/recharts/recharts , .../releases?per_page=100 , .../commits?since=2026-08-04T00:00:00Z&per_page=100
- https://registry.npmjs.org/@visx/visx/latest ; https://api.github.com/repos/airbnb/visx , .../releases ; https://github.com/airbnb/visx/commits/master
- https://registry.npmjs.org/echarts/latest ; https://api.github.com/repos/apache/echarts/releases ; https://registry.npmjs.org/echarts-for-react (latest + time) ; https://api.github.com/repos/hustcc/echarts-for-react , .../releases ; https://github.com/hustcc/echarts-for-react/commits/master
- https://registry.npmjs.org/@nivo/core/latest ; https://api.github.com/repos/plouc/nivo , .../releases ; https://github.com/plouc/nivo/commits/master
- https://registry.npmjs.org/chart.js/latest ; https://api.github.com/repos/chartjs/Chart.js/releases ; https://registry.npmjs.org/react-chartjs-2/latest ; https://api.github.com/repos/reactchartjs/react-chartjs-2 , .../releases ; https://github.com/reactchartjs/react-chartjs-2/commits/master

Forms and state
- https://registry.npmjs.org/react-hook-form/latest ; https://api.github.com/repos/react-hook-form/react-hook-form , .../releases?per_page=100 ; https://github.com/react-hook-form/react-hook-form/commits/master
- https://registry.npmjs.org/zustand/latest ; https://api.github.com/repos/pmndrs/zustand , .../releases ; https://github.com/pmndrs/zustand/commits/main

OpenAPI
- https://registry.npmjs.org/@hey-api/openapi-ts/latest , https://registry.npmjs.org/@hey-api/openapi-ts (dist-tags) ; https://api.github.com/repos/hey-api/openapi-ts ; https://github.com/hey-api/openapi-ts/releases ; https://github.com/hey-api/hey-api , https://github.com/hey-api/hey-api/releases , https://github.com/hey-api/hey-api/commits/main ; https://heyapi.dev/openapi-ts/get-started ; https://heyapi.dev/openapi-ts/plugins/tanstack-query ; https://heyapi.dev/openapi-ts/migrating
- https://registry.npmjs.org/orval/latest ; https://api.github.com/repos/orval-labs/orval , .../releases ; https://github.com/orval-labs/orval/commits/master ; https://orval.dev/ , https://orval.dev/docs , https://orval.dev/docs/guides/react-query
- https://registry.npmjs.org/openapi-typescript/latest , https://registry.npmjs.org/openapi-fetch/latest , https://registry.npmjs.org/openapi-react-query/latest ; https://api.github.com/repos/openapi-ts/openapi-typescript , .../releases?per_page=100 ; https://github.com/openapi-ts/openapi-typescript/commits/main ; https://openapi-ts.dev/openapi-react-query/

Tooling
- https://registry.npmjs.org/vite/latest ; https://api.github.com/repos/vitejs/vite/releases?per_page=100 ; https://vite.dev/blog/announcing-vite8
- https://registry.npmjs.org/vitest/latest ; https://api.github.com/repos/vitest-dev/vitest/releases?per_page=50
- https://registry.npmjs.org/@playwright/test/latest ; https://api.github.com/repos/microsoft/playwright/releases?per_page=30
- https://registry.npmjs.org/typescript/latest ; https://api.github.com/repos/microsoft/TypeScript/releases?per_page=30 ; https://devblogs.microsoft.com/typescript/announcing-typescript-7-0/
- https://registry.npmjs.org/react/latest ; https://api.github.com/repos/facebook/react/releases?per_page=30
- https://registry.npmjs.org/tailwindcss/latest ; https://api.github.com/repos/tailwindlabs/tailwindcss/releases?per_page=30
- https://registry.npmjs.org/react-router/latest ; https://api.github.com/repos/remix-run/react-router/releases?per_page=100
- https://raw.githubusercontent.com/nodejs/Release/main/schedule.json ; https://nodejs.org/en/about/previous-releases
- https://raw.githubusercontent.com/docker-library/official-images/master/library/node

Weekly downloads: https://api.npmjs.org/downloads/point/last-week/<package> for every package named above (week 2026-10-28..2026-11-03).
