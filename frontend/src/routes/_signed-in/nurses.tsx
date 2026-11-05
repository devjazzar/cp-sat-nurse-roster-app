import { zodResolver } from "@hookform/resolvers/zod"
import { useQueryClient } from "@tanstack/react-query"
import { createFileRoute, useNavigate, useRouteContext } from "@tanstack/react-router"
import { useEffect, useMemo, useState } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"

import {
  getListManagersToPlaceQueryKey,
  getListNursesQueryKey,
  useCorrectNurseDetails,
  useCreateNurse,
  useGiveManagerNurseProfile,
  useListManagersToPlace,
  useListNurses,
  useListUnits,
  useResetNursePassword,
  useSetNurseEndDate,
  useTransferNurse,
} from "@/api/generated/endpoints"
import { Role, type ManagerToPlace, type NurseRow, type UnitSchema } from "@/api/generated/model"
import {
  createNurseBodyFullNameMax as FULL_NAME_MAX,
  createNurseBodyHospitalIdMax as HOSPITAL_ID_MAX,
  createNurseBodyHospitalIdRegExp as HOSPITAL_ID,
} from "@/api/generated/zod"
import { FormField, SelectField } from "@/components/form-field"
import { PasswordDialog, type Shown } from "@/components/password-dialog"
import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field"
import { NativeSelect, NativeSelectOption } from "@/components/ui/native-select"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { serverErrors, showServerErrors } from "@/lib/server-errors"
import { useEditing } from "@/lib/use-editing"
import { asDate, monthName, scrollableRegion } from "@/lib/utils"
import { ROLE_NAMES } from "@/roles"
import { onlyFor } from "@/session"

const searchSchema = z.object({ unit: z.string().optional().catch(undefined) })

export const Route = createFileRoute("/_signed-in/nurses")({
  validateSearch: (search) => searchSchema.parse(search),
  beforeLoad: onlyFor(Role.cno, Role.unit_manager),
  staticData: { title: "Nurses" },
  component: NursesPage,
})

const GENDERS = { F: "Female", M: "Male" } as const
const MONTHS_AHEAD = 24
const COULD_NOT_SAVE = "That did not work. Check your connection and try again."

const shortDate = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" })
const dayName = (iso: string) => shortDate.format(asDate(iso))

/** This month and the ones after it. The browser's month, and the API has the last word on the hospital's. */
function comingMonths(): string[] {
  const now = new Date()
  return Array.from({ length: MONTHS_AHEAD + 1 }, (_, index) => {
    const month = new Date(Date.UTC(now.getFullYear(), now.getMonth() + index, 1))
    return month.toISOString().slice(0, 7)
  })
}

function useRefreshNurses() {
  const queryClient = useQueryClient()
  return () => {
    void queryClient.invalidateQueries({ queryKey: getListNursesQueryKey() })
    void queryClient.invalidateQueries({ queryKey: getListManagersToPlaceQueryKey() })
  }
}

const required = (message: string) => z.string().min(1, message)
const profileFields = {
  gender: z.enum(["F", "M"], "Choose a gender."),
  unit_id: required("Choose a unit."),
  start_date: required("Enter the start date."),
}

const fullName = z.string().trim().min(1, "Enter their full name.").max(FULL_NAME_MAX, `At most ${FULL_NAME_MAX} characters.`)

const newNurseSchema = z.object({
  hospital_id: z.string().trim().min(1, "Enter their hospital ID.").max(HOSPITAL_ID_MAX, `At most ${HOSPITAL_ID_MAX} characters.`)
    .regex(HOSPITAL_ID, "Use only letters, digits, dots, dashes and underscores."),
  full_name: fullName,
  ...profileFields,
})
type NewNurse = z.input<typeof newNurseSchema>

function GenderOptions() {
  return (
    <>
      <NativeSelectOption value="">Choose</NativeSelectOption>
      {Object.entries(GENDERS).map(([value, label]) => <NativeSelectOption key={value} value={value}>{label}</NativeSelectOption>)}
    </>
  )
}

