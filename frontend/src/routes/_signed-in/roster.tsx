import { zodResolver } from "@hookform/resolvers/zod"
import { keepPreviousData, useQueryClient } from "@tanstack/react-query"
import { createFileRoute, Link, useRouteContext } from "@tanstack/react-router"
import { useEffect, useRef, useState } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"

import { ApiError } from "@/api/fetcher"
import {
  getGetRosterMonthQueryKey,
  getGetSolveProgressQueryKey,
  getPreviewSolveQueryKey,
  useGetRosterMonth,
  useGetSolveProgress,
  useGetSolveResult,
  usePreviewSolve,
  useStartSolve,
  useStopSolve,
} from "@/api/generated/endpoints"
import { Role, type Draft, type DraftChange, type SolvePreview, type SolveProgress } from "@/api/generated/model"
import { FormField } from "@/components/form-field"
import { MONTH_LINK, monthInAddress, MonthNav } from "@/components/month-nav"
import { GridLegend, RosterGrid } from "@/components/roster-grid"
import { SolveResultPanels } from "@/components/solve-result"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { useChosenUnit } from "@/components/unit-picker"
import { plainRefusal, showServerErrors } from "@/lib/server-errors"
import { hospitalTime, monthName } from "@/lib/utils"
import { onlyFor } from "@/session"

const searchSchema = z.object({ month: monthInAddress })

export const Route = createFileRoute("/_signed-in/roster")({
  validateSearch: (search) => searchSchema.parse(search),
  beforeLoad: onlyFor(Role.unit_manager),
  staticData: { title: "Roster" },
  component: RosterPage,
})

/** How often an open page asks how a solve is getting on. Short in a test, so a test sees the page change without waiting. */
const POLL_MS = import.meta.env.MODE === "test" ? 10 : 1500
const LINK = "underline underline-offset-3"

const isRefusal = (error: unknown) => error instanceof ApiError && error.status < 500
const isActive = (solve: SolveProgress) => solve.state === "queued" || solve.state === "running"
const plural = (count: number, one: string, many = `${one}s`) => `${count} ${count === 1 ? one : many}`

function ProgressCard({ unitId, solve: first, onEnded }: { unitId: string; solve: SolveProgress; onEnded: (solve: SolveProgress) => void }) {
  const queryClient = useQueryClient()
  const progress = useGetSolveProgress(unitId, first.id, {
    query: {
      initialData: first,
      // A refusal will not change by asking again, and a page that goes on asking keeps a tab busy for good.
      refetchInterval: (query) => (query.state.data && isActive(query.state.data) && !isRefusal(query.state.error) ? POLL_MS : false),
    },
  })
  const stop = useStopSolve()
  const solve = progress.data ?? first

  // Once: the card stays until the month's next answer takes it away, and the page around it renders meanwhile.
  const told = useRef(false)
  useEffect(() => {
    if (isActive(solve) || told.current) return
    told.current = true
    onEnded(solve)
  }, [solve, onEnded])

  const stopNow = () => stop.mutate({ unitId, solveId: first.id }, {
    onSuccess: (answer) => queryClient.setQueryData(getGetSolveProgressQueryKey(unitId, first.id), answer),
  })

  return (
    <Card role="region" aria-labelledby="solve-progress" data-solve-progress>
      <CardHeader>
        <CardTitle><h3 id="solve-progress" tabIndex={-1} className="outline-none">Solving {monthName(solve.month)}</h3></CardTitle>
        <CardDescription>You can leave this page: the solve carries on, and its draft is here when you come back.</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col items-start gap-3">
        {solve.state === "queued" && (
          <p>{solve.queue_ahead ? `Waiting in the hospital's queue: ${plural(solve.queue_ahead, "solve")} ahead of this one.` : "Next in the hospital's queue."}</p>
        )}
        {solve.state === "running" && (
          <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm tabular-nums">
            <dt className="text-muted-foreground">Searched for</dt>
            <dd>{Math.round(solve.elapsed_seconds)} of {plural(solve.time_limit_seconds, "second")}</dd>
            <dt className="text-muted-foreground">Best cost so far</dt>
            <dd>{solve.best_cost ?? "No roster yet"}</dd>
            <dt className="text-muted-foreground">Improving rosters</dt>
            <dd>{solve.improvements}</dd>
          </dl>
        )}
        {solve.attempts > 1 && <p className="text-sm text-muted-foreground">The first attempt failed, so this is the second: {solve.error}</p>}
        {progress.isError && (
          <p role="alert" className="text-sm text-destructive">
            {isRefusal(progress.error) ? "This solve can no longer be read from here. Reload the page." : "The latest progress could not be read. This page keeps trying."}
          </p>
        )}
        {stop.isError && <p role="alert" className="text-sm text-destructive">{plainRefusal(stop.error) ?? "The solve could not be stopped. Check your connection and try again."}</p>}
        <Button variant="outline" onClick={stopNow} disabled={stop.isPending || solve.stop_requested}>
          {solve.stop_requested ? "Stopping…" : solve.state === "queued" ? "Take out of the queue" : "Stop and keep the best roster"}
        </Button>
      </CardContent>
    </Card>
  )
}

