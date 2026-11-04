import { zodResolver } from "@hookform/resolvers/zod"
import { useQueryClient } from "@tanstack/react-query"
import { createFileRoute, useRouteContext } from "@tanstack/react-router"
import { Trash2Icon } from "lucide-react"
import { useEffect, useRef, useState, type ReactNode } from "react"
import { useController, useForm, type Control, type FieldError, type FieldPath } from "react-hook-form"
import { z } from "zod"

import { ApiError } from "@/api/fetcher"
import {
  getGetHospitalRulesQueryKey,
  useGetHospitalRules,
  useUpdateHospitalRules,
} from "@/api/generated/endpoints"
import { Role, type HospitalRules, type HospitalRulesState, type Weights } from "@/api/generated/model"
import {
  updateHospitalRulesBodyHoursPerDayMax as DAILY_HOURS_MAX,
  updateHospitalRulesBodyOvertimeMonthCapMax as HOURS_MAX,
  updateHospitalRulesBodyWeightsChangeMax as WEIGHT_MAX,
} from "@/api/generated/zod"
import { CHECKBOX, CheckboxField, FormField } from "@/components/form-field"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { FieldDescription, FieldError as FieldErrorText, FieldGroup, FieldLegend, FieldSet } from "@/components/ui/field"
import { NativeSelect, NativeSelectOption } from "@/components/ui/native-select"
import { onlyFor } from "@/session"

export const Route = createFileRoute("/_signed-in/hospital-rules")({
  beforeLoad: onlyFor(Role.cno, Role.deputy_cno),
  staticData: { title: "Hospital rules" },
  component: HospitalRulesPage,
})

type Explained<Name extends string> = { name: Name; label: string; description: string }
type NumberRule = "hours_per_day" | "ramadan_hours_per_day" | "breastfeeding_reduction" | "overtime_month_cap" | "overtime_year_cap" | "dept_overtime_cap"
type SwitchRule = "hours_rule_enabled" | "overtime_caps_enabled"

const DAILY_HOURS: Explained<NumberRule>[] = [
  {
    name: "hours_per_day",
    label: "Hours per day",
    description: "The regular hours a nurse owes for each working day: a day that is neither a weekend day nor a public holiday.",
  },
  {
    name: "ramadan_hours_per_day",
    label: "Ramadan hours per day",
    description: "The same on Ramadan days, for a nurse marked Ramadan-reduced. Cannot be more than the hours per day.",
  },
  {
    name: "breastfeeding_reduction",
    label: "Breastfeeding reduction (hours)",
    description: "Taken off each working day for a nurse marked breastfeeding. Cannot be more than the Ramadan hours per day.",
  },
]

const SWITCHES: Explained<SwitchRule>[] = [
  {
    name: "hours_rule_enabled",
    label: "Count hours",
    description: "When off, a nurse may work any number of shifts and nobody's overtime or hours short are counted, so the caps below do nothing.",
  },
  {
    name: "overtime_caps_enabled",
    label: "Cap each nurse's overtime",
    description: "When off, the monthly and yearly caps below do not apply.",
  },
]

const CAPS: Explained<NumberRule>[] = [
  {
    name: "overtime_month_cap",
    label: "Monthly overtime cap (hours)",
    description: "The most overtime a nurse may work in a month. The solver returns no roster that breaks this.",
  },
  {
    name: "overtime_year_cap",
    label: "Yearly overtime cap (hours)",
    description: "The most overtime a nurse may work in a year, counting what is already worked. The solver returns no roster that breaks this.",
  },
  {
    name: "dept_overtime_cap",
    label: "Unit overtime cap (hours)",
    description: "The overtime a unit may use in a month before each further hour costs its weight. A roster may go over this one.",
  },
]

const NOT_USED = "Nothing reaches this for now: an accepted request is pinned, so the solver cannot trade it away."