function UnitOptions({ units }: { units: UnitSchema[] }) {
  return (
    <>
      <NativeSelectOption value="">Choose a unit</NativeSelectOption>
      {units.map((unit) => <NativeSelectOption key={unit.id} value={unit.id}>{unit.name}</NativeSelectOption>)}
    </>
  )
}

function Unexpected({ error }: { error: unknown }) {
  return error && serverErrors(error).length === 0
    ? <p role="alert" className="text-sm text-destructive">{COULD_NOT_SAVE}</p>
    : null
}

function FormButtons({ submit, pending, onCancel }: { submit: string; pending: boolean; onCancel: () => void }) {
  return (
    <div className="flex gap-2">
      <Button type="submit" disabled={pending}>{submit}</Button>
      <Button type="button" variant="outline" onClick={onCancel}>Cancel</Button>
    </div>
  )
}

function AddNurseForm({ units, onCreated, onCancel }: { units: UnitSchema[]; onCreated: (shown: Shown) => void; onCancel: () => void }) {
  const refresh = useRefreshNurses()
  const create = useCreateNurse({ mutation: { gcTime: 0 } })
  const form = useForm<NewNurse>({
    resolver: zodResolver(newNurseSchema),
    defaultValues: { hospital_id: "", full_name: "", gender: "" as NewNurse["gender"], unit_id: "", start_date: "" },
  })
  const { errors } = form.formState

  useEffect(() => { form.setFocus("hospital_id") }, [form])

  const submit = form.handleSubmit((data) =>
    create.mutate({ data: data as z.output<typeof newNurseSchema> }, {
      onSuccess: ({ nurse, generated_password }) => {
        refresh()
        onCreated({ username: nurse.hospital_id, full_name: nurse.full_name, password: generated_password })
      },
      onError: (error) => showServerErrors(form, error),
    }),
  )

  return (
    <form onSubmit={submit} noValidate>
      <FieldGroup>
        <FormField label="Hospital ID" description="It is also their username." autoComplete="off" spellCheck={false} autoCapitalize="none"
          registration={form.register("hospital_id")} error={errors.hospital_id} />
        <FormField label="Full name" autoComplete="off" registration={form.register("full_name")} error={errors.full_name} />
        <SelectField label="Gender" registration={form.register("gender")} error={errors.gender}><GenderOptions /></SelectField>
        <SelectField label="Unit" registration={form.register("unit_id")} error={errors.unit_id}><UnitOptions units={units} /></SelectField>
        <FormField label="Start date" type="date" registration={form.register("start_date")} error={errors.start_date} />
        <Unexpected error={create.error} />
        <FormButtons submit="Add nurse" pending={create.isPending} onCancel={onCancel} />
      </FieldGroup>
    </form>
  )
}

const managerProfileSchema = z.object({ user_id: required("Choose a unit manager."), ...profileFields })
type ManagerProfile = z.input<typeof managerProfileSchema>

