import { keepPreviousData } from "@tanstack/react-query"
import { createFileRoute, Link } from "@tanstack/react-router"
import { z } from "zod"

import { useGetMyLeave } from "@/api/generated/endpoints"
import { Role } from "@/api/generated/model"
import { MONTH_LINK, monthInAddress, MonthNav } from "@/components/month-nav"
import { Card, CardContent } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { dayRange, monthName, scrollableRegion } from "@/lib/utils"
import { onlyFor } from "@/session"

const searchSchema = z.object({ month: monthInAddress })

export const Route = createFileRoute("/_signed-in/my-leave")({
  validateSearch: (search) => searchSchema.parse(search),
  beforeLoad: onlyFor(Role.staff_nurse, Role.unit_manager),
  staticData: { title: "My leave" },
  component: MyLeavePage,
})

function MyLeavePage() {
  const { month } = Route.useSearch()
  const leave = useGetMyLeave(month ? { month } : undefined, { query: { placeholderData: keepPreviousData } })
  const answer = leave.data

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-4">
      <h1 className="text-xl font-medium">My leave</h1>
      <p className="text-muted-foreground">Your unit manager records your leave. Only you and your manager can see its type: colleagues see a day off.</p>
      {leave.isPending && <p>Loading…</p>}
      {leave.isError && <p role="alert">Your leave could not be read. Reload the page to try again.</p>}
      {answer && <MonthNav month={answer.month} link={(next, label) => <Link to="/my-leave" search={{ month: next }} className={MONTH_LINK}>{label}</Link>} />}
      {answer && answer.runs.length === 0 && <p>You have no leave recorded in {monthName(answer.month)}.</p>}
      {answer && answer.runs.length > 0 && (
        <Card>
          <CardContent>
            <Table container={scrollableRegion(`Your leave in ${monthName(answer.month)}`)}>
              <TableHeader>
                <TableRow>
                  <TableHead>Dates</TableHead>
                  <TableHead>Days</TableHead>
                  <TableHead>Type</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {answer.runs.map((run) => (
                  <TableRow key={run.first}>
                    <TableCell className="tabular-nums">{dayRange(run.first, run.last)}</TableCell>
                    <TableCell className="tabular-nums">{run.days}</TableCell>
                    <TableCell>{run.leave_type}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
