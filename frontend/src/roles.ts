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
const HOME_ONLY = linkOptions([HOME])
const HOME_AND_RULES = linkOptions([HOME, { to: "/hospital-rules", label: "Hospital rules" }])

/** What each role reaches from the header. A role's pages join its list as their tickets land; the
 *  API refuses the rest whatever this says. */
export const NAVIGATION = {
  system_admin: ADMIN_PAGES,
  cno: HOME_AND_RULES,
  deputy_cno: HOME_AND_RULES,
  unit_manager: HOME_ONLY,
  staff_nurse: HOME_ONLY,
} satisfies Record<Role, unknown>