function ManagerProfileForm({ units, onDone, onCancel }: { units: UnitSchema[]; onDone: (message: string) => void; onCancel: () => void }) {
  const refresh = useRefreshNurses()
  const managers = useListManagersToPlace()
  const give = useGiveManagerNurseProfile()
  const form = useForm<ManagerProfile>({
    resolver: zodResolver(managerProfileSchema),
    defaultValues: { user_id: "", gender: "" as ManagerProfile["gender"], unit_id: "", start_date: "" },
  })
  const { errors } = form.formState

  useEffect(() => { if (managers.data) form.setFocus("user_id") }, [form, managers.data])

  const choices: ManagerToPlace[] = managers.data ?? []
  const registration = form.register("user_id", {
    // A manager's profile goes in the unit they hold, so the form starts from there.
    onChange: (event) => {
      const held = choices.find((manager) => manager.id === event.target.value)?.unit
      if (held) form.setValue("unit_id", held.id)
    },
  })

  const submit = form.handleSubmit((data) =>
    give.mutate({ data: data as z.output<typeof managerProfileSchema> }, {
      onSuccess: (nurse) => {
        refresh()
        onDone(`${nurse.full_name} now has a nurse profile, and keeps their role and password.`)
      },
      onError: (error) => showServerErrors(form, error),
    }),
  )

  if (managers.isPending) return <p>Loading…</p>
  if (managers.isError) return <p role="alert">The unit managers could not be read. Reload the page to try again.</p>
  if (choices.length === 0) {
    return (
      <div className="flex flex-col items-start gap-4">
        <p>Every active unit manager already has a nurse profile.</p>
        <Button type="button" variant="outline" onClick={onCancel}>Close</Button>
      </div>
    )
  }
  return (
    <form onSubmit={submit} noValidate>
      <FieldGroup>
        <SelectField label="Unit manager" description="Their username becomes their hospital ID on the rosters." registration={registration} error={errors.user_id}>
          <NativeSelectOption value="">Choose a unit manager</NativeSelectOption>
          {choices.map((manager) => (
            <NativeSelectOption key={manager.id} value={manager.id}>{manager.full_name} ({manager.username})</NativeSelectOption>
          ))}
        </SelectField>
        <SelectField label="Gender" registration={form.register("gender")} error={errors.gender}><GenderOptions /></SelectField>
        <SelectField label="Unit" description="A manager's profile must be in the unit they hold." registration={form.register("unit_id")} error={errors.unit_id}>
          <UnitOptions units={units} />
        </SelectField>
        <FormField label="Start date" type="date" registration={form.register("start_date")} error={errors.start_date} />
        <Unexpected error={give.error} />
        <FormButtons submit="Give profile" pending={give.isPending} onCancel={onCancel} />
      </FieldGroup>
    </form>
  )
}

const transferSchema = z.object({ unit_id: required("Choose a unit."), from_month: required("Choose a month.") })
type Transfer = z.infer<typeof transferSchema>

function TransferForm({ nurse, units, onDone, onCancel }: { nurse: NurseRow; units: UnitSchema[]; onDone: (message: string) => void; onCancel: () => void }) {
  const refresh = useRefreshNurses()
  const transfer = useTransferNurse()
  const form = useForm<Transfer>({ resolver: zodResolver(transferSchema), defaultValues: { unit_id: "", from_month: "" } })
  const { errors } = form.formState
  const months = useMemo(comingMonths, [])

  useEffect(() => { form.setFocus("unit_id") }, [form])

  const submit = form.handleSubmit((data) =>
    transfer.mutate({ nurseId: nurse.id, data }, {
      onSuccess: () => {
        refresh()
        const unit = units.find((candidate) => candidate.id === data.unit_id)?.name
        onDone(`${nurse.full_name} transfers to ${unit} from ${monthName(data.from_month)}.`)
      },
      onError: (error) => showServerErrors(form, error),
    }),
  )

  return (
    <form onSubmit={submit} noValidate>
      <FieldGroup>
        <SelectField label="To unit" registration={form.register("unit_id")} error={errors.unit_id}><UnitOptions units={units} /></SelectField>
        <SelectField label="Effective from" description="They stay where they are until that month begins. This replaces any transfer waiting for that month or later."
          registration={form.register("from_month")} error={errors.from_month}>
          <NativeSelectOption value="">Choose a month</NativeSelectOption>
          {months.map((month) => <NativeSelectOption key={month} value={month}>{monthName(month)}</NativeSelectOption>)}
        </SelectField>
        <Unexpected error={transfer.error} />
        <FormButtons submit="Transfer" pending={transfer.isPending} onCancel={onCancel} />
      </FieldGroup>
    </form>
  )
}

