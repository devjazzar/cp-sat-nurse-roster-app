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
const NURSES = { to: "/nurses", label: "Nurses" } as const
const UNIT_RULES = { to: "/unit-rules", label: "Unit rules" } as const
const ATTRIBUTES = { to: "/rostering-attributes", label: "Rostering attributes" } as const
const LEAVE = { to: "/leave", label: "Leave" } as const
const MY_LEAVE = { to: "/my-leave", label: "My leave" } as const
const NURSE_PAGES = linkOptions([HOME, MY_LEAVE, ...CATALOGUE])
const MANAGER_PAGES = linkOptions([HOME, UNIT_RULES, ATTRIBUTES, NURSES, LEAVE, ...CATALOGUE])
const DEPUTY_PAGES = linkOptions([HOME, UNIT_RULES, ATTRIBUTES, LEAVE, RULES, ...CATALOGUE])
const CNO_PAGES = linkOptions([HOME, UNITS, UNIT_RULES, ATTRIBUTES, NURSES, LEAVE, RULES, ...CATALOGUE])

/** What each role reaches from the header. A role's pages join its list as their tickets land; the
 *  API refuses the rest whatever this says. The catalogue's pages open for the System Admin too, since
 *  every role may read them, but nothing in their work calls for a link. */
export const NAVIGATION = {
  system_admin: ADMIN_PAGES,
  cno: CNO_PAGES,
  deputy_cno: DEPUTY_PAGES,
  unit_manager: MANAGER_PAGES,
  staff_nurse: NURSE_PAGES,
} satisfies Record<Role, unknown>