function UnitRulesLink({ children }: { children: string }) {
  return <Link to="/unit-rules" className={LINK}>{children}</Link>
}

function RulesRefused({ detail }: { detail: string }) {
  return (
    <div className="flex flex-col gap-1">
      <p>The solver cannot take the rules as they stand. <UnitRulesLink>Review the unit rules</UnitRulesLink>, or ask the CNO if this names a hospital rule.</p>
      <p className="text-sm text-muted-foreground">It says: {detail}</p>
    </div>
  )
}

function WhyNoDraft({ solve }: { solve: SolveProgress }) {
  if (solve.failure === "refused") return <RulesRefused detail={solve.error} />
  if (solve.state === "failed") {
    return <p role="alert">The solve failed, and the draft is as it was. You can run it again. It says: {solve.error}</p>
  }
  if (solve.state === "cancelled") {
    return <p>The solve you stopped had found no roster yet, so nothing has changed.</p>
  }
  return (
    <>
      <p role="alert">The solver found no roster for this month, so nothing has changed. {solve.message}</p>
      {solve.precheck.length > 0 && <ul className="list-disc ps-5 text-sm">{solve.precheck.map((issue) => <li key={issue}>{issue}</li>)}</ul>}
    </>
  )
}

/** Why the latest solve left no draft of its own. The whole of it is one link away. */
function LastSolve({ solve }: { solve: SolveProgress }) {
  return (
    <div className="flex flex-col gap-1">
      <WhyNoDraft solve={solve} />
      <p><Link to="/solve-history/$solveId" params={{ solveId: solve.id }} className={`text-sm ${LINK}`}>Open this result</Link></p>
    </div>
  )
}

const CHANGE_SAYS: Record<DraftChange["what"], string> = {
  gender: "gender was corrected",
  leave: "leave or dates changed",
  joined: "is now in this month but not in this draft",
  left: "is no longer in this month but still in this draft",
}

function DraftDetails({ unitId, solveId }: { unitId: string; solveId: string }) {
  const result = useGetSolveResult(unitId, solveId)
  if (result.isPending) return <p className="text-sm">Loading the details of this result…</p>
  if (!result.data) return <p role="alert" className="text-sm">The details of this result could not be read. The grid above is still the draft. Reload the page to try again.</p>
  return <SolveResultPanels result={result.data} />
}

function DraftCard({ unitId, draft, label }: { unitId: string; draft: Draft; label: string }) {
  return (
    <section aria-labelledby="draft" className="flex flex-col gap-4">
      <div className="flex flex-col gap-1">
        <h3 id="draft" tabIndex={-1} className="font-medium outline-none">Draft</h3>
        <p className="text-sm text-muted-foreground tabular-nums">
          {draft.restored_at ? `Restored ${hospitalTime(draft.restored_at)} from the solve of ${hospitalTime(draft.solved_at)}.` : `Solved ${hospitalTime(draft.solved_at)}.`} Cost {draft.cost}.
          {draft.stopped_early && " You stopped this solve early, so this is the best roster it had found."}
        </p>
      </div>
      {draft.changes.length > 0 && (
        <div role="alert" className="flex flex-col gap-1 rounded-md border border-destructive/40 p-3 text-sm">
          <p className="font-medium">This draft was solved before these changes:</p>
          <ul className="list-disc ps-5">
            {draft.changes.map((change) => <li key={change.hospital_id + change.what}>{change.full_name || change.hospital_id}: {CHANGE_SAYS[change.what]}</li>)}
          </ul>
          <p>Solve again to take them in. Otherwise, the roster is checked again when you submit it.</p>
        </div>
      )}
      <RosterGrid grid={draft} label={label} />
      <GridLegend grid={draft} />
      <DraftDetails unitId={unitId} solveId={draft.solve_id} />
    </section>
  )
}