const detailsSchema = z.object({ full_name: fullName, gender: profileFields.gender, start_date: profileFields.start_date })
type Details = z.input<typeof detailsSchema>

function DetailsForm({ nurse, onDone, onCancel }: { nurse: NurseRow; onDone: (message: string) => void; onCancel: () => void }) {
  const refresh = useRefreshNurses()
  const correct = useCorrectNurseDetails()
  const form = useForm<Details>({
    resolver: zodResolver(detailsSchema),
    defaultValues: { full_name: nurse.full_name, gender: nurse.gender, start_date: nurse.start_date },
  })
  const { errors } = form.formState
  const isStaffNurse = nurse.role === Role.staff_nurse

  useEffect(() => { form.setFocus(isStaffNurse ? "full_name" : "gender") }, [form, isStaffNurse])

  const submit = form.handleSubmit((data) =>
    correct.mutate({ nurseId: nurse.id, data: data as z.output<typeof detailsSchema> }, {
      onSuccess: ({ nurse: next, first_placement_extended: extended }) => {
        refresh()
        const renamed = next.full_name !== nurse.full_name
        if (!renamed && next.gender === nurse.gender && next.start_date === nurse.start_date) {
          onDone(`Nothing changed for ${next.full_name}.`)
          return
        }
        const longer = extended ? ` Their time in ${extended.unit.name} now begins in ${monthName(extended.from_month)}.` : ""
        onDone(`The details of ${next.full_name} are corrected.${longer}`)
      },
      onError: (error) => showServerErrors(form, error),
    }),
  )

  return (
    <form onSubmit={submit} noValidate>
      <FieldGroup>
        <FormField label="Full name" autoComplete="off" readOnly={!isStaffNurse} className="read-only:bg-muted" registration={form.register("full_name")} error={errors.full_name}
          description={isStaffNurse ? undefined : "It is on their account, which is the System Admin's, so it cannot be corrected here."} />
        <SelectField label="Gender" registration={form.register("gender")} error={errors.gender}><GenderOptions /></SelectField>
        <FormField label="Start date" type="date" registration={form.register("start_date")} error={errors.start_date}
          description="A date before their first month in a unit starts their time in that unit from that date's month." />
        <p className="text-sm text-muted-foreground">
          Hospital ID <span translate="no">{nurse.hospital_id}</span> cannot be corrected, because it is their username.
        </p>
        <Unexpected error={correct.error} />
        <FormButtons submit="Save details" pending={correct.isPending} onCancel={onCancel} />
      </FieldGroup>
    </form>
  )
}

const endDateSchema = z.object({ end_date: required("Enter the end date.") })
type EndDate = z.infer<typeof endDateSchema>

function EndDateForm({ nurse, onDone, onCancel }: { nurse: NurseRow; onDone: (message: string) => void; onCancel: () => void }) {
  const refresh = useRefreshNurses()
  const setEndDate = useSetNurseEndDate()
  const form = useForm<EndDate>({ resolver: zodResolver(endDateSchema), defaultValues: { end_date: nurse.end_date ?? "" } })
  const { errors } = form.formState
  const isStaffNurse = nurse.role === Role.staff_nurse

  useEffect(() => { form.setFocus("end_date") }, [form])

  function save(endDate: string | null) {
    setEndDate.mutate({ nurseId: nurse.id, data: { end_date: endDate } }, {
      onSuccess: (next) => {
        refresh()
        if (!next.end_date) onDone(`${next.full_name} has no end date now.`)
        else if (!isStaffNurse) onDone(`The end date of ${next.full_name} is ${dayName(next.end_date)}. Their account stays active.`)
        else if (!next.is_active) onDone(`${next.full_name} is deactivated.`)
        else onDone(`${next.full_name} stays active until ${dayName(next.end_date)}.`)
      },
      onError: (error) => showServerErrors(form, error),
    })
  }

  return (
    <form onSubmit={form.handleSubmit(({ end_date }) => save(end_date))} noValidate>
      <FieldGroup>
        <FormField label="End date" type="date" registration={form.register("end_date")} error={errors.end_date}
          description={isStaffNurse
            ? "Their last day. Today or earlier deactivates them at once and logs them out; a later date does so when it has passed. Nurses are never deleted. Clearing the date lets them log in again with the password they had."
            : "Their last day on the rosters. Their account stays as it is: it is the System Admin's."} />
        <Unexpected error={setEndDate.error} />
        <div className="flex flex-wrap gap-2">
          <Button type="submit" disabled={setEndDate.isPending}>Save end date</Button>
          {nurse.end_date && <Button type="button" variant="outline" disabled={setEndDate.isPending} onClick={() => save(null)}>Clear end date</Button>}
          <Button type="button" variant="outline" onClick={onCancel}>Cancel</Button>
        </div>
      </FieldGroup>
    </form>
  )
}

