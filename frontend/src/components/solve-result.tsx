import { createContext, useContext, type ReactNode } from "react"

import type { NurseAccounting, RuleMatch, RuleResult, SolveResult, SolverStatistics, Violation } from "@/api/generated/model"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { stoppedBy } from "@/lib/solve-words"
import { scrollableRegion, shortDay } from "@/lib/utils"
import { WEIGHTS } from "@/lib/weights"

const labels = new Map(WEIGHTS.map((weight) => [weight.name as string, weight.label]))
/** Who a line of the solver's is about, and when if its words do not say: most of them hold the date already. */
const whose = (row: { full_name: string; hospital_id?: string | null; date?: string | null; text: string }) =>
  `${row.full_name || row.hospital_id || "The unit"}${row.date && !row.text.includes(row.date) ? `, ${shortDay(row.date)}` : ""}`

/** The level their heading takes depends on what is above: the roster page has the draft's heading and the result's page only its title. */
const HeadingLevel = createContext<"h2" | "h4">("h4")

function Panel({ id, title, children }: { id: string; title: string; children: ReactNode }) {
  const Heading = useContext(HeadingLevel)
  return (
    <section aria-labelledby={id} className="flex flex-col gap-2">
      <Heading id={id} className="text-sm font-medium">{title}</Heading>
      {children}
    </section>
  )
}