function Warnings({ preview }: { preview: SolvePreview }) {
  const { hospital_rules_need_review, unit_rules_need_review, unreviewed_scores, left_out } = preview.warnings
  const items = [
    hospital_rules_need_review && <>The hospital rules are still the seeded defaults, which the CNO has not reviewed.</>,
    unit_rules_need_review && <>The unit rules are still the seeded defaults. <UnitRulesLink>Review them</UnitRulesLink></>,
    unreviewed_scores > 0 && (
      <>{unreviewed_scores === 1 ? "1 nurse's attributes have never been saved, so their score is" : `${unreviewed_scores} nurses' attributes have never been saved, so their scores are`} still the default.{" "}
        <Link to="/rostering-attributes" className={LINK}>Review them</Link></>
    ),
    left_out.length > 0 && <>{left_out.join(", ")} {left_out.length === 1 ? "is" : "are"} left out of this solve: a manager's account deactivated, with no end date on the nurse profile.</>,
  ].filter(Boolean)
  if (items.length === 0) return null
  return (
    <div className="flex flex-col gap-1">
      <h4 className="text-sm font-medium">Worth a look. None of these stops a solve.</h4>
      <ul className="list-disc ps-5 text-sm">{items.map((item, index) => <li key={index}>{item}</li>)}</ul>
    </div>
  )
}

function Precheck({ issues }: { issues: string[] | null }) {
  if (issues === null) return <p className="text-sm">The solver did not answer, so the month could not be checked in advance. A solve started now may fail.</p>
  if (issues.length === 0) return <p className="text-sm">The solver's check found no reason this month could not be solved.</p>
  return (
    <div className="flex flex-col gap-1">
      <h4 className="text-sm font-medium">The solver's check says this month may not be solvable:</h4>
      <ul className="list-disc ps-5 text-sm">{issues.map((issue) => <li key={issue}>{issue}</li>)}</ul>
    </div>
  )
}