const WEIGHTS: Explained<keyof Weights>[] = [
  { name: "avoidable_shortfall", label: "Avoidable hours short", description: "Each hour a nurse ends short beyond what is less than one shift and what their days could not give. Keep this far above every other weight, so that nothing leaves a nurse idle while a shift of theirs is free." },
  { name: "nurse_shortfall", label: "Hours short", description: "Each hour a nurse ends the month under what they owe. Those hours carry over to the next month." },
  { name: "nurse_overtime", label: "Nurse overtime", description: "Each hour of a nurse's overtime." },
  { name: "dept_overtime", label: "Unit overtime", description: "Each hour of a unit's overtime above the unit overtime cap." },
  { name: "night_rest", label: "Night rest", description: "Each day shift that follows a night shift with too little rest. Applies only in a unit that lets this rule be broken." },
  { name: "shift_switch", label: "Day and night switches", description: "Each switch between day and night shifts above the unit's maximum. Applies only in a unit that lets this rule be broken." },
  { name: "excess_weekend", label: "Too many weekend days", description: "Each weekend day a nurse works above the unit's maximum." },
  { name: "fair_day", label: "Fair share of day shifts", description: "Each tenth of a shift that a nurse's day shifts stray from their fair share, beyond the unit's tolerance." },
  { name: "fair_night", label: "Fair share of night shifts", description: "Each tenth of a shift that a nurse's night shifts stray from their fair share, beyond the unit's tolerance." },
  { name: "fair_weekend", label: "Fair share of weekend days", description: "Each tenth of a shift that a nurse's weekend days stray from their fair share, beyond the unit's tolerance." },
  { name: "score_deficit", label: "Shift score below target", description: "Each hundredth of a score point, per person, that a shift's average score falls below the unit's target." },
  { name: "score_spread", label: "Shift scores far apart", description: "Each hundredth of a score point, per person, that a shift's average rises above the unit's ceiling; or, in a unit that compares shifts, each hundredth between the strongest and the weakest." },
  { name: "change", label: "Changes in a re-plan", description: "Each cell that differs from the roster in force when a month is re-planned." },
  { name: "undesired_day", label: "Working a day asked off", description: `Each day a nurse softly asked to have off but works. ${NOT_USED}` },
  { name: "desired_day", label: "Off on a day asked to work", description: `Each day a nurse softly asked to work but is off. ${NOT_USED}` },
]

// The solver's numbering, 0 is Monday, shown in the order the hospital's week runs.
const WEEKDAYS = [
  [6, "Sunday"], [0, "Monday"], [1, "Tuesday"], [2, "Wednesday"], [3, "Thursday"], [4, "Friday"], [5, "Saturday"],
] as const

const wholeNumber = (max: number) =>
  z.int("Enter a whole number.").min(0, `Between 0 and ${max}.`).max(max, `Between 0 and ${max}.`)

const dailyHours = wholeNumber(DAILY_HOURS_MAX)
const hours = wholeNumber(HOURS_MAX)
const weight = wholeNumber(WEIGHT_MAX)

const schema = z
  .object({
    hours_per_day: dailyHours,
    ramadan_hours_per_day: dailyHours,
    breastfeeding_reduction: dailyHours,
    weekend_weekdays: z.array(z.int()),
    forbidden_successions: z.array(z.array(z.string())),
    forbidden_successions_enabled: z.boolean(),
    hours_rule_enabled: z.boolean(),
    overtime_caps_enabled: z.boolean(),
    overtime_month_cap: hours,
    overtime_year_cap: hours,
    dept_overtime_cap: hours,
    weights: z.object(Object.fromEntries(WEIGHTS.map(({ name }) => [name, weight])) as Record<keyof Weights, typeof weight>),
  })
  .superRefine((rules, context) => {
    if (rules.ramadan_hours_per_day > rules.hours_per_day)
      context.addIssue({ code: "custom", path: ["ramadan_hours_per_day"], message: "Cannot be more than the hours per day." })
    if (rules.breastfeeding_reduction > rules.ramadan_hours_per_day)
      context.addIssue({ code: "custom", path: ["breastfeeding_reduction"], message: "Cannot be more than the Ramadan hours per day." })
    const seen = new Set<string>()
    for (const [today, tomorrow] of rules.forbidden_successions) {
      const pair = `${today} then ${tomorrow}`
      if (seen.has(pair)) {
        context.addIssue({ code: "custom", path: ["forbidden_successions"], message: `${pair} is listed twice. Remove one.` })
        break
      }
      seen.add(pair)
    }
  })

/** A section of the page: a region named by its heading, whichever role is reading. */
function Section({ title, description, children }: { title: string; description?: ReactNode; children: ReactNode }) {
  const id = `section-${title.toLowerCase().replaceAll(" ", "-")}`
  return (
    <Card role="region" aria-labelledby={id}>
      <CardHeader>
        <CardTitle><h2 id={id}>{title}</h2></CardTitle>
        {description && <CardDescription>{description}</CardDescription>}
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  )
}

