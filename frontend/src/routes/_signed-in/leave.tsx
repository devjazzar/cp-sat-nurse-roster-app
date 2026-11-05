import { zodResolver } from "@hookform/resolvers/zod"
import { keepPreviousData, useQueryClient } from "@tanstack/react-query"
import { createFileRoute, Link, useNavigate, useRouteContext } from "@tanstack/react-router"
import { useEffect, useRef, useState } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"

import { ApiError } from "@/api/fetcher"
import {
  getListUnitLeaveQueryKey,
  useChangeLeave,
  useListLeaveTypes,
  useListUnitLeave,
  useRecordLeave,
  useRemoveLeave,
} from "@/api/generated/endpoints"
import { Role, type LeaveNurse, type LeaveRun, type UnitLeaveMonth } from "@/api/generated/model"
import { ConfirmDialog } from "@/components/confirm-dialog"
import { FormField, SelectField } from "@/components/form-field"
import { MONTH_LINK, monthInAddress, MonthNav } from "@/components/month-nav"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field"
import { NativeSelect, NativeSelectOption } from "@/components/ui/native-select"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { useChosenUnit } from "@/components/unit-picker"
import { serverErrors, showServerErrors } from "@/lib/server-errors"
import { useEditing } from "@/lib/use-editing"
import { dayRange, monthName } from "@/lib/utils"
import { onlyFor } from "@/session"

const searchSchema = z.object({
  month: monthInAddress,
  nurse: z.string().optional().catch(undefined),
})

export const Route = createFileRoute("/_signed-in/leave")({
  validateSearch: (search) => searchSchema.parse(search),
  beforeLoad: onlyFor(Role.unit_manager),
  staticData: { title: "Leave" },
  component: LeavePage,
})

const RECORD_BUTTON = "record-leave"

const formSchema = z.object({
  nurse_id: z.string().min(1, "Choose a nurse."),
  leave_type_id: z.string().min(1, "Choose a leave type."),
  first: z.iso.date("Enter the first day."),
  last: z.iso.date("Enter a date, or leave this empty for one day.").or(z.literal("")),
})
type FormValues = z.infer<typeof formSchema>

/** What a refusal that is not about a field says, when the answer says anything: 403 and 409 explain themselves. */
function plainRefusal(error: unknown): string | undefined {
  if (!(error instanceof ApiError) || error.status === 422) return undefined
  const detail = (error.body as { detail?: unknown } | undefined)?.detail
  return typeof detail === "string" ? detail : undefined
}

function LeaveForm({ unitId, nurses, run, defaultNurse, onCancel, onDone }: {
  unitId: string
  nurses: LeaveNurse[]
  /** The leave being changed, or nothing for new leave. */
  run: LeaveRun | null
  defaultNurse: string | undefined
  onCancel: () => void
  onDone: (message: string, first: string) => void
}) {
  const queryClient = useQueryClient()
  const types = useListLeaveTypes()
  const record = useRecordLeave()
  const change = useChangeLeave()
  const mutation = run ? change : record
  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      nurse_id: run?.nurse.id ?? defaultNurse ?? "",
      leave_type_id: run?.leave_type.id ?? "",
      first: run?.first ?? "",
      last: run && run.last !== run.first ? run.last : "",
    },
  })
  const { errors } = form.formState
  // Only an active type may be chosen, but leave of a type since retired may keep it.
  const choices = (types.data ?? []).filter((type) => type.active || type.id === run?.leave_type.id)

  useEffect(() => { form.setFocus(run ? "leave_type_id" : "nurse_id") }, [form, run])
  // The select has no options until the types arrive, so a value set before then would not show.
  useEffect(() => { if (run && types.data) form.setValue("leave_type_id", run.leave_type.id) }, [form, run, types.data])

  const submit = form.handleSubmit(({ nurse_id, leave_type_id, first, last }) => {
    const dates = { leave_type_id, first, last: last || first }
    const name = run?.nurse.full_name ?? nurses.find((nurse) => nurse.id === nurse_id)?.full_name
    const callbacks = {
      onSuccess: () => {
        void queryClient.invalidateQueries({ queryKey: getListUnitLeaveQueryKey(unitId) })
        onDone(`The leave of ${name} is saved: ${dayRange(first, last || first)}.`, first)
      },
      onError: (error: unknown) => showServerErrors(form, error),
    }
    if (run) change.mutate({ unitId, data: { ...dates, leave_ids: run.leave_ids } }, callbacks)
    else record.mutate({ unitId, data: { ...dates, nurse_id } }, callbacks)
  })

  const refused = mutation.isError && serverErrors(mutation.error).length === 0
  return (
    <form onSubmit={submit} noValidate className="flex flex-col gap-4">
      <FieldGroup>
        {!run && (
          <SelectField label="Nurse" registration={form.register("nurse_id")} error={errors.nurse_id}>
            <NativeSelectOption value="">Choose a nurse</NativeSelectOption>
            {nurses.map((nurse) => <NativeSelectOption key={nurse.id} value={nurse.id}>{nurse.full_name}</NativeSelectOption>)}
          </SelectField>
        )}
        <SelectField label="Leave type" registration={form.register("leave_type_id")} error={errors.leave_type_id}
          description={types.isError ? "The leave types could not be read. Reload the page to try again." : undefined}>
          <NativeSelectOption value="">Choose a type</NativeSelectOption>
          {choices.map((type) => <NativeSelectOption key={type.id} value={type.id}>{type.active ? type.name : `${type.name} (retired)`}</NativeSelectOption>)}
        </SelectField>
        <FormField label="First day" type="date" registration={form.register("first")} error={errors.first} />
        <FormField label="Last day" type="date" description="Leave this empty for one day." registration={form.register("last")} error={errors.last} />
      </FieldGroup>
      {refused && <p role="alert" className="text-sm text-destructive">{plainRefusal(mutation.error) ?? "That did not work. Check your connection and try again."}</p>}
      <div className="flex gap-2">
        <Button type="submit" disabled={mutation.isPending}>Save</Button>
        <Button type="button" variant="outline" onClick={onCancel}>Cancel</Button>
      </div>
    </form>
  )
}

