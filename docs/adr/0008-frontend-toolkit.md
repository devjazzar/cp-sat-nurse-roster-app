---
status: accepted
date: 2026-11-04
---
# Frontend toolkit: shadcn/ui on Base UI, TanStack Query/Router/Table/Virtual, React Hook Form, Zustand, Recharts, orval

Chosen on 2026-11-04 from the maintenance signals recorded in
`docs/research/2026-11-04-frontend-stack.md`; the reasons below are why a reader should not
"upgrade" one of these to its TanStack or newer sibling without re-reading that file.

- **shadcn/ui on Base UI, Tailwind 4, React 19.** shadcn/ui made Base UI its default base in
  July 2026; Radix is still supported but no longer the documented first path. The copied
  components under `components/ui` are our code: upgrades go through the CLI's diff command,
  deliberately, never automatically.
- **TanStack Query 5** for all server state, including solve progress polling.
- **TanStack Router 1** for file-based, typed routes and typed search parameters (unit, month
  and filters live in the URL). React Router was the mainstream alternative and gains nothing here.
- **TanStack Table 9 and TanStack Virtual** from day one, for every list and for the roster
  grid's row and column model.
- **React Hook Form with Zod**, not TanStack Form: TanStack Form 1.x is stable but has not
  shipped since August 2026 while its v2 rewrite is in alpha; React Hook Form has the widest
  use and shadcn's `Field` component documents both. Revisit when TanStack Form 2 is stable.
- **Zustand** for the little client-only state (current unit, grid selection, unsaved cell
  edits). TanStack Store is an internal primitive in alpha and is not used directly.
- **Recharts 3 through shadcn's chart components.** TanStack Charts reached 1.0 on 2026-10-03
  with one author; reconsider it in a year.
- **TanStack Pacer** only behind one hook of ours (debounced live validation while editing
  cells); it is beta by its own docs, so one file absorbs any API change.
- **orval** generates the typed TanStack Query hooks, fetch client and Zod schemas from the
  Django Ninja OpenAPI document, in CI, so a backend change that breaks the frontend fails
  the build. hey-api (one maintainer, no release since June 2026) and the openapi-typescript
  family (bot-only commits since April 2026) were rejected.
- **Tooling:** Vite 8, Vitest 5, Playwright, Node 26 LTS for the build stage only, TypeScript 6
  until Vite and Vitest run cleanly on the Go-native TypeScript 7.