const WEEKEND_DESCRIPTION = "The days that count as the weekend. A nurse owes no regular hours on them, and each unit's weekend rules apply to them."
const SUCCESSIONS_TITLE = "Forbidden successions"
const SUCCESSIONS_DESCRIPTION = "Shifts a nurse may not work on two days in a row, in that order. The solver returns no roster that breaks these."
const SUCCESSIONS_SWITCH = "When off, the pairs below stay here but the solver ignores them."
const WEIGHTS_DESCRIPTION = "A weight is the price of breaking a soft rule once. The solver looks for the roster with the lowest total, so only how the weights compare to each other matters, and 0 switches the rule off. Each one below says what it is the price of."

function WeekendField({ control, error }: { control: Control<HospitalRules>; error?: FieldError }) {
  const { field } = useController({ control, name: "weekend_weekdays" })
  const toggle = (day: number, on: boolean) =>
    field.onChange(on ? [...field.value, day].sort((a, b) => a - b) : field.value.filter((other) => other !== day))
  return (
    <FieldSet ref={field.ref} tabIndex={-1} aria-describedby={error ? "weekend-days-error" : undefined} className="outline-none">
      <FieldLegend className="sr-only">Weekend days</FieldLegend>
      <div className="flex flex-wrap gap-x-4 gap-y-2">
        {WEEKDAYS.map(([day, name]) => (
          <label key={day} className="flex items-center gap-2 text-sm">
            <input type="checkbox" className={CHECKBOX} checked={field.value.includes(day)}
              onChange={(event) => toggle(day, event.target.checked)} />
            {name}
          </label>
        ))}
      </div>
      <FieldErrorText id="weekend-days-error" errors={error ? [error] : undefined} role={undefined} />
    </FieldSet>
  )
}

function SuccessionsField({ control, codes, error }: { control: Control<HospitalRules>; codes: string[]; error?: FieldError }) {
  const { field } = useController({ control, name: "forbidden_successions" })
  const pairs = field.value
  const add = useRef<HTMLButtonElement>(null)
  const list = useRef<HTMLUListElement>(null)
  const [focus, setFocus] = useState<"none" | "last" | "add">("none")

  // After the list has drawn what the button just changed, so focus never falls back to the page.
  useEffect(() => {
    if (focus === "add") add.current?.focus()
    if (focus === "last") list.current?.querySelector<HTMLElement>("li:last-child select")?.focus()
    if (focus !== "none") setFocus("none")
  }, [focus])

  const listed = new Set(pairs.map(([today, tomorrow]) => `${today} ${tomorrow}`))
  // Two different shifts first: a shift forbidden after itself is a far stronger rule to add by accident.
  const unlisted = codes
    .flatMap((today) => codes.map((tomorrow) => [today, tomorrow]))
    .filter(([today, tomorrow]) => !listed.has(`${today} ${tomorrow}`))
  const nextPair = unlisted.find(([today, tomorrow]) => today !== tomorrow) ?? unlisted[0]
  const change = (index: number, side: 0 | 1, code: string) =>
    field.onChange(pairs.map((pair, i) => (i === index ? (side === 0 ? [code, pair[1]] : [pair[0], code]) : pair)))

  return (
    <div ref={field.ref} tabIndex={-1} role="group" aria-label="Pairs" aria-describedby={error ? "forbidden-successions-error" : undefined}
      className="flex flex-col gap-3 outline-none">
      {pairs.length === 0 && <p className="text-sm text-muted-foreground">No successions are forbidden.</p>}
      <ul ref={list} className="flex flex-col gap-3 sm:gap-2">
        {pairs.map(([today, tomorrow], index) => (
          // By position: a row holds no state of its own, only what `pairs` says.
          <li key={index}>
            <div role="group" aria-label={`Pair ${index + 1}`} className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm">
            <label className="flex items-center gap-2">
              After
              <NativeSelect className="w-20" value={today} onChange={(event) => change(index, 0, event.target.value)}>
                {codes.map((code) => <NativeSelectOption key={code} value={code}>{code}</NativeSelectOption>)}
              </NativeSelect>
            </label>
            <label className="flex items-center gap-2">
              the next day cannot be
              <NativeSelect className="w-20" value={tomorrow} onChange={(event) => change(index, 1, event.target.value)}>
                {codes.map((code) => <NativeSelectOption key={code} value={code}>{code}</NativeSelectOption>)}
              </NativeSelect>
            </label>
            <Button type="button" variant="ghost" size="icon" aria-label={`Remove pair ${index + 1}`}
              onClick={() => {
                field.onChange(pairs.filter((_, i) => i !== index))
                setFocus(pairs.length === 1 || index === pairs.length - 1 ? "add" : "none")
              }}>
              <Trash2Icon aria-hidden="true" />
            </Button>
            </div>
          </li>
        ))}
      </ul>
      <FieldErrorText id="forbidden-successions-error" errors={error ? [error] : undefined} role={undefined} />
      <Button ref={add} type="button" variant="outline" className="self-start" disabled={!nextPair}
        onClick={() => {
          if (!nextPair) return
          field.onChange([...pairs, nextPair])
          setFocus("last")
        }}>
        Add a pair
      </Button>
    </div>
  )
}