// A row's actions do not stay in view on a narrow screen, as on the holidays page: two buttons would cover the dates. Like
// the other lists, this one has not moved to TanStack Table (ADR 0008), a breach tickets 07 and 09 recorded.
function LeaveTable({ runs, showNurse, month, onChange, onRemove }: {
  runs: LeaveRun[]
  showNurse: boolean
  month: string
  onChange: (run: LeaveRun, button: HTMLElement) => void
  onRemove: (run: LeaveRun) => void
}) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          {showNurse && <TableHead>Nurse</TableHead>}
          <TableHead>Dates</TableHead>
          <TableHead>Days</TableHead>
          <TableHead>Type</TableHead>
          <TableHead><span className="sr-only">Actions</span></TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {runs.map((run) => {
          const what = `leave of ${run.nurse.full_name}, ${dayRange(run.first, run.last)}`
          return (
            <TableRow key={run.leave_ids[0]}>
              {showNurse && (
                <TableCell>
                  <Link to="/leave" search={{ month, nurse: run.nurse.id }} className="underline underline-offset-3">{run.nurse.full_name}</Link>
                </TableCell>
              )}
              <TableCell>
                <div className="flex flex-col items-start gap-1">
                  <span className="tabular-nums">{dayRange(run.first, run.last)}</span>
                  {run.outside_dates && <Badge variant="outline">Outside their dates</Badge>}
                </div>
              </TableCell>
              <TableCell className="tabular-nums">{run.days}</TableCell>
              <TableCell>{run.leave_type.name}</TableCell>
              <TableCell>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" aria-label={`Change ${what}`} onClick={(event) => onChange(run, event.currentTarget)}>Change</Button>
                  <Button variant="outline" size="sm" aria-label={`Remove ${what}`} onClick={() => onRemove(run)}>Remove</Button>
                </div>
              </TableCell>
            </TableRow>
          )
        })}
      </TableBody>
    </Table>
  )
}

type Panel = { run: LeaveRun | null }

