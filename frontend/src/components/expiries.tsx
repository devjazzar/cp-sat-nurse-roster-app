import { Link } from "@tanstack/react-router"

import { useListExpiries } from "@/api/generated/endpoints"
import { ExpiryState, type ExpiryRow } from "@/api/generated/model"
import { Badge } from "@/components/ui/badge"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { scrollableRegion, shortDay } from "@/lib/utils"

/** The horizon is the hospital's one meaning of "expiring" (ticket 37): fixed, so the page can say it. */
export const HORIZON_DAYS = 90

const STATE_WORDS: Record<ExpiryState, string> = {
  expired: "Expired",
  expiring: "Expiring",
  no_record: "No record",
}

/** What the list holds and leaves out, in one sentence each, for the page and the manager's Nurses page alike. */
export const EXPIRIES_SAY = `Skills that have expired or expire within ${HORIZON_DAYS} days, and skills required to work that a nurse has no record of. ` +
  "Deactivated nurses and those past their end date are left out."

function State({ state }: { state: ExpiryState }) {
  return <Badge variant={state === ExpiryState.expired ? "destructive" : "outline"}>{STATE_WORDS[state]}</Badge>
}

function ExpiriesTable({ rows, label, showUnit }: { rows: ExpiryRow[]; label: string; showUnit: boolean }) {
  return (
    <Table container={scrollableRegion(label)}>
      <TableHeader>
        <TableRow>
          <TableHead>Name</TableHead>
          <TableHead>Hospital ID</TableHead>
          {showUnit && <TableHead>Unit</TableHead>}
          <TableHead>Skill</TableHead>
          <TableHead>State</TableHead>
          <TableHead>Expiry</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.map((row) => (
          <TableRow key={`${row.nurse_id} ${row.skill}`}>
            <TableCell>{row.full_name}</TableCell>
            <TableCell translate="no">{row.hospital_id}</TableCell>
            {showUnit && <TableCell>{row.unit.name}</TableCell>}
            <TableCell>{row.skill}</TableCell>
            <TableCell><State state={row.state} /></TableCell>
            <TableCell className="tabular-nums">
              {row.expiry ? shortDay(row.expiry) : <span className="text-muted-foreground">Required to work</span>}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}

/** The list as the reader may see it: every unit's for the CNO and the Deputy CNO, a manager's own unit's. Oldest date first,
 *  then the skills nobody has recorded, as the API orders them. */
export function ExpiriesList({ label, showUnit }: { label: string; showUnit: boolean }) {
  const expiries = useListExpiries()
  if (expiries.isPending) return <p>Loading the expiries…</p>
  if (expiries.isError) return <p role="alert">The expiries could not be read. Reload the page to try again.</p>
  if (expiries.data.rows.length === 0) {
    return <p>No skill has expired or expires within {HORIZON_DAYS} days, and every nurse has a record of each skill required to work.</p>
  }
  return <ExpiriesTable rows={expiries.data.rows} label={label} showUnit={showUnit} />
}

/** The CNO's home: how many rows the page has, read afresh, so it always matches the page. */
export function ExpiriesCount() {
  const expiries = useListExpiries()
  if (expiries.isPending) return null
  if (expiries.isError) return <p role="alert">The expiries could not be read, so their count is not shown. Reload the page to try again.</p>
  const { count } = expiries.data
  const link = <Link to="/expiries" className="underline underline-offset-3">the Expiries page</Link>
  if (count === 0) return <p>Nothing is on {link}: no skill has expired or expires within {HORIZON_DAYS} days, and none required to work is missing.</p>
  return <p>{count} {count === 1 ? "entry is" : "entries are"} on {link}: skills expired, expiring within {HORIZON_DAYS} days, or required and not recorded.</p>
}