function Accounting({ nurses, unitCost }: { nurses: NurseAccounting[]; unitCost: number | null }) {
  return (
    <Panel id="result-hours" title="Hours and cost per nurse">
      <Table container={scrollableRegion("Each nurse's hours and cost")}>
        <TableHeader>
          <TableRow>
            <TableHead>Nurse</TableHead>
            <TableHead className="text-end">Contract</TableHead>
            <TableHead className="text-end">Leave credit</TableHead>
            <TableHead className="text-end">Required</TableHead>
            <TableHead className="text-end">Worked</TableHead>
            <TableHead className="text-end">Overtime</TableHead>
            <TableHead className="text-end">Shortfall</TableHead>
            <TableHead>Shifts</TableHead>
            <TableHead className="text-end">Cost</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {nurses.map((nurse) => (
            <TableRow key={nurse.hospital_id}>
              <TableHead scope="row" className="font-normal">{nurse.full_name || nurse.hospital_id}</TableHead>
              {[nurse.contract, nurse.leave_credit, nurse.required, nurse.hours_worked, nurse.overtime, nurse.shortfall].map((hours, index) => (
                <TableCell key={index} className="text-end tabular-nums">{hours}</TableCell>
              ))}
              <TableCell className="tabular-nums">{Object.entries(nurse.shifts).filter(([, count]) => count > 0).map(([code, count]) => `${code} ${count}`).join(", ")}</TableCell>
              <TableCell className="text-end tabular-nums">{nurse.cost}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      <p className="text-sm text-muted-foreground">In hours, apart from the shifts and the cost.{unitCost ? ` The unit as a whole costs ${unitCost} more, for what no one nurse is behind.` : ""}</p>
    </Panel>
  )
}

function Occurrence({ match }: { match: RuleMatch }) {
  return <li className="wrap-anywhere">{whose(match)}: {match.text}</li>
}

function Rule({ rule }: { rule: RuleResult }) {
  const name = labels.get(rule.rule) ?? rule.rule
  return (
    <li className="flex flex-col gap-1 border-b py-2 last:border-b-0">
      <p className="flex justify-between gap-4 font-medium"><span>{name}</span><span className="tabular-nums">{rule.penalty}</span></p>
      {rule.amount !== null && (
        <p className="text-muted-foreground tabular-nums">{rule.amount} × {rule.weight}, its weight. Counted in: {rule.counted_in}.</p>
      )}
      {rule.largest.length > 0 && <ul className="list-disc ps-5">{rule.largest.map((match, index) => <Occurrence key={index} match={match} />)}</ul>}
      {rule.others > 0 && <p className="text-muted-foreground">and {rule.others} more like these</p>}
    </li>
  )
}

function Penalties({ rules, explained }: { rules: RuleResult[]; explained: boolean }) {
  return (
    <Panel id="result-rules" title="Penalties per rule">
      {!explained && <p className="text-sm">These totals are what the solver reported. The occurrences behind them could not be explained: the solver's code no longer reads this solve's input.</p>}
      {rules.length === 0
        ? <p className="text-sm">No soft rule is broken.</p>
        : (
          <>
            <ul className="flex flex-col text-sm">{rules.map((rule) => <Rule key={rule.rule} rule={rule} />)}</ul>
            <p className="text-sm text-muted-foreground">Every other soft rule costs nothing.</p>
          </>
        )}
    </Panel>
  )
}

function Violations({ id, title, rows, note }: { id: string; title: string; rows: Violation[]; note: string }) {
  return (
    <Panel id={id} title={title}>
      <p className="text-sm text-muted-foreground">{note}</p>
      <ul className="list-disc ps-5 text-sm">{rows.map((row, index) => <li key={index} className="wrap-anywhere">{whose(row)}: {row.text}</li>)}</ul>
    </Panel>
  )
}

function Precheck({ issues }: { issues: string[] }) {
  return (
    <Panel id="result-precheck" title="The solver's check">
      {issues.length === 0
        ? <p className="text-sm">Before searching, it warned of nothing.</p>
        : <ul className="list-disc ps-5 text-sm">{issues.map((issue) => <li key={issue} className="wrap-anywhere">{issue}</li>)}</ul>}
    </Panel>
  )
}

const shown = (value: number | null | undefined, unit = "") => (value === null || value === undefined ? "Not known" : `${Math.round(value * 100) / 100}${unit}`)

function Statistics({ statistics }: { statistics: SolverStatistics }) {
  const rows: [string, string][] = [
    ["Outcome", statistics.status],
    ["What stopped it", stoppedBy(statistics.stopped_by)],
    ["Searched for", shown(statistics.solve_seconds, " s")],
    ["Time limit", shown(statistics.time_limit_seconds, " s")],
    ["Improving rosters", shown(statistics.improvements)],
    ["Cost as the search counted it", shown(statistics.objective)],
    ["Lowest cost possible, as far as it proved", shown(statistics.best_bound)],
    ["Workers", shown(statistics.workers)],
    ["Building the model took", shown(statistics.build_seconds, " s")],
    ["Deterministic time", shown(statistics.deterministic_time)],
    ["Model variables", shown(statistics.variables)],
    ["Model constraints", shown(statistics.constraints)],
    ["Model objective terms", shown(statistics.objective_terms)],
  ]
  return (
    <Panel id="result-statistics" title="Solver statistics">
      <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm tabular-nums">
        {rows.map(([name, value]) => (
          <div key={name} className="contents">
            <dt className="text-muted-foreground">{name}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
    </Panel>
  )
}

/** Everything a result holds but its grid, for the draft beside it and for any result opened from the history. */
export function SolveResultPanels({ result, headingLevel = "h4" }: { result: SolveResult; headingLevel?: "h2" | "h4" }) {
  return (
    <HeadingLevel.Provider value={headingLevel}>
    <div className="flex flex-col gap-6">
      {result.nurses.length > 0 && <Accounting nurses={result.nurses} unitCost={result.unit_cost} />}
      {result.grid && <Penalties rules={result.rules} explained={result.explained} />}
      {result.violations.length > 0 && (
        <Violations id="result-violations" title="Hard rules this roster breaks" rows={result.violations} note="A roster that breaks one does not become a draft." />
      )}
      {result.elapsed_violations.length > 0 && (
        <Violations id="result-facts" title="Recorded facts that broke rules" rows={result.elapsed_violations} note="These days are over, so no solve could change them." />
      )}
      {result.statistics && <Precheck issues={result.precheck} />}
      {result.statistics && <Statistics statistics={result.statistics} />}
    </div>
    </HeadingLevel.Provider>
  )
}