function StartForm({ unitId, preview, onStarted, solvingAgain }: { unitId: string; preview: SolvePreview; onStarted: () => void; solvingAgain: boolean }) {
  const start = useStartSolve()
  const schema = z.object({
    time_limit_seconds: z.number("Enter a whole number of seconds.").int("Enter a whole number of seconds.")
      .min(1, "At least 1 second.").max(preview.time_limit_cap, `The System Admin's cap is ${preview.time_limit_cap} seconds.`),
  })
  const form = useForm<z.infer<typeof schema>>({ resolver: zodResolver(schema), defaultValues: { time_limit_seconds: preview.time_limit_default } })
  const submit = form.handleSubmit((data) => start.mutate({ unitId, data: { month: preview.month, ...data } }, {
    onSuccess: onStarted,
    onError: (error) => showServerErrors(form, error, (loc) => String(loc.at(-1))),
  }))
  const refused = start.isError && plainRefusal(start.error)
  return (
    <form onSubmit={submit} noValidate className="flex flex-col items-start gap-3">
      <div className="w-48">
        <FormField label="Time limit (seconds)" type="number" inputMode="numeric" min={1} max={preview.time_limit_cap}
          description={`Up to ${preview.time_limit_cap}.`}
          registration={form.register("time_limit_seconds", { valueAsNumber: true })} error={form.formState.errors.time_limit_seconds} />
      </div>
      {solvingAgain && <p className="text-sm text-muted-foreground">Solving again replaces the draft's grid. The solve history keeps what it replaced.</p>}
      {refused && <p role="alert" className="text-sm text-destructive">{refused}</p>}
      {start.isError && !refused && !form.formState.errors.time_limit_seconds && <p role="alert" className="text-sm text-destructive">The solve could not be started. Check your connection and try again.</p>}
      <Button type="submit" disabled={start.isPending}>{solvingAgain ? "Solve again" : "Start solve"}</Button>
    </form>
  )
}

function PreviewCard({ unitId, month, onStarted, solvingAgain }: { unitId: string; month: string; onStarted: () => void; solvingAgain: boolean }) {
  const preview = usePreviewSolve(unitId, { month })
  const answer = preview.data
  return (
    <Card role="region" aria-labelledby="before-solving">
      <CardHeader>
        <CardTitle><h3 id="before-solving" tabIndex={-1} className="outline-none">What the solver will receive</h3></CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {preview.isPending && <p>Loading…</p>}
        {preview.isError && <p role="alert">This month could not be read. Reload the page to try again.</p>}
        {answer && (
          <>
            <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm tabular-nums">
              <dt className="text-muted-foreground">Nurses</dt>
              <dd>{answer.summary.nurses}</dd>
              <dt className="text-muted-foreground">Days of leave</dt>
              <dd>{answer.summary.leave_days}</dd>
              <dt className="text-muted-foreground">Days before a start date or after an end date</dt>
              <dd>{answer.summary.outside_days}</dd>
              <dt className="text-muted-foreground">Pinned cells</dt>
              <dd>{answer.summary.pins}</dd>
            </dl>
            {answer.rules_refusal ? <RulesRefused detail={answer.rules_refusal} /> : !answer.refusal && <Precheck issues={answer.precheck} />}
            <Warnings preview={answer} />
            {answer.refusal && <p role="alert">{answer.refusal}</p>}
            {!answer.refusal && !answer.rules_refusal && <StartForm unitId={unitId} preview={answer} onStarted={onStarted} solvingAgain={solvingAgain} />}
          </>
        )}
      </CardContent>
    </Card>
  )
}

function UnitRoster({ unit, month: inAddress }: { unit: { id: string; name: string }; month: string | undefined }) {
  const queryClient = useQueryClient()
  const roster = useGetRosterMonth(unit.id, inAddress ? { month: inAddress } : undefined, { query: { placeholderData: keepPreviousData } })
  const [said, setSaid] = useState("")
  const answer = roster.data
  const refresh = () => Promise.all([
    queryClient.invalidateQueries({ queryKey: getGetRosterMonthQueryKey(unit.id) }),
    queryClient.invalidateQueries({ queryKey: getPreviewSolveQueryKey(unit.id) }),
  ])
  // Focus was on Start or on Stop, and each goes when the page changes, so it follows to what took their place.
  const focusNext = useRef<string | null>(null)
  useEffect(() => {
    if (focusNext.current && document.getElementById(focusNext.current)) {
      document.getElementById(focusNext.current)?.focus()
      focusNext.current = null
    }
  })
  const started = () => {
    setSaid("")
    focusNext.current = "solve-progress"
    void refresh()
  }
  const ended = (solve: SolveProgress) => {
    setSaid(solve.found_roster
      ? `The solve ${solve.state === "cancelled" ? "stopped" : "finished"} with a cost of ${solve.best_cost}, and the draft is replaced.`
      : "The solve ended with no new draft.")
    // Only if focus was on Stop, which is going, or nowhere: a solve can end minutes later, with the manager elsewhere on the page.
    const onTheCard = document.activeElement?.closest("[data-solve-progress]")
    if (onTheCard || document.activeElement === document.body) focusNext.current = solve.found_roster ? "draft" : "before-solving"
    void refresh()
  }
  const active = answer?.active_solve
  return (
    <>
      {roster.isPending && <p>Loading…</p>}
      {roster.isError && <p role="alert">This month's roster could not be read. Reload the page to try again.</p>}
      {/* Always rendered, because a live region mounted with its text may never be read out. */}
      <p role="status" className="text-sm text-muted-foreground empty:sr-only">{said}</p>
      {answer && (
        <>
          <MonthNav month={answer.month} link={(month, label) => <Link to="/roster" search={{ month }} className={MONTH_LINK} onClick={() => setSaid("")}>{label}</Link>} />
          <p><Link to="/solve-history" search={{ month: answer.month }} className={`text-sm ${LINK}`}>Solve history of {monthName(answer.month)}</Link></p>
          {active && <ProgressCard key={active.id} unitId={unit.id} solve={active} onEnded={ended} />}
          {!active && answer.last_solve && <LastSolve solve={answer.last_solve} />}
          {answer.draft && <DraftCard unitId={unit.id} draft={answer.draft} label={`Draft of ${unit.name}, ${monthName(answer.month)}`} />}
          {!answer.draft && !active && !answer.last_solve && <p>No draft yet for {monthName(answer.month)}.</p>}
          {!active && <PreviewCard key={answer.month} unitId={unit.id} month={answer.month} onStarted={started} solvingAgain={!!answer.draft} />}
        </>
      )}
    </>
  )
}

function RosterPage() {
  const { user } = useRouteContext({ from: "/_signed-in" })
  const { month } = Route.useSearch()
  const { units, chosen } = useChosenUnit(user, undefined)
  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-4">
      <h1 className="text-xl font-medium">{chosen ? `Roster of ${chosen.name}` : "Roster"}</h1>
      <p className="text-muted-foreground">Solve a month to get its draft. Each solve replaces the draft's grid. Only you see a draft.</p>
      {units.isPending && <p>Loading…</p>}
      {units.isError && <p role="alert">Your unit could not be read. Reload the page to try again.</p>}
      {units.data && !chosen && <p>No unit is assigned to you yet. The CNO assigns each unit its manager.</p>}
      {chosen && <UnitRoster key={chosen.id} unit={chosen} month={month} />}
    </div>
  )
}