function serverErrors(error: unknown): { path: string; message: string }[] {
  if (!(error instanceof ApiError) || error.status !== 422) return []
  const detail = (error.body as { detail?: { loc: (string | number)[]; msg: string }[] } | undefined)?.detail ?? []
  return detail.map(({ loc, msg }) => {
    // ["body", "body", "weights", "change"], or ["body", "body", "forbidden_successions", 3, 0].
    const [first, second] = loc.slice(2)
    // Pydantic opens a validator's own message with this.
    return { path: first === "weights" ? `weights.${second}` : String(first), message: msg.replace(/^Value error, /, "") }
  })
}

function RulesForm({ state }: { state: HospitalRulesState }) {
  const queryClient = useQueryClient()
  const update = useUpdateHospitalRules()
  const form = useForm<HospitalRules>({ resolver: zodResolver(schema), defaultValues: state.rules })
  const { errors, isDirty } = form.formState
  const asNumber = { valueAsNumber: true }

  const submit = form.handleSubmit((data) =>
    update.mutate(
      { data },
      {
        onSuccess: (saved) => {
          queryClient.setQueryData(getGetHospitalRulesQueryKey(), saved)
          form.reset(saved.rules)
        },
        onError: (error) => {
          serverErrors(error).forEach(({ path, message }, index) =>
            form.setError(path as FieldPath<HospitalRules>, { message }, { shouldFocus: index === 0 }))
        },
      },
    ),
  )
  const refused = update.isError && serverErrors(update.error).length > 0

  return (
    <form onSubmit={submit} noValidate className="flex flex-col gap-4">
      <Section title="Daily hours">
        <FieldGroup>
          {DAILY_HOURS.map(({ name, label, description }) => (
            <FormField key={name} label={label} type="number" inputMode="numeric" description={description}
              registration={form.register(name, asNumber)} error={errors[name]} />
          ))}
        </FieldGroup>
      </Section>
      <Section title="Weekend days" description={WEEKEND_DESCRIPTION}>
        <WeekendField control={form.control} error={errors.weekend_weekdays as FieldError | undefined} />
      </Section>
      <Section title={SUCCESSIONS_TITLE} description={SUCCESSIONS_DESCRIPTION}>
        <FieldGroup>
          <CheckboxField label="Forbid these successions" description={SUCCESSIONS_SWITCH}
            registration={form.register("forbidden_successions_enabled")} />
          <SuccessionsField control={form.control} codes={state.shift_codes}
            error={errors.forbidden_successions as FieldError | undefined} />
        </FieldGroup>
      </Section>
      <Section title="Hours and overtime">
        <FieldGroup>
          {SWITCHES.map(({ name, label, description }) => (
            <CheckboxField key={name} label={label} description={description} registration={form.register(name)} />
          ))}
          {CAPS.map(({ name, label, description }) => (
            <FormField key={name} label={label} type="number" inputMode="numeric" description={description}
              registration={form.register(name, asNumber)} error={errors[name]} />
          ))}
        </FieldGroup>
      </Section>
      <Section title="Weights" description={WEIGHTS_DESCRIPTION}>
        <FieldGroup>
          {WEIGHTS.map(({ name, label, description }) => (
            <FormField key={name} label={label} type="number" inputMode="numeric" description={description}
              registration={form.register(`weights.${name}`, asNumber)} error={errors.weights?.[name]} />
          ))}
        </FieldGroup>
      </Section>
      {update.isError && (
        <p role="alert" className="text-sm text-destructive">
          {refused ? "Some values were refused. Correct the fields marked above and save again." : "The rules could not be saved. Check your connection and save again."}
        </p>
      )}
      {/* Always rendered, because a live region mounted with its text may never be read out. */}
      <p role="status" className="text-sm text-muted-foreground empty:sr-only">
        {update.isSuccess && !isDirty ? "Saved." : ""}
      </p>
      <Button type="submit" className="self-start" disabled={update.isPending || !(isDirty || state.needs_review)}>Save</Button>
    </form>
  )
}