function UnitLeave({ unit, month: inAddress, nurseId }: { unit: { id: string; name: string }; month: string | undefined; nurseId: string | undefined }) {
  const queryClient = useQueryClient()
  const navigate = useNavigate({ from: Route.fullPath })
  const leave = useListUnitLeave(unit.id, inAddress ? { month: inAddress } : undefined, { query: { placeholderData: keepPreviousData } })
  const remove = useRemoveLeave()
  const { editing, start, finish, drop } = useEditing<Panel>()
  const [removing, setRemoving] = useState<LeaveRun | null>(null)
  const [done, setDone] = useState("")
  const focusAfter = useRef<string | null>(null)

  const answer: UnitLeaveMonth | undefined = leave.data
  const chosenNurse = answer?.nurses.find((nurse) => nurse.id === nurseId)
  const runs = (answer?.runs ?? []).filter((run) => !chosenNurse || run.nurse.id === chosenNurse.id)
  const days = runs.reduce((total, run) => total + run.days, 0)

  const confirmRemoval = () => {
    if (!removing) return
    const { full_name } = removing.nurse
    const when = dayRange(removing.first, removing.last)
    remove.mutate({ unitId: unit.id, data: { leave_ids: removing.leave_ids } }, {
      onSuccess: () => {
        void queryClient.invalidateQueries({ queryKey: getListUnitLeaveQueryKey(unit.id) })
        focusAfter.current = RECORD_BUTTON
        setRemoving(null)
        setDone(`The leave of ${full_name} is removed: ${when}.`)
      },
    })
  }

  return (
    <>
      {leave.isPending && <p>Loading…</p>}
      {leave.isError && <p role="alert">The leave could not be read. Reload the page to try again.</p>}
      {/* Always rendered, because a live region mounted with its text may never be read out. */}
      <p role="status" className="text-sm text-muted-foreground empty:sr-only">{done}</p>
      {answer && (
        <>
          <MonthNav month={answer.month} link={(month, label) => <Link to="/leave" search={{ month, nurse: nurseId }} className={MONTH_LINK}>{label}</Link>} />
          <div className="flex flex-wrap items-end gap-3">
            <Field className="max-w-xs">
              <FieldLabel htmlFor="chosen-nurse">Show</FieldLabel>
              <NativeSelect id="chosen-nurse" value={chosenNurse?.id ?? ""}
                onChange={(event) => void navigate({ search: { month: answer.month, nurse: event.target.value || undefined } })}>
                <NativeSelectOption value="">Everyone</NativeSelectOption>
                {answer.nurses.map((nurse) => <NativeSelectOption key={nurse.id} value={nurse.id}>{nurse.full_name}</NativeSelectOption>)}
              </NativeSelect>
            </Field>
            <Button id={RECORD_BUTTON} onClick={(event) => { setDone(""); remove.reset(); start({ run: null }, event.currentTarget) }}>Record leave</Button>
          </div>
          {editing && (
            <Card className="max-w-xl">
              <CardHeader>
                <CardTitle><h3>{editing.run ? `Change leave of ${editing.run.nurse.full_name}` : "Record leave"}</h3></CardTitle>
                <CardDescription>Every day in between counts. Only you and the nurse can see the type.</CardDescription>
              </CardHeader>
              <CardContent>
                <LeaveForm key={editing.run?.leave_ids[0] ?? "new"} unitId={unit.id} nurses={answer.nurses} run={editing.run}
                  defaultNurse={chosenNurse?.id} onCancel={finish}
                  onDone={(message, first) => {
                    setDone(message)
                    if (editing.run) {
                      // The row and its button may be gone, so focus waits on the button that stays.
                      drop()
                      document.getElementById(RECORD_BUTTON)?.focus()
                    } else finish()
                    const saved = first.slice(0, 7)
                    if (saved !== answer.month) void navigate({ search: { month: saved, nurse: nurseId } })
                  }} />
              </CardContent>
            </Card>
          )}
          {nurseId && !chosenNurse && (
            <p>The nurse you chose is not in {unit.name} in {monthName(answer.month)}, so this shows everyone.</p>
          )}
          {chosenNurse && (
            <p>{chosenNurse.full_name} has {days === 1 ? "1 day" : `${days} days`} of leave in {monthName(answer.month)}.</p>
          )}
          {!chosenNurse && runs.length === 0 && (
            <p>{answer.nurses.length === 0 ? `${unit.name} has no nurses in ${monthName(answer.month)}.` : `No leave is recorded in ${monthName(answer.month)}.`}</p>
          )}
          {runs.length > 0 && (
            <Card>
              <CardContent>
                <LeaveTable runs={runs} showNurse={!chosenNurse} month={answer.month}
                  onChange={(run, button) => { setDone(""); start({ run }, button) }}
                  onRemove={(run) => { setDone(""); remove.reset(); focusAfter.current = null; setRemoving(run) }} />
              </CardContent>
            </Card>
          )}
          {runs.some((run) => run.outside_dates) && (
            <p className="text-sm text-muted-foreground">A correction to the nurse's start or end date left the days marked Outside their dates beyond them, where they count for nothing. Remove them unless the date is corrected back.</p>
          )}
        </>
      )}
      <ConfirmDialog
        question={removing && {
          title: `Remove this leave of ${removing.nurse.full_name}?`,
          body: `${dayRange(removing.first, removing.last)}, ${removing.leave_type.name}. These days count as ordinary days again.`,
          confirm: "Remove leave",
        }}
        pending={remove.isPending} failed={remove.isError} failure={plainRefusal(remove.error)} focusAfter={focusAfter}
        onConfirm={confirmRemoval} onCancel={() => setRemoving(null)} />
    </>
  )
}

function LeavePage() {
  const { user } = useRouteContext({ from: "/_signed-in" })
  const { month, nurse } = Route.useSearch()
  const { units, chosen } = useChosenUnit(user, undefined)

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-4">
      <h1 className="text-xl font-medium">{chosen ? `Leave in ${chosen.name}` : "Leave"}</h1>
      <p className="text-muted-foreground">
        The leave of your unit's nurses, month by month. A month in another unit is that unit's manager's. Only you and the nurse can see a leave's type: colleagues see a day off.
      </p>
      {units.isPending && <p>Loading…</p>}
      {units.isError && <p role="alert">Your unit could not be read. Reload the page to try again.</p>}
      {units.data && !chosen && (
        <p>
          No unit is assigned to you yet. The CNO assigns each unit its manager. If you are on a roster yourself, your own leave is under{" "}
          <Link to="/my-leave" className="underline underline-offset-3">My leave</Link>.
        </p>
      )}
      {chosen && <UnitLeave unit={chosen} month={month} nurseId={nurse} />}
    </div>
  )
}
