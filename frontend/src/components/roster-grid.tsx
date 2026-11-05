import { tableFeatures, useTable, type ColumnDef } from "@tanstack/react-table"
import { useVirtualizer } from "@tanstack/react-virtual"
import { useMemo, useRef } from "react"

import type { Draft, GridCell, GridRow, GridShift } from "@/api/generated/model"
import { asDate, cn, readableOn, scrollableRegion } from "@/lib/utils"

const features = tableFeatures({})
const weekday = new Intl.DateTimeFormat("en-GB", { weekday: "short", timeZone: "UTC" })
const longDay = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "long", timeZone: "UTC" })

const NURSE_HEADER = "Nurse"
const ROW_HEIGHT = 33
/** A unit's usual month fits in the page, where the browser's find and a screen reader see all of it. Past this, only the rows
 *  in view are drawn, and `aria-rowcount` still says how many there are. */
const WINDOWED_ABOVE = 60

/** How a cell that is no shift looks and reads. */
const NOT_WORKING: Record<Exclude<GridCell["kind"], "shift">, { says: string; mark: string; className?: string }> = {
  leave: { says: "Leave", mark: "L", className: "bg-muted" },
  outside: { says: "Outside their dates", mark: "·", className: "text-muted-foreground" },
  off: { says: "Off", mark: "" },
}

function Cell({ cell, shifts, title }: { cell: GridCell; shifts: Map<string, GridShift>; title: string }) {
  if (cell.kind === "shift") {
    const shift = shifts.get(cell.shift)
    return (
      <td title={`${title}: ${shift?.display_name ?? cell.shift}`} className="border-b border-s p-0 text-center text-xs font-medium"
        style={shift ? { backgroundColor: shift.colour, color: readableOn(shift.colour) } : undefined}>
        {cell.shift}
      </td>
    )
  }
  const { says, mark, className } = NOT_WORKING[cell.kind]
  return (
    <td title={`${title}: ${says}`} className={cn("border-b border-s p-0 text-center text-xs font-medium", className)}>
      <span aria-hidden="true">{mark}</span><span className="sr-only">{says}</span>
    </td>
  )
}

/** The draft's nurses across its dates. Nurse names stay in view while it scrolls, and on a phone it scrolls sideways. */
export function RosterGrid({ draft, label }: { draft: Draft; label: string }) {
  const scroller = useRef<HTMLDivElement>(null)
  const shifts = useMemo(() => new Map(draft.shifts.map((shift) => [shift.code, shift])), [draft.shifts])
  const columns = useMemo<ColumnDef<typeof features, GridRow>[]>(() => [
    { id: "nurse", header: NURSE_HEADER, accessorFn: (row) => row.full_name || row.hospital_id },
    ...draft.days.map((day, index) => ({
      id: day.date,
      header: day.date,
      accessorFn: (row: GridRow) => row.cells[index],
    })),
  ], [draft.days])
  const table = useTable({ features, columns, data: draft.rows })
  const rows = table.getRowModel().rows
  const windowed = rows.length > WINDOWED_ABOVE
  const virtualizer = useVirtualizer({
    enabled: windowed,
    count: rows.length,
    getScrollElement: () => scroller.current,
    estimateSize: () => ROW_HEIGHT,
    overscan: 8,
  })
  const items = windowed ? virtualizer.getVirtualItems() : rows.map((_, index) => ({ index, start: index * ROW_HEIGHT, end: (index + 1) * ROW_HEIGHT }))
  const before = windowed ? (items[0]?.start ?? 0) : 0
  const after = windowed ? virtualizer.getTotalSize() - (items.at(-1)?.end ?? 0) : 0

  const region = scrollableRegion(label)

  // `relative` keeps each cell's screen-reader text inside the scroller, or the whole page scrolls sideways.
  return (
    <div ref={scroller} {...region}
      className={cn(region.className, "relative overflow-auto border", windowed && "max-h-[70svh]")}>
      <table aria-rowcount={rows.length + 1} className="w-max border-separate border-spacing-0 text-sm">
        <thead className="sticky top-0 z-20 bg-background">
          <tr aria-rowindex={1}>
            {table.getHeaderGroups()[0].headers.map((header, index) => {
              if (index === 0) return <th key={header.id} scope="col" className="sticky start-0 z-30 min-w-40 border-b bg-background px-2 py-1 text-start font-medium">{NURSE_HEADER}</th>
              const day = draft.days[index - 1]
              const date = asDate(day.date)
              return (
                <th key={header.id} scope="col" title={longDay.format(date) + (day.holiday ? ", public holiday" : "")}
                  className={cn("w-9 min-w-9 border-b border-s px-0 py-1 text-center text-xs font-medium tabular-nums", (day.weekend || day.holiday) && "bg-muted")}>
                  <span className="block">{date.getUTCDate()}</span>
                  {/* Plain foreground: the muted one falls short of 4.5:1 on the shaded days. */}
                  <span className="block font-normal">{day.holiday ? "Hol" : weekday.format(date)}</span>
                </th>
              )
            })}
          </tr>
        </thead>
        <tbody>
          {before > 0 && <tr aria-hidden="true"><td style={{ height: before }} colSpan={draft.days.length + 1} /></tr>}
          {items.map(({ index }) => {
            const row = rows[index]
            const [nurse, ...cells] = row.getAllCells()
            const name = nurse.getValue() as string
            return (
              <tr key={row.id} ref={windowed ? virtualizer.measureElement : undefined} data-index={index} aria-rowindex={index + 2} style={{ height: ROW_HEIGHT }}>
                {/* Wraps rather than truncates: a name has to be reachable whole, and a title is not by keyboard. */}
                <th scope="row" className="sticky start-0 z-10 max-w-48 border-b bg-background px-2 py-1 text-start font-normal wrap-anywhere">{name}</th>
                {cells.map((cell) => (
                  <Cell key={cell.id} cell={cell.getValue() as GridCell} shifts={shifts} title={`${name}, ${longDay.format(asDate(cell.column.id))}`} />
                ))}
              </tr>
            )
          })}
          {after > 0 && <tr aria-hidden="true"><td style={{ height: after }} colSpan={draft.days.length + 1} /></tr>}
        </tbody>
      </table>
    </div>
  )
}

export function GridLegend({ draft }: { draft: Draft }) {
  return (
    <ul aria-label="What the cells mean" className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-muted-foreground">
      {draft.shifts.map((shift) => (
        <li key={shift.code} className="flex items-center gap-1.5">
          <span aria-hidden="true" className="inline-flex size-6 items-center justify-center rounded-sm text-xs font-medium"
            style={{ backgroundColor: shift.colour, color: readableOn(shift.colour) }}>{shift.code}</span>
          {shift.display_name}, {shift.hours} hours
        </li>
      ))}
      <li className="flex items-center gap-1.5"><span aria-hidden="true" className="inline-flex size-6 items-center justify-center rounded-sm bg-muted text-xs font-medium text-foreground">L</span>Leave</li>
      <li className="flex items-center gap-1.5"><span aria-hidden="true" className="inline-flex size-6 items-center justify-center rounded-sm border text-xs">·</span>Before their start date or after their end date</li>
      <li className="flex items-center gap-1.5"><span aria-hidden="true" className="inline-flex size-6 rounded-sm border" />Off</li>
      <li>Hol: a public holiday</li>
    </ul>
  )
}