function ReadOnlyList({ items }: { items: { label: string; value: ReactNode; description: string }[] }) {
  return (
    <dl className="flex flex-col gap-4">
      {items.map(({ label, value, description }) => (
        <div key={label} className="flex flex-col gap-0.5">
          <dt className="text-sm font-medium">{label}</dt>
          <dd className="text-sm tabular-nums">{value}</dd>
          <dd><FieldDescription>{description}</FieldDescription></dd>
        </div>
      ))}
    </dl>
  )
}

const onOff = (on: boolean) => (on ? "On" : "Off")

function RulesReadOnly({ rules }: { rules: HospitalRules }) {
  const weekend = WEEKDAYS.filter(([day]) => rules.weekend_weekdays.includes(day)).map(([, name]) => name)
  return (
    <div className="flex flex-col gap-4">
      <Section title="Daily hours">
        <ReadOnlyList items={DAILY_HOURS.map(({ name, label, description }) => ({ label, description, value: rules[name] }))} />
      </Section>
      <Section title="Weekend days" description={WEEKEND_DESCRIPTION}>
        <ul className="flex flex-col gap-1 text-sm">
          {weekend.length ? weekend.map((name) => <li key={name}>{name}</li>) : <li>None</li>}
        </ul>
      </Section>
      <Section title={SUCCESSIONS_TITLE} description={SUCCESSIONS_DESCRIPTION}>
        <div className="flex flex-col gap-4">
          <ReadOnlyList items={[{ label: "Forbid these successions", description: SUCCESSIONS_SWITCH, value: onOff(rules.forbidden_successions_enabled) }]} />
          <ul className="flex flex-col gap-1 text-sm">
            {rules.forbidden_successions.length === 0 && <li>No successions are forbidden.</li>}
            {rules.forbidden_successions.map(([today, tomorrow]) => (
              <li key={`${today} ${tomorrow}`}>After {today}, not {tomorrow}</li>
            ))}
          </ul>
        </div>
      </Section>
      <Section title="Hours and overtime">
        <ReadOnlyList items={[
          ...SWITCHES.map(({ name, label, description }) => ({ label, description, value: onOff(rules[name]) })),
          ...CAPS.map(({ name, label, description }) => ({ label, description, value: rules[name] })),
        ]} />
      </Section>
      <Section title="Weights" description={WEIGHTS_DESCRIPTION}>
        <ReadOnlyList items={WEIGHTS.map(({ name, label, description }) => ({ label, description, value: rules.weights[name] }))} />
      </Section>
    </div>
  )
}

function HospitalRulesPage() {
  const { user } = useRouteContext({ from: "/_signed-in" })
  const rules = useGetHospitalRules()
  const mayChange = user.role === Role.cno

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-4">
      <h1 className="text-xl font-medium">Hospital rules</h1>
      <p className="text-muted-foreground">
        The rules every unit rosters by. Every solve starts from them.
        {!mayChange && " Only the CNO can change these."}
      </p>
      {rules.isPending && <p>Loading…</p>}
      {rules.isError && <p role="alert">The rules could not be read. Reload the page to try again.</p>}
      {rules.data?.needs_review && (
        <div className="flex flex-col items-start gap-1">
          <Badge variant="secondary">Defaults, review before the first solve</Badge>
          {mayChange && <p className="text-sm">Saving this page marks them as reviewed, even with nothing changed.</p>}
        </div>
      )}
      {rules.data && (mayChange ? <RulesForm state={rules.data} /> : <RulesReadOnly rules={rules.data.rules} />)}
    </div>
  )
}
