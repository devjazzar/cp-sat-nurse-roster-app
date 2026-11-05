import { zodResolver } from "@hookform/resolvers/zod"
import { useQueryClient } from "@tanstack/react-query"
import { createFileRoute, Link, useRouteContext } from "@tanstack/react-router"
import { useEffect, useRef, useState } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"

import {
  getListPublicHolidaysQueryKey,
  getListRamadanMonthsQueryKey,
  useCreatePublicHoliday,
  useDeletePublicHoliday,
  useFixRamadanMonth,
  useListPublicHolidays,
  useListRamadanMonths,
  useUnfixRamadanMonth,
  useUpdatePublicHoliday,
} from "@/api/generated/endpoints"
import { Role, RamadanMonthSource, type PublicHolidayBody, type PublicHolidaySchema, type RamadanMonth } from "@/api/generated/model"
import {
  createPublicHolidayBodyNameMax as NAME_MAX,
  listRamadanMonthsQueryYearMax as LAST_YEAR,
  listRamadanMonthsQueryYearMin as FIRST_YEAR,
} from "@/api/generated/zod"
import { CHECKBOX, FormField } from "@/components/form-field"
import { ConfirmDialog } from "@/components/confirm-dialog"
import { Badge } from "@/components/ui/badge"
import { Button, buttonVariants } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { FieldError, FieldGroup, FieldLegend, FieldSet } from "@/components/ui/field"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { serverErrors, showServerErrors } from "@/lib/server-errors"
import { useEditing } from "@/lib/use-editing"
import { asDate, monthName, scrollableRegion } from "@/lib/utils"

/** A hand-edited year is dropped rather than sent: the API would refuse it and the page could only say "reload". */
const searchSchema = z.object({ year: z.number().int().min(FIRST_YEAR).max(LAST_YEAR).optional().catch(undefined) })

/** Open to every role, which may all read the catalogue. Only the CNO gets the forms. */
export const Route = createFileRoute("/_signed-in/holidays")({
  validateSearch: (search) => searchSchema.parse(search),
  staticData: { title: "Holidays and Ramadan" },
  component: HolidaysPage,
})

const longDate = new Intl.DateTimeFormat("en-GB", { weekday: "long", day: "numeric", month: "long", year: "numeric", timeZone: "UTC" })
const dayOf = (iso: string) => Number(iso.slice(8))

/** "1 to 19, 25" for days of one month, in order. */
function dayRanges(dates: string[]): string {
  const runs: [number, number][] = []
  for (const day of dates.map(dayOf)) {
    const last = runs.at(-1)
    if (last && day === last[1] + 1) last[1] = day
    else runs.push([day, day])
  }
  return runs.map(([first, last]) => (first === last ? `${first}` : `${first} to ${last}`)).join(", ") || "None"
}

const isOneRun = (dates: string[]) => dates.length > 0 && dates.every((day, index) => index === 0 || dayOf(day) === dayOf(dates[index - 1]) + 1)

// Unlike the shifts' table, a row's actions here do not stay in view on a narrow screen: two buttons
// would cover the dates, which are what the row is for.

// ---- public holidays ------------------------------------------------------------------------------
function HolidayForm({ year, row, onDone, onCancel }: { year: number; row: PublicHolidaySchema | null; onDone: (message: string) => void; onCancel: () => void }) {
  const queryClient = useQueryClient()
  const create = useCreatePublicHoliday()
  const update = useUpdatePublicHoliday()
  const mutation = row ? update : create
  const schema = z.object({
    date: z.iso.date("Enter a date.").refine((date) => date.startsWith(`${year}-`), `This is not in ${year}. Go to that year to enter it.`),
    name: z.string().trim().min(1, "Enter a name.").max(NAME_MAX, `At most ${NAME_MAX} characters.`),
  })
  const form = useForm<PublicHolidayBody>({ resolver: zodResolver(schema), defaultValues: row ?? { date: "", name: "" } })
  const { errors } = form.formState

  useEffect(() => {
    if (row) form.setFocus("date")
  }, [row, form])

  const saved = (message: string) => {
    void queryClient.invalidateQueries({ queryKey: getListPublicHolidaysQueryKey({ year }) })
    onDone(message)
  }
  const refused = (error: unknown) => showServerErrors(form, error)

  const submit = form.handleSubmit((data) => {
    if (row) {
      update.mutate({ holidayId: row.id, data }, { onSuccess: (next) => saved(`${next.name} is saved.`), onError: refused })
    } else {
      create.mutate({ data }, {
        onSuccess: (next) => {
          form.reset({ date: "", name: "" })
          saved(`${next.name} is added.`)
        },
        onError: refused,
      })
    }
  })
  const unexpected = mutation.isError && serverErrors(mutation.error).length === 0

  return (
    <form onSubmit={submit} noValidate>
      <FieldGroup>
        <FormField label="Date" type="date" min={`${year}-01-01`} max={`${year}-12-31`} registration={form.register("date")} error={errors.date} />
        <FormField label="Name" autoComplete="off" registration={form.register("name")} error={errors.name} />
        {unexpected && <p role="alert" className="text-sm text-destructive">The holiday could not be saved. Check your connection and try again.</p>}
        <div className="flex gap-2">
          <Button type="submit" disabled={mutation.isPending}>{row ? "Save holiday" : "Add holiday"}</Button>
          {row && <Button type="button" variant="outline" onClick={onCancel}>Cancel</Button>}
        </div>
      </FieldGroup>
    </form>
  )
}

