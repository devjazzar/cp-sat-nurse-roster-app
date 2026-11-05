import { linkOptions } from "@tanstack/react-router"

import { Role } from "@/api/generated/model"

export const ROLE_NAMES: Record<Role, string> = {
  system_admin: "System Admin",
  cno: "CNO",
  deputy_cno: "Deputy CNO",
  unit_manager: "Unit Manager",
  staff_nurse: "Staff Nurse",
}

const ADMIN_PAGES = linkOptions([
  { to: "/health", label: "Health" },
  { to: "/settings", label: "Technical settings" },
  { to: "/users", label: "Users" },
  { to: "/audit-log", label: "Audit log" },
])
const HOME = { to: "/", label: "Home", activeOptions: { exact: true } } as const
const RULES = { to: "/hospital-rules", label: "Hospital rules" } as const
const CATALOGUE = [
  { to: "/shifts", label: "Shifts" },
  { to: "/leave-types", label: "Leave types" },
  { to: "/holidays", label: "Holidays and Ramadan" },
] as const
const UNITS = { to: "/units", label: "Units" } as const
const WITH_CATALOGUE = linkOptions([HOME, ...CATALOGUE])
const WITH_RULES_AND_CATALOGUE = linkOptions([HOME, RULES, ...CATALOGUE])
const CNO_PAGES = linkOptions([HOME, UNITS, RULES, ...CATALOGUE])

/** What each role reaches from the header. A role's pages join its list as their tickets land; the
 *  API refuses the rest whatever this says. The catalogue's pages open for the System Admin too, since
 *  every role may read them, but nothing in their work calls for a link. */
export const NAVIGATION = {
  system_admin: ADMIN_PAGES,
  cno: CNO_PAGES,
  deputy_cno: WITH_RULES_AND_CATALOGUE,
  unit_manager: WITH_CATALOGUE,
  staff_nurse: WITH_CATALOGUE,
} satisfies Record<Role, unknown>
