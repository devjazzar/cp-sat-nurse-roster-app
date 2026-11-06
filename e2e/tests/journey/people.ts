import type { Swap } from "../../support"

/** Who the journey makes, and what it keeps in its notebook (e2e/.stack/<project>.journey.json) for the steps after. */
export const UNIT = "Ward B"

export const people = {
  cno: { username: "nadia", name: "Nadia Faris", role: "CNO" },
  deputy: { username: "yusuf", name: "Yusuf Rahman", role: "Deputy CNO" },
  manager: { username: "rana", name: "Rana Haddad", role: "Unit Manager" },
  // The solver's four-nurse sample, as hospital IDs of their own: two women and two men.
  nurses: [
    { username: "W101", name: "Sara Amin", gender: "Female" },
    { username: "W102", name: "Tariq Aziz", gender: "Male" },
    { username: "W103", name: "Lina Odeh", gender: "Female" },
    { username: "W104", name: "Karim Saad", gender: "Male" },
  ],
}

export const nameOf = (username: string) =>
  [people.cno, people.deputy, people.manager, ...people.nurses].find((person) => person.username === username)?.name ?? username

export type Journey = {
  /** "2026-12": the month the manager rosters; the month after, whose requests the nurses make. */
  rostered: string
  requested: string
  /** The password each was given when made, and the one they chose at their first login. */
  given: Record<string, string>
  chosen: Record<string, string>
  /** The swap the journey's nurses made, which the manager approved: version 2. */
  swap: Swap
}
