import { createFileRoute, Link, redirect, useRouteContext } from "@tanstack/react-router"
import type { ReactNode } from "react"

import { useGetMyUnit, useListUnits } from "@/api/generated/endpoints"
import { Role } from "@/api/generated/model"
import { ROLE_NAMES } from "@/roles"

export const Route = createFileRoute("/_signed-in/")({
  beforeLoad: ({ context }) => {
    if (context.user.role === Role.system_admin) throw redirect({ to: "/health" })
  },
  staticData: { title: "Home" },
  component: HomePage,
})

/** A deactivated manager's unit waits here for the CNO, who is told nowhere else, so a failed read must say so. */
function CnoHome() {
  const units = useListUnits()
  const waiting = (units.data ?? []).filter((unit) => !unit.archived && !unit.manager).map((unit) => unit.name)
  return (
    <>
      <p>Set the rules every unit rosters by under Hospital rules, and keep the shifts, leave types, holidays and Ramadan dates they use.</p>
      <p>Add the hospital's nurses under <Link to="/nurses" className="underline underline-offset-3">Nurses</Link>.</p>
      {units.isError && <p role="alert">The units could not be read, so any with no manager are not listed. Reload the page to try again.</p>}
      {waiting.length > 0 && (
        <p>
          {waiting.join(", ")} {waiting.length === 1 ? "has" : "have"} no manager.{" "}
          <Link to="/units" className="underline underline-offset-3">Assign one under Units</Link>
        </p>
      )}
    </>
  )
}

function ManagerHome() {
  const units = useListUnits()
  if (units.isPending) return <p>Loading…</p>
  if (units.isError) return <p role="alert">Your unit could not be read. Reload the page to try again.</p>
  const unit = units.data[0]
  if (!unit) return <p>No unit is assigned to you yet. The CNO assigns each unit its manager.</p>
  return (
    <>
      <p>Your unit is {unit.name}.</p>
      {unit.rules_need_review && (
        <p>
          Its unit rules are still the seeded defaults.{" "}
          <Link to="/unit-rules" className="underline underline-offset-3">Review them before its first solve</Link>
        </p>
      )}
    </>
  )
}

function NurseHome() {
  const unit = useGetMyUnit()
  if (unit.isPending) return <p>Loading…</p>
  if (unit.isError) return <p role="alert">Your unit could not be read. Reload the page to try again.</p>
  return (
    <>
      <p>Your unit is {unit.data.name}.</p>
      <p>No roster yet.</p>
    </>
  )
}

/** Every role but the System Admin's, so a new role cannot go without a home. */
const HOME_OF: Record<Exclude<Role, "system_admin">, () => ReactNode> = {
  cno: CnoHome,
  deputy_cno: () => <p>Submitted rosters waiting for your decision will be listed here.</p>,
  unit_manager: ManagerHome,
  staff_nurse: NurseHome,
}

function HomePage() {
  const { user } = useRouteContext({ from: "/_signed-in" })
  const Home = HOME_OF[user.role as keyof typeof HOME_OF]
  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-2">
      <h1 className="text-xl font-medium">{user.full_name || user.username}</h1>
      <p className="text-muted-foreground">{ROLE_NAMES[user.role]}</p>
      <Home />
    </div>
  )
}