function Holidays({ year, mayChange }: { year: number; mayChange: boolean }) {
  const queryClient = useQueryClient()
  const holidays = useListPublicHolidays({ year })
  const remove = useDeletePublicHoliday()
  const { editing, start, finish, drop } = useEditing<PublicHolidaySchema>()
  const [done, setDone] = useState("")
  const [asked, setAsked] = useState<PublicHolidaySchema | null>(null)
  const focusAfter = useRef<string | null>(null)

  function removeHoliday(row: PublicHolidaySchema) {
    remove.mutate({ holidayId: row.id }, {
      onSuccess: () => {
        void queryClient.invalidateQueries({ queryKey: getListPublicHolidaysQueryKey({ year }) })
        setDone(`${row.name} is removed.`)
        if (editing?.id === row.id) drop()
        focusAfter.current = "field-date" // Where the next holiday would be entered.
        setAsked(null)
      },
    })
  }

  return (
    <section className="flex flex-col gap-4">
      <h2 className="text-lg font-medium">Public holidays in {year}</h2>
      {holidays.isPending && <p>Loading…</p>}
      {holidays.isError && <p role="alert">The public holidays could not be read. Reload the page to try again.</p>}
      <p role="status" className="text-sm text-muted-foreground empty:sr-only">{done}</p>
      {holidays.data && (
        <Card>
          <CardContent>
            {holidays.data.length === 0
              ? <p className="text-sm text-muted-foreground">No public holidays are entered for {year}.</p>
              : (
                <Table container={mayChange ? undefined : scrollableRegion(`Public holidays in ${year}`)}>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Date</TableHead>
                      <TableHead>Name</TableHead>
                      {mayChange && <TableHead><span className="sr-only">Actions</span></TableHead>}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {holidays.data.map((row) => (
                      <TableRow key={row.id}>
                        <TableCell className="tabular-nums">{longDate.format(asDate(row.date))}</TableCell>
                        <TableCell>{row.name}</TableCell>
                        {mayChange && (
                          <TableCell>
                            <div className="flex justify-end gap-2">
                              <Button variant="outline" size="sm" aria-label={`Edit ${row.name}`}
                                onClick={(event) => { setDone(""); start(row, event.currentTarget) }}>
                                Edit
                              </Button>
                              <Button variant="outline" size="sm" aria-label={`Remove ${row.name}`}
                                onClick={() => { setDone(""); remove.reset(); focusAfter.current = null; setAsked(row) }}>
                                Remove
                              </Button>
                            </div>
                          </TableCell>
                        )}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
          </CardContent>
        </Card>
      )}
      {mayChange && holidays.data && (
        <Card className="max-w-xl">
          <CardHeader><CardTitle><h3>{editing ? `Edit ${editing.name}` : "Add a public holiday"}</h3></CardTitle></CardHeader>
          <CardContent>
            <HolidayForm key={`${year} ${editing?.id ?? "new"}`} year={year} row={editing} onCancel={finish}
              onDone={(message) => { setDone(message); finish() }} />
          </CardContent>
        </Card>
      )}
      <ConfirmDialog pending={remove.isPending} failed={remove.isError} focusAfter={focusAfter}
        question={asked && {
          title: `Remove ${asked.name}?`,
          body: `${longDate.format(asDate(asked.date))} stops counting as a public holiday in solves from now on.`,
          confirm: "Remove holiday",
        }}
        onCancel={() => setAsked(null)} onConfirm={() => { if (asked) removeHoliday(asked) }} />
    </section>
  )
}

// ---- Ramadan dates --------------------------------------------------------------------------------
type RamadanFields = { mode: "range" | "list"; first: string; last: string; days: string[] }

function RamadanForm({ state, onDone, onCancel }: { state: RamadanMonth; onDone: (message: string) => void; onCancel: () => void }) {
  const queryClient = useQueryClient()
  const fix = useFixRamadanMonth()
  const { month } = state
  const name = monthName(month)
  const [year, number] = month.split("-").map(Number)
  const lastDay = new Date(Date.UTC(year, number, 0)).getUTCDate()
  const allDays = Array.from({ length: lastDay }, (_, index) => `${month}-${String(index + 1).padStart(2, "0")}`)
  const heading = useRef<HTMLHeadingElement>(null)

  const schema = z.object({ mode: z.enum(["range", "list"]), first: z.string(), last: z.string(), days: z.array(z.string()) })
    .superRefine((fields, context) => {
      if (fields.mode !== "range") return
      if (!allDays.includes(fields.first)) context.addIssue({ code: "custom", path: ["first"], message: `Enter a day in ${name}.` })
      if (!allDays.includes(fields.last)) context.addIssue({ code: "custom", path: ["last"], message: `Enter a day in ${name}.` })
      else if (fields.first && fields.last < fields.first) context.addIssue({ code: "custom", path: ["last"], message: "This is before the first day." })
    })
  const form = useForm<RamadanFields>({
    resolver: zodResolver(schema),
    defaultValues: {
      // A month fixed to no days has nothing a range could show.
      mode: isOneRun(state.dates) || state.source === RamadanMonthSource.derived ? "range" : "list",
      first: state.dates[0] ?? "",
      last: state.dates.at(-1) ?? "",
      days: state.dates,
    },
  })
  const { errors } = form.formState
  const mode = form.watch("mode")

  useEffect(() => heading.current?.focus(), [])

  const submit = form.handleSubmit((fields) =>
    fix.mutate(
      { month, data: fields.mode === "range" ? { first: fields.first, last: fields.last } : { dates: fields.days } },
      {
        onSuccess: () => {
          void queryClient.invalidateQueries({ queryKey: getListRamadanMonthsQueryKey({ year }) })
          onDone(`The Ramadan dates of ${name} are fixed.`)
        },
        onError: (error) => showServerErrors(form, error, ([field]) => (field === "dates" ? "days" : String(field))),
      },
    ),
  )
  const unexpected = fix.isError && serverErrors(fix.error).length === 0

  return (
    <Card className="max-w-xl">
      <CardHeader>
        <CardTitle><h3 ref={heading} tabIndex={-1} className="outline-none">Fix the Ramadan dates of {name}</h3></CardTitle>
        <CardDescription>The dates from the moon sighting. The calendar says: {dayRanges(state.derived_dates)}.</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={submit} noValidate>
          <FieldGroup>
            <FieldSet>
              <FieldLegend variant="label">Enter them as</FieldLegend>
              <div className="flex flex-wrap gap-x-4 gap-y-2">
                <label className="flex items-center gap-2 text-sm">
                  <input type="radio" value="range" className={CHECKBOX} {...form.register("mode")} /> A range
                </label>
                <label className="flex items-center gap-2 text-sm">
                  <input type="radio" value="list" className={CHECKBOX} {...form.register("mode")} /> A list of days
                </label>
              </div>
            </FieldSet>
            {mode === "range" ? (
              <div className="grid gap-4 sm:grid-cols-2">
                <FormField label="First day" type="date" min={allDays[0]} max={allDays.at(-1)} registration={form.register("first")} error={errors.first} />
                <FormField label="Last day" type="date" min={allDays[0]} max={allDays.at(-1)} registration={form.register("last")} error={errors.last} />
              </div>
            ) : (
              <FieldSet aria-describedby={errors.days ? "ramadan-days-error" : "ramadan-days-hint"}>
                <FieldLegend variant="label">Days of {name}</FieldLegend>
                <div className="grid grid-cols-7 gap-2">
                  {allDays.map((day) => (
                    <label key={day} className="flex items-center gap-1 text-sm tabular-nums">
                      <input type="checkbox" value={day} className={CHECKBOX} {...form.register("days")} /> {dayOf(day)}
                    </label>
                  ))}
                </div>
                <p id="ramadan-days-hint" className="text-sm text-muted-foreground">With none ticked, this month has no Ramadan days.</p>
                <FieldError id="ramadan-days-error" role={undefined} errors={errors.days ? [errors.days as { message?: string }] : undefined} />
              </FieldSet>
            )}
            {unexpected && <p role="alert" className="text-sm text-destructive">The dates could not be saved. Check your connection and try again.</p>}
            <div className="flex gap-2">
              <Button type="submit" disabled={fix.isPending}>Fix dates</Button>
              <Button type="button" variant="outline" onClick={onCancel}>Cancel</Button>
            </div>
          </FieldGroup>
        </form>
      </CardContent>
    </Card>
  )
}

function Ramadan({ year, mayChange }: { year: number; mayChange: boolean }) {
  const queryClient = useQueryClient()
  const months = useListRamadanMonths({ year })
  const unfix = useUnfixRamadanMonth()
  const { editing, start, finish, drop } = useEditing<RamadanMonth>()
  const [done, setDone] = useState("")
  const [asked, setAsked] = useState<RamadanMonth | null>(null)
  const focusAfter = useRef<string | null>(null)

  function backToCalendar(state: RamadanMonth) {
    unfix.mutate({ month: state.month }, {
      onSuccess: () => {
        void queryClient.invalidateQueries({ queryKey: getListRamadanMonthsQueryKey({ year }) })
        setDone(`${monthName(state.month)} follows the calendar again.`)
        if (editing?.month === state.month) drop()
        focusAfter.current = `fix-${state.month}` // The button that opened the question goes with the fixed dates.
        setAsked(null)
      },
    })
  }

  return (
    <section className="flex flex-col gap-4">
      <h2 className="text-lg font-medium">Ramadan dates in {year}</h2>
      <p className="text-sm text-muted-foreground">
        The days a Ramadan-reduced nurse owes fewer hours. Each month follows the Umm al-Qura calendar unless the CNO fixes its dates after the moon sighting.
      </p>
      {months.isPending && <p>Loading…</p>}
      {months.isError && <p role="alert">The Ramadan dates could not be read. Reload the page to try again.</p>}
      <p role="status" className="text-sm text-muted-foreground empty:sr-only">{done}</p>
      {months.data && (
        <Card>
          <CardContent>
            <Table container={mayChange ? undefined : scrollableRegion(`Ramadan dates in ${year}`)}>
              <TableHeader>
                <TableRow>
                  <TableHead>Month</TableHead>
                  <TableHead>Ramadan days</TableHead>
                  <TableHead>Set by</TableHead>
                  {mayChange && <TableHead><span className="sr-only">Actions</span></TableHead>}
                </TableRow>
              </TableHeader>
              <TableBody>
                {months.data.map((state) => {
                  const fixed = state.source === RamadanMonthSource.fixed
                  const name = monthName(state.month)
                  return (
                    <TableRow key={state.month}>
                      <TableCell>{name}</TableCell>
                      <TableCell className="tabular-nums">
                        {dayRanges(state.dates)}
                        {fixed && <p className="text-xs text-muted-foreground">The calendar says: {dayRanges(state.derived_dates)}</p>}
                      </TableCell>
                      <TableCell><Badge variant={fixed ? "secondary" : "outline"}>{fixed ? "The CNO" : "The calendar"}</Badge></TableCell>
                      {mayChange && (
                        <TableCell>
                          <div className="flex justify-end gap-2">
                            <Button id={`fix-${state.month}`} variant="outline" size="sm" aria-label={`Fix the dates of ${name}`}
                              onClick={(event) => { setDone(""); start(state, event.currentTarget) }}>
                              Fix dates
                            </Button>
                            {fixed && (
                              <Button variant="outline" size="sm" aria-label={`Use the calendar for ${name}`}
                                onClick={() => { setDone(""); unfix.reset(); focusAfter.current = null; setAsked(state) }}>
                                Use the calendar
                              </Button>
                            )}
                          </div>
                        </TableCell>
                      )}
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
      {mayChange && editing && (
        <RamadanForm key={editing.month} state={editing} onCancel={finish}
          onDone={(message) => { setDone(message); finish() }} />
      )}
      <ConfirmDialog pending={unfix.isPending} failed={unfix.isError} focusAfter={focusAfter}
        question={asked && {
          title: `Use the calendar for ${monthName(asked.month)}?`,
          body: `The fixed dates (${dayRanges(asked.dates)}) are dropped, and the month's Ramadan days become ${dayRanges(asked.derived_dates)}.`,
          confirm: "Use the calendar",
        }}
        onCancel={() => setAsked(null)} onConfirm={() => { if (asked) backToCalendar(asked) }} />
    </section>
  )
}

function HolidaysPage() {
  const { user } = useRouteContext({ from: "/_signed-in" })
  const { year: chosen } = Route.useSearch()
  const year = chosen ?? new Date().getFullYear()
  const mayChange = user.role === Role.cno
  const yearLink = buttonVariants({ variant: "outline", size: "sm" })

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6">
      <div className="flex flex-col gap-2">
        <h1 className="text-xl font-medium">Holidays and Ramadan</h1>
        <p className="text-muted-foreground">
          The days every unit's hours are worked out from.
          {!mayChange && " Only the CNO can change these."}
        </p>
        <nav aria-label="Year" className="flex items-center gap-2">
          {year > FIRST_YEAR && <Link to="/holidays" search={{ year: year - 1 }} className={yearLink}>{year - 1}</Link>}
          <span aria-current="page" className="px-2 font-medium tabular-nums">{year}</span>
          {year < LAST_YEAR && <Link to="/holidays" search={{ year: year + 1 }} className={yearLink}>{year + 1}</Link>}
        </nav>
      </div>
      <Holidays key={`holidays ${year}`} year={year} mayChange={mayChange} />
      <Ramadan key={`ramadan ${year}`} year={year} mayChange={mayChange} />
    </div>
  )
}
