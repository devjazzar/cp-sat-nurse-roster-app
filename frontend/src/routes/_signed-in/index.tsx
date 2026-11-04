import { createFileRoute, redirect, useRouteContext } from "@tanstack/react-router"

import { Role } from "@/api/generated/model"
import { ROLE_NAMES } from "@/roles"

/** The System Admin's home is the health page. Nothing below can be reached by that role. */
const WHAT_COMES_HERE: Record<Exclude<Role, "system_admin">, string> = {
  cno: "The hospital's rules, its units and its nurses will be managed from here.",
  deputy_cno: "Submitted rosters waiting for your decision will be listed here.",
  unit_manager: "No unit is assigned to you yet. The CNO assigns each unit its manager.",
  staff_nurse: "Your unit's approved roster will be shown here.",
}

export const Route = createFileRoute("/_signed-in/")({
  beforeLoad: ({ context }) => {
    if (context.user.role === Role.system_admin) throw redirect({ to: "/health" })
  },
  staticData: { title: "Home" },
  component: HomePage,
})

function HomePage() {
  const { user } = useRouteContext({ from: "/_signed-in" })
  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-2">
      <h1 className="text-xl font-medium">{user.full_name || user.username}</h1>
      <p className="text-muted-foreground">{ROLE_NAMES[user.role]}</p>
      <p>{WHAT_COMES_HERE[user.role as keyof typeof WHAT_COMES_HERE]}</p>
    </div>
  )
}
