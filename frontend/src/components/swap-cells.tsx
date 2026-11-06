import type { ReactNode } from "react"

import type { SwapCellRow } from "@/api/generated/model"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { cellWords } from "@/lib/swap-words"
import { scrollableRegion, shortDay } from "@/lib/utils"

/** Every cell a swap changes, before and after, by date. `extra` adds the manager's columns. */
export function SwapCells<Row extends SwapCellRow>({ cells, label, names, extra = [] }: {
  cells: Row[]
  label: string
  names: Record<string, string>
  extra?: { heading: string; cell: (row: Row) => ReactNode }[]
}) {
  return (
    // On a phone the cells wrap, so a swap's four columns fit 320 px without scrolling; the manager's extra ones may still scroll.
    <Table container={scrollableRegion(label)} className="max-sm:[&_td]:whitespace-normal max-sm:[&_th]:whitespace-normal">
      <TableHeader>
        <TableRow>
          <TableHead>Nurse</TableHead>
          <TableHead>Date</TableHead>
          <TableHead>Was</TableHead>
          <TableHead>Becomes</TableHead>
          {extra.map((column) => <TableHead key={column.heading}>{column.heading}</TableHead>)}
        </TableRow>
      </TableHeader>
      <TableBody>
        {cells.map((row) => (
          <TableRow key={`${row.hospital_id}-${row.date}`}>
            <TableCell>{row.full_name || row.hospital_id}</TableCell>
            <TableCell className="tabular-nums">{shortDay(row.date)}</TableCell>
            <TableCell>{cellWords(row.before, names)}</TableCell>
            <TableCell>{cellWords(row.after, names)}</TableCell>
            {extra.map((column) => <TableCell key={column.heading}>{column.cell(row)}</TableCell>)}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}