function ResetDialog({ nurse, onCancel, onReset }: { nurse: NurseRow | null; onCancel: () => void; onReset: (shown: Shown) => void }) {
  const reset = useResetNursePassword({ mutation: { gcTime: 0 } })
  const refresh = useRefreshNurses()

  function confirm() {
    if (!nurse) return
    reset.mutate({ nurseId: nurse.id }, {
      onSuccess: ({ generated_password }) => {
        refresh()
        reset.reset()
        onReset({ username: nurse.hospital_id, full_name: nurse.full_name, password: generated_password })
      },
    })
  }

  return (
    <AlertDialog open={nurse !== null} onOpenChange={(open) => { if (!open && !reset.isPending) { reset.reset(); onCancel() } }}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Reset the password of {nurse?.hospital_id}?</AlertDialogTitle>
          <AlertDialogDescription>
            Their password stops working and they are logged out. You get a new one to give them, which they must change at their next login.
          </AlertDialogDescription>
        </AlertDialogHeader>
        {reset.isError && <p role="alert" className="text-sm text-destructive">{serverErrors(reset.error)[0]?.message ?? COULD_NOT_SAVE}</p>}
        <AlertDialogFooter>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <Button variant="destructive" disabled={reset.isPending} onClick={confirm}>Reset password</Button>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}

/** What the coming transfers mean to the caller. A manager learns only when a nurse joins or leaves their unit. */
function transferLines({ unit, transfers }: NurseRow, isCno: boolean): string[] {
  if (isCno) return transfers.map((transfer) => `${transfer.unit?.name} from ${monthName(transfer.from_month)}`)
  let inTheUnit = unit !== null
  return transfers.flatMap((transfer) => {
    const joins = transfer.unit !== null
    if (joins === inTheUnit) return []
    inTheUnit = joins
    return `${joins ? "Joins" : "Leaves"} from ${monthName(transfer.from_month)}`
  })
}

/** A manager's account is the System Admin's, and a nurse still to join is not yet this manager's. */
const canReset = (nurse: NurseRow) => nurse.role === Role.staff_nurse && nurse.unit !== null

function Status({ nurse, isCno }: { nurse: NurseRow; isCno: boolean }) {
  return (
    <div className="flex flex-col items-start gap-1">
      <div className="flex flex-wrap gap-1">
        <Badge variant={nurse.is_active ? "secondary" : "outline"}>{nurse.is_active ? "Active" : "Deactivated"}</Badge>
        {nurse.role !== Role.staff_nurse && <Badge variant="outline">{ROLE_NAMES[nurse.role]}</Badge>}
        {nurse.must_change_password && <Badge variant="outline">Password change due</Badge>}
      </div>
      {nurse.end_date && <span className="text-muted-foreground">End date {dayName(nurse.end_date)}</span>}
      {transferLines(nurse, isCno).map((line) => <span key={line} className="text-muted-foreground">{line}</span>)}
    </div>
  )
}

/** The form above the list, one at a time, so a long list does not push it out of reach. */
type Panel =
  | { kind: "add" }
  | { kind: "manager" }
  | { kind: "details"; nurse: NurseRow }
  | { kind: "transfer"; nurse: NurseRow }
  | { kind: "end"; nurse: NurseRow }

const PANEL_TITLES: Record<Panel["kind"], (name: string) => string> = {
  add: () => "Add a nurse",
  manager: () => "Give a unit manager a nurse profile",
  details: (name) => `Correct the details of ${name}`,
  transfer: (name) => `Transfer ${name}`,
  end: (name) => `End date of ${name}`,
}

function NursesPage() {
  const { user } = useRouteContext({ from: "/_signed-in" })
  const isCno = user.role === Role.cno
  const nurses = useListNurses()
  const units = useListUnits()
  const { editing: panel, start, finish } = useEditing<Panel>()
  const [done, setDone] = useState("")
  const [shown, setShown] = useState<Shown | null>(null)
  const [resetting, setResetting] = useState<NurseRow | null>(null)
  const { unit: unitInAddress } = Route.useSearch()
  const navigate = useNavigate({ from: Route.fullPath })

  const liveUnits = (units.data ?? []).filter((unit) => !unit.archived)
  const held = isCno ? undefined : units.data?.[0]
  // An old link may name a unit that is not there, and nobody would be listed for no reason a person could see.
  const unitShown = units.data?.some((unit) => unit.id === unitInAddress) ? unitInAddress : ""
  const rows = (nurses.data ?? []).filter((nurse) =>
    !unitShown || nurse.unit?.id === unitShown || nurse.transfers.some((transfer) => transfer.unit?.id === unitShown))
  const open = (next: Panel, button: HTMLElement) => { setDone(""); start(next, button) }
  const finished = (message: string) => { setDone(message); finish() }

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-4">
      <h1 className="text-xl font-medium">{held ? `Nurses of ${held.name}` : "Nurses"}</h1>
      <p className="text-muted-foreground">
        {isCno
          ? "Everyone on a unit's rosters. Nurses are never deleted: an end date deactivates them."
          : "The CNO adds nurses, transfers them and sets their end dates. You can reset the password of a nurse in your unit."}
      </p>
      {(nurses.isPending || units.isPending) && <p>Loading…</p>}
      {(nurses.isError || units.isError) && <p role="alert">The nurses could not be read. Reload the page to try again.</p>}
      {/* Always rendered, because a live region mounted with its text may never be read out. */}
      <p role="status" className="text-sm text-muted-foreground empty:sr-only">{done}</p>
      {isCno && units.data && (
        <div className="flex flex-wrap gap-2">
          <Button onClick={(event) => open({ kind: "add" }, event.currentTarget)}>Add a nurse</Button>
          <Button variant="outline" onClick={(event) => open({ kind: "manager" }, event.currentTarget)}>Give a unit manager a nurse profile</Button>
        </div>
      )}
      {panel && (
        <Card className="max-w-xl">
          <CardHeader>
            <CardTitle><h2>{PANEL_TITLES[panel.kind]("nurse" in panel ? panel.nurse.full_name : "")}</h2></CardTitle>
          </CardHeader>
          <CardContent>
            {panel.kind === "add" && (
              <AddNurseForm units={liveUnits} onCancel={finish} onCreated={(next) => { setShown(next); finished(`${next.full_name} is added.`) }} />
            )}
            {panel.kind === "manager" && <ManagerProfileForm units={liveUnits} onCancel={finish} onDone={finished} />}
            {panel.kind === "details" && (
              <DetailsForm key={panel.nurse.id} nurse={panel.nurse} onCancel={finish} onDone={finished} />
            )}
            {panel.kind === "transfer" && <TransferForm key={panel.nurse.id} nurse={panel.nurse} units={liveUnits} onCancel={finish} onDone={finished} />}
            {panel.kind === "end" && <EndDateForm key={panel.nurse.id} nurse={panel.nurse} onCancel={finish} onDone={finished} />}
          </CardContent>
        </Card>
      )}
      {nurses.data && units.data && (
        <Card>
          <CardContent className="flex flex-col gap-4">
            {isCno && nurses.data.length > 0 && (
              <Field className="max-w-xs">
                <FieldLabel htmlFor="show-unit">Show</FieldLabel>
                <NativeSelect id="show-unit" value={unitShown} onChange={(event) => void navigate({ search: { unit: event.target.value || undefined } })}>
                  <NativeSelectOption value="">Every unit</NativeSelectOption>
                  {units.data.map((unit) => <NativeSelectOption key={unit.id} value={unit.id}>{unit.name}</NativeSelectOption>)}
                </NativeSelect>
              </Field>
            )}
            {nurses.data.length === 0 ? (
              <p>
                {isCno && "There are no nurses yet. Add the first one above."}
                {!isCno && held && `${held.name} has no nurses yet. The CNO adds them.`}
                {!isCno && !held && "No unit is assigned to you yet. The CNO assigns each unit its manager."}
              </p>
            ) : rows.length === 0 ? (
              <p>No nurse is in this unit or due to join it.</p>
            ) : (
              // As on the Units page, a row's actions do not stay in view on a narrow screen: they would cover the name.
              <Table container={isCno || rows.some(canReset) ? undefined : scrollableRegion(held ? `Nurses of ${held.name}` : "Nurses")}>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Hospital ID</TableHead>
                    {isCno && <TableHead>Unit</TableHead>}
                    <TableHead>Gender</TableHead>
                    <TableHead>Start date</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead><span className="sr-only">Actions</span></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {rows.map((nurse) => (
                    <TableRow key={nurse.id}>
                      <TableCell>{nurse.full_name}</TableCell>
                      <TableCell translate="no">{nurse.hospital_id}</TableCell>
                      {isCno && <TableCell>{nurse.unit?.name}</TableCell>}
                      <TableCell>{GENDERS[nurse.gender]}</TableCell>
                      <TableCell className="tabular-nums">{dayName(nurse.start_date)}</TableCell>
                      <TableCell><Status nurse={nurse} isCno={isCno} /></TableCell>
                      <TableCell>
                        {/* Two by two for the CNO, because four in a line push the last out of view on a laptop. */}
                        <div className={isCno ? "ml-auto grid w-fit grid-cols-[auto_auto] gap-2" : "flex justify-end"}>
                          {isCno && (
                            <>
                              <Button variant="outline" size="sm" aria-label={`Correct details of ${nurse.full_name}`}
                                onClick={(event) => open({ kind: "details", nurse }, event.currentTarget)}>
                                Correct details
                              </Button>
                              <Button variant="outline" size="sm" aria-label={`Transfer ${nurse.full_name}`}
                                onClick={(event) => open({ kind: "transfer", nurse }, event.currentTarget)}>
                                Transfer
                              </Button>
                              <Button variant="outline" size="sm" aria-label={`${nurse.end_date ? "Change" : "Set"} end date of ${nurse.full_name}`}
                                onClick={(event) => open({ kind: "end", nurse }, event.currentTarget)}>
                                {nurse.end_date ? "Change end date" : "Set end date"}
                              </Button>
                            </>
                          )}
                          {canReset(nurse) && (
                            <Button variant="outline" size="sm" aria-label={`Reset password of ${nurse.full_name}`}
                              onClick={() => { setDone(""); setResetting(nurse) }}>
                              Reset password
                            </Button>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      )}
      <ResetDialog nurse={resetting} onCancel={() => setResetting(null)} onReset={(next) => {
        setResetting(null)
        setDone(`The password of ${next.username} is reset.`)
        setShown(next)
      }} />
      <PasswordDialog shown={shown} onDone={() => setShown(null)} />
    </div>
  )
}
