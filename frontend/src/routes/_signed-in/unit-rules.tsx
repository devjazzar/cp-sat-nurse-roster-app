import { zodResolver } from "@hookform/resolvers/zod"
import { useQueryClient } from "@tanstack/react-query"
import { createFileRoute, useNavigate, useRouteContext } from "@tanstack/react-router"
import { Fragment, useEffect, useRef, useState } from "react"
import { useController, useFieldArray, useForm, type FieldError, type UseFormReturn } from "react-hook-form"
import { z } from "zod"

import { getGetUnitRulesQueryKey, getListUnitsQueryKey, useGetUnitRules, useUpdateUnitRules } from "@/api/generated/endpoints"
import { Role, type HeadcountRule, type ShiftChoice, type UnitRulesAnswer, type UnitRulesBody, type UnitRulesState } from "@/api/generated/model"
import {
  updateUnitRulesBodyPreferenceCapMax as PREFERENCE_CAP_MAX,
  updateUnitRulesBodyRequestCapMax as REQUEST_CAP_MAX,
  updateUnitRulesBodyRulesCarryCapMax as PARAM_MAX,
  updateUnitRulesBodyRulesHeadcountsItemWeekdayMinMax as HEADCOUNT_MAX,
  updateUnitRulesBodyRulesMaxFullRunsMax as FULL_RUNS_MAX,
  updateUnitRulesBodyRulesNightRestDaysMax as REST_DAYS_MAX,
  updateUnitRulesBodyRulesShiftsMax as SHIFTS_MAX,
} from "@/api/generated/zod"
import { CodeCheckboxes } from "@/components/code-checkboxes"
import { CheckboxField, FormField, SelectField } from "@/components/form-field"
import { onOff, ReadOnlyList, Section } from "@/components/rules-section"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { FieldGroup } from "@/components/ui/field"
import { NativeSelectOption } from "@/components/ui/native-select"
import { UnitPicker, useChosenUnit } from "@/components/unit-picker"
import { serverErrors, showServerErrors } from "@/lib/server-errors"
import { onlyFor } from "@/session"

const searchSchema = z.object({ unit: z.string().optional().catch(undefined) })

export const Route = createFileRoute("/_signed-in/unit-rules")({
  validateSearch: (search) => searchSchema.parse(search),
  beforeLoad: onlyFor(Role.unit_manager, Role.cno, Role.deputy_cno),
  staticData: { title: "Unit rules" },
  component: UnitRulesPage,
})

type Explained<Name extends string> = { name: Name; label: string; description: string }
type NumberRule = "score_target" | "score_target_weekend" | "score_band_hi" | "score_band_hi_weekend" | "night_rest_days" | "fair_tolerance" | "carry_cap" | "max_consecutive_shifts" | "max_full_runs" | "double_cycle_rest" | "max_weekends" | "max_switches"
type SwitchRule = "headcount_enabled" | "require_team_leader" | "require_both_genders" | "score_balance" | "night_rest_hard" | "fair_weekends" | "carry_fairness" | "no_mixed_blocks" | "switches_hard"

const SHIFTS_DESCRIPTION = "Chosen from the hospital's shift catalogue. A nurse in this unit can only be given these."
const NIGHT_AND_DAY = [
  { name: "night_shift", label: "Night shift", description: "The shift the rules on night rest, unmixed runs and switches treat as night." },
  { name: "day_shift", label: "Day shift", description: "The shift the same rules treat as day. Any other shift this unit works counts as neither." },
] as const

const HEADCOUNT_SWITCH: Explained<SwitchRule> = {
  name: "headcount_enabled",
  label: "Hold every shift to its headcount",
  description: "When off, the numbers below stay here but the solver ignores them.",
}
const HEADCOUNTS_DESCRIPTION = "How many nurses each shift needs on a weekday and on a weekend day. The solver returns no roster that breaks these."
const WHO_SWITCHES: Explained<SwitchRule>[] = [
  { name: "require_team_leader", label: "A team leader on every shift", description: "Every shift with a headcount needs at least one nurse marked team leader. The solver returns no roster that breaks this." },
  { name: "require_both_genders", label: "Both genders on every shift", description: "Every shift with a headcount needs at least one female and one male nurse. The solver returns no roster that breaks this." },
]
const SCORE_TARGETS: Explained<NumberRule>[] = [
  { name: "score_target", label: "Score target on a weekday", description: "What the average score of each shift with a headcount should reach, from 0 to 1. A roster may fall short, at the price of the hospital's weight." },
  { name: "score_target_weekend", label: "Score target on a weekend day", description: "The same on a weekend day." },
]
const SCORE_SWITCH: Explained<SwitchRule> = {
  name: "score_balance",
  label: "Keep the strength of shifts balanced",
  description: "When off, a shift can be as far above its target as the roster makes it, at no price.",
}
const SCORE_MODES = { band: "Keep each shift under a ceiling (faster to solve)", spread: "Keep the strongest and weakest shifts close (slower to solve)" } as const
const SCORE_MODE_DESCRIPTION = "How strength is balanced. Under a ceiling, the two ceilings below apply and the targets cannot be above them."
const SCORE_CEILINGS: Explained<NumberRule>[] = [
  { name: "score_band_hi", label: "Score ceiling on a weekday", description: "The average score above which a shift starts to cost, when balancing under a ceiling." },
  { name: "score_band_hi_weekend", label: "Score ceiling on a weekend day", description: "The same on a weekend day." },
]
const NIGHT_REST_DAYS: Explained<NumberRule> = {
  name: "night_rest_days",
  label: "Days off after a night shift",
  description: "How many days off a nurse is owed between a night shift and the next day shift. 0 switches this off.",
}
const NIGHT_REST_SWITCH: Explained<SwitchRule> = {
  name: "night_rest_hard",
  label: "Never break the night rest",
  description: "When on, the solver returns no roster that breaks it. When off, a roster may, at the price of the hospital's weight.",
}
const LONGEST_RUN: Explained<NumberRule> = {
  name: "max_consecutive_shifts",
  label: "Longest run of shifts",
  description: "The most days in a row a nurse may work. 0 means no limit. The solver returns no roster that breaks this.",
}
/** Shown only while the longest run is above 1: at 0 a run has no limit and at 1 every run would be full. */
const FULL_RUNS: Explained<NumberRule> = {
  name: "max_full_runs",
  label: "Most full runs in a month",
  description: "A full run is as many shifts in a row as the longest run allows. Each one beyond this costs the solver, which then breaks the work into shorter runs.",
}
const AFTER_TWO_RUNS: Explained<NumberRule> = {
  name: "double_cycle_rest",
  label: "Days off after two runs",
  description: "After a run, one day off and another run, how many days off a nurse is then owed. The solver returns no roster that breaks this.",
}
/** Not while the longest run is blank, so that the field does not vanish while a new number is typed. */
const fullRunsApply = (longest: number) => Number.isNaN(longest) || longest > 1
const MIXED_SWITCH: Explained<SwitchRule> = {
  name: "no_mixed_blocks",
  label: "Keep runs unmixed",
  description: "When on, the days of a run are all day shifts or all night shifts. The solver returns no roster that breaks this.",
}
const FAIR_SHIFTS_DESCRIPTION = "Whose counts are spread fairly among the nurses who may work them. Only a shift with a headcount can be chosen."
const FAIR_TOLERANCE: Explained<NumberRule> = {
  name: "fair_tolerance",
  label: "Free difference from a fair share (shifts)",
  description: "How many shifts a nurse may stray from their fair share before it starts to cost.",
}
const FAIR_SWITCHES: Explained<SwitchRule>[] = [
  { name: "fair_weekends", label: "Spread weekend days fairly", description: "Weekend days worked are spread evenly among the unit's nurses." },
  { name: "carry_fairness", label: "Carry fairness between months", description: "Nights and weekend days above or below a nurse's fair share so far move this month's fair share." },
]
const CARRY_CAP: Explained<NumberRule> = {
  name: "carry_cap",
  label: "Most a month's share can move (shifts)",
  description: "The limit on how far what is carried can move a fair share in one month.",
}
const LIMITS: Explained<NumberRule>[] = [
  { name: "max_weekends", label: "Weekend days a month", description: "How many weekend days a nurse may work in a month before each further one costs the hospital's weight." },
  { name: "max_switches", label: "Switches between day and night a month", description: "How many times a nurse may switch between day and night shifts in a month. The change from last month counts." },
]
const SWITCHES_HARD: Explained<SwitchRule> = {
  name: "switches_hard",
  label: "Never go over the switch limit",
  description: "When on, the solver returns no roster that breaks it. When off, a roster may, at the price of the hospital's weight.",
}
const REQUEST_CAP_DESCRIPTION = "How many requests each nurse may make for a month. 0 means none."
const PREFERENCE_CAP_DESCRIPTION = "How many preferences each nurse may make for a month, days she would rather have off or work, which the solver keeps when it can. 0 switches them off. A request window opens while either cap is above 0."
const TIME_LIMIT_DESCRIPTION = "How long a solve searches unless you choose otherwise when you start it."

const COUNT_FIELDS = [
  { name: "weekday_min", label: "Weekday, at least" },
  { name: "weekday_max", label: "Weekday, at most" },
  { name: "weekend_min", label: "Weekend day, at least" },
  { name: "weekend_max", label: "Weekend day, at most" },
] as const

const wholeNumber = (min: number, max: number) => z.int("Enter a whole number.").min(min, `Between ${min} and ${max}.`).max(max, `Between ${min} and ${max}.`)
const number = (max: number) => z.number("Enter a number.").min(0, `Between 0 and ${max}.`).max(max, `Between 0 and ${max}.`)
const count = wholeNumber(0, PARAM_MAX)
const scoreLevel = number(1)
const shiftCount = number(PARAM_MAX)
const people = wholeNumber(0, HEADCOUNT_MAX)
const fullRuns = wholeNumber(0, FULL_RUNS_MAX)

function schemaFor(timeLimitCap: number) {
  return z
    .object({
      rules: z.object({
        shifts: z.array(z.string()).min(1, "Choose at least one shift.").max(SHIFTS_MAX, `At most ${SHIFTS_MAX} shifts.`),
        night_shift: z.string().min(1, "Choose the night shift."),
        day_shift: z.string().min(1, "Choose the day shift."),
        headcounts: z.array(z.object({
          shift: z.string(),
          weekday_min: people,
          weekday_max: people,
          weekend_min: people,
          weekend_max: people,
          also_counts: z.array(z.string()),
        }).superRefine((row, context) => {
          if (row.weekday_max < row.weekday_min) context.addIssue({ code: "custom", path: ["weekday_max"], message: "Cannot be below the weekday minimum." })
          if (row.weekend_max < row.weekend_min) context.addIssue({ code: "custom", path: ["weekend_max"], message: "Cannot be below the weekend minimum." })
        })),
        headcount_enabled: z.boolean(),
        require_team_leader: z.boolean(),
        require_both_genders: z.boolean(),
        score_target: scoreLevel,
        score_target_weekend: scoreLevel,
        score_balance: z.boolean(),
        score_balance_mode: z.enum(["band", "spread"]),
        score_band_hi: scoreLevel,
        score_band_hi_weekend: scoreLevel,
        night_rest_days: wholeNumber(0, REST_DAYS_MAX),
        night_rest_hard: z.boolean(),
        fair_shifts: z.array(z.string()),
        fair_tolerance: shiftCount,
        fair_weekends: z.boolean(),
        carry_fairness: z.boolean(),
        carry_cap: shiftCount,
        max_consecutive_shifts: count,
        // Checked below, and only while the field shows: a hidden field cannot show its error. `withFullRunsKept` sends the
        // saved value instead of one left wrong behind it.
        max_full_runs: z.union([z.number(), z.nan()]),
        double_cycle_rest: count,
        max_weekends: count,
        no_mixed_blocks: z.boolean(),
        max_switches: count,
        switches_hard: z.boolean(),
      }).superRefine((rules, context) => {
        if (fullRunsApply(rules.max_consecutive_shifts)) {
          const checked = fullRuns.safeParse(rules.max_full_runs)
          if (!checked.success) context.addIssue({ code: "custom", path: ["max_full_runs"], message: checked.error.issues[0].message })
        }
        if (rules.night_shift && rules.night_shift === rules.day_shift)
          context.addIssue({ code: "custom", path: ["day_shift"], message: "Cannot be the night shift too." })
        if (rules.score_balance && rules.score_balance_mode === "band") {
          if (rules.score_target > rules.score_band_hi)
            context.addIssue({ code: "custom", path: ["score_band_hi"], message: "Cannot be below the weekday score target." })
          if (rules.score_target_weekend > rules.score_band_hi_weekend)
            context.addIssue({ code: "custom", path: ["score_band_hi_weekend"], message: "Cannot be below the weekend score target." })
        }
      }),
      request_cap: wholeNumber(0, REQUEST_CAP_MAX),
      preference_cap: wholeNumber(0, PREFERENCE_CAP_MAX),
      default_time_limit: wholeNumber(1, timeLimitCap),
    })
}

/** "rules.shifts.2" stops at the list, which shows the error, and a headcount's shift has no input of its own. */
function formPath(loc: (string | number)[]): string {
  const [first, second, index, field] = loc
  if (second === "shifts" || second === "fair_shifts") return `${first}.${second}`
  if (second === "headcounts" && field === "shift") return `${first}.shifts`
  if (second === "headcounts" && field === "also_counts") return `${first}.${second}.${index}.${field}`
  return loc.join(".")
}

const shiftLabel = ({ code, display_name }: ShiftChoice) => `${code}, ${display_name}`

/** The cap keeps its value while hidden, but one typed wrong and then hidden by lowering the longest run is no value: the
 *  saved one goes instead. */
function withFullRunsKept(data: UnitRulesBody, saved: UnitRulesState): UnitRulesBody {
  if (fullRuns.safeParse(data.rules.max_full_runs).success) return data
  return { ...data, rules: { ...data.rules, max_full_runs: saved.rules.max_full_runs } }
}

const NEW_HEADCOUNT = { weekday_min: 1, weekday_max: 1, weekend_min: 1, weekend_max: 1, also_counts: [] }

function ShiftsField({ form, shifts: active }: { form: UseFormReturn<UnitRulesBody>; shifts: ShiftChoice[] }) {
  const { field } = useController({ control: form.control, name: "rules.shifts" })
  /** A shift the unit stops working goes from everywhere that may name only the unit's shifts. The night and day shifts
   *  stay, because the choice of another is the manager's and their fields then say so. */
  const change = (next: string[]) => {
    const gone = (code: string) => !next.includes(code)
    field.onChange(next)
    form.setValue("rules.headcounts", form.getValues("rules.headcounts")
      .filter((row) => !gone(row.shift))
      .map((row) => ({ ...row, also_counts: row.also_counts.filter((code) => !gone(code)) })), { shouldDirty: true })
    form.setValue("rules.fair_shifts", form.getValues("rules.fair_shifts").filter((code) => !gone(code)), { shouldDirty: true })
  }
  return (
    <CodeCheckboxes id="field-rules.shifts" legend="Shifts this unit works" description={SHIFTS_DESCRIPTION}
      options={active.map((shift) => ({ code: shift.code, label: `${shiftLabel(shift)}, ${shift.hours} hours` }))}
      value={field.value} onChange={change} error={form.formState.errors.rules?.shifts as FieldError | undefined} fieldRef={field.ref} />
  )
}

function CodesField({ form, name, ...rest }: { form: UseFormReturn<UnitRulesBody>; name: `rules.headcounts.${number}.also_counts` | "rules.fair_shifts"; legend: string; description: string; options: { code: string; label: string }[]; error?: FieldError }) {
  const { field } = useController({ control: form.control, name })
  return <CodeCheckboxes id={`field-${name}`} value={field.value} onChange={field.onChange} fieldRef={field.ref} {...rest} />
}

function HeadcountsField({ form, shifts: active }: { form: UseFormReturn<UnitRulesBody>; shifts: ShiftChoice[] }) {
  const { fields, append, remove } = useFieldArray({ control: form.control, name: "rules.headcounts" })
  const rows = form.watch("rules.headcounts")
  const working = form.watch("rules.shifts")
  const blocks = useRef(new Map<string, HTMLElement>())
  const [focusIn, setFocusIn] = useState<string | null>(null)
  const label = (code: string) => {
    const shift = active.find((candidate) => candidate.code === code)
    return shift ? shiftLabel(shift) : code
  }

  // After the block has drawn what the button just changed, so focus never falls back to the page.
  useEffect(() => {
    if (focusIn) blocks.current.get(focusIn)?.querySelector<HTMLElement>("input, button")?.focus()
    if (focusIn) setFocusIn(null)
  }, [focusIn])

  if (working.length === 0) return <p className="text-sm text-muted-foreground">Choose the unit's shifts first.</p>
  return (
    <div className="flex flex-col gap-6">
      {working.map((code) => {
        const index = rows.findIndex((row) => row.shift === code)
        const rowErrors = index >= 0 ? form.formState.errors.rules?.headcounts?.[index] : undefined
        return (
          <section key={code} ref={(element) => { if (element) blocks.current.set(code, element); else blocks.current.delete(code) }}
            aria-label={label(code)} className="flex flex-col gap-3 border-t pt-4 first:border-t-0 first:pt-0">
            <h3 className="text-sm font-medium">{label(code)}</h3>
            {index < 0 ? (
              <>
                <p className="text-sm text-muted-foreground">No headcount of its own, so the team leader, gender, score and fairness rules leave it alone.</p>
                <Button type="button" variant="outline" className="self-start" aria-label={`Add a headcount for ${code}`}
                  onClick={() => { append({ shift: code, ...NEW_HEADCOUNT }); setFocusIn(code) }}>
                  Add a headcount
                </Button>
              </>
            ) : (
              // By the field array's id: a row's inputs hold their values, and removing another moves its position.
              <Fragment key={fields[index]?.id}>
                <div className="grid gap-3 sm:grid-cols-2">
                  {COUNT_FIELDS.map(({ name, label: countLabel }) => (
                    <FormField key={name} label={countLabel} type="number" inputMode="numeric"
                      registration={form.register(`rules.headcounts.${index}.${name}`, { valueAsNumber: true })} error={rowErrors?.[name]} />
                  ))}
                </div>
                {working.length > 1 && (
                  <CodesField form={form} name={`rules.headcounts.${index}.also_counts`} legend="Shifts that also count towards it"
                    description="For overlapping shifts: a nurse on one of these counts towards this shift's numbers."
                    options={working.filter((other) => other !== code).map((other) => ({ code: other, label: other }))}
                    error={rowErrors?.also_counts as FieldError | undefined} />
                )}
                <Button type="button" variant="ghost" className="self-start" aria-label={`Remove the headcount of ${code}`}
                  onClick={() => {
                    remove(index)
                    form.setValue("rules.fair_shifts", form.getValues("rules.fair_shifts").filter((other) => other !== code), { shouldDirty: true })
                    setFocusIn(code)
                  }}>
                  Remove this headcount
                </Button>
              </Fragment>
            )}
          </section>
        )
      })}
    </div>
  )
}

function RulesForm({ unitId, state }: { unitId: string; state: UnitRulesState }) {
  const queryClient = useQueryClient()
  const update = useUpdateUnitRules()
  const valuesOf = (from: UnitRulesState): UnitRulesBody => ({
    rules: from.rules as UnitRulesBody["rules"], request_cap: from.request_cap, preference_cap: from.preference_cap, default_time_limit: from.default_time_limit,
  })
  const form = useForm<UnitRulesBody>({ resolver: zodResolver(schemaFor(state.time_limit_cap)), defaultValues: valuesOf(state) })
  const { errors, isDirty } = form.formState
  const ruleErrors = errors.rules
  const asNumber = { valueAsNumber: true }
  const working = form.watch("rules.shifts")
  const rows = form.watch("rules.headcounts") as HeadcountRule[]
  const withHeadcount = working.filter((code) => rows.some((row) => row.shift === code))
  const longest = form.watch("rules.max_consecutive_shifts")

  const numberField = ({ name, label, description }: Explained<NumberRule>, step?: string) => (
    <FormField key={name} label={label} type="number" inputMode={step ? "decimal" : "numeric"} step={step} description={description}
      registration={form.register(`rules.${name}`, asNumber)} error={ruleErrors?.[name]} />
  )
  const switchField = ({ name, label, description }: Explained<SwitchRule>) => (
    <CheckboxField key={name} label={label} description={description} registration={form.register(`rules.${name}`)} />
  )

  const submit = form.handleSubmit((data) =>
    update.mutate(
      { unitId, data: withFullRunsKept(data, state) },
      {
        onSuccess: (saved) => {
          queryClient.setQueryData(getGetUnitRulesQueryKey(unitId), saved)
          void queryClient.invalidateQueries({ queryKey: getListUnitsQueryKey() })
          form.reset(valuesOf(saved))
        },
        onError: (error) => showServerErrors(form, error, formPath),
      },
    ),
  )
  const refused = update.isError && serverErrors(update.error, formPath).length > 0

  return (
    <form onSubmit={submit} noValidate className="flex flex-col gap-4">
      <Section title="Shifts">
        <FieldGroup>
          <ShiftsField form={form} shifts={state.active_shifts} />
          {NIGHT_AND_DAY.map(({ name, label, description }) => (
            <SelectField key={name} label={label} description={description} registration={form.register(`rules.${name}`)} error={ruleErrors?.[name]}>
              <NativeSelectOption value="">Choose</NativeSelectOption>
              {state.active_shifts.map((shift) => <NativeSelectOption key={shift.code} value={shift.code}>{shiftLabel(shift)}</NativeSelectOption>)}
            </SelectField>
          ))}
        </FieldGroup>
      </Section>
      <Section title="Headcounts" description={HEADCOUNTS_DESCRIPTION}>
        <FieldGroup>
          {switchField(HEADCOUNT_SWITCH)}
          <HeadcountsField form={form} shifts={state.active_shifts} />
        </FieldGroup>
      </Section>
      <Section title="Who a shift needs">
        <FieldGroup>{WHO_SWITCHES.map(switchField)}</FieldGroup>
      </Section>
      <Section title="Score targets">
        <FieldGroup>
          {SCORE_TARGETS.map((rule) => numberField(rule, "any"))}
          {switchField(SCORE_SWITCH)}
          <SelectField label="Way of balancing" description={SCORE_MODE_DESCRIPTION} registration={form.register("rules.score_balance_mode")} error={ruleErrors?.score_balance_mode}>
            {Object.entries(SCORE_MODES).map(([mode, label]) => <NativeSelectOption key={mode} value={mode}>{label}</NativeSelectOption>)}
          </SelectField>
          {SCORE_CEILINGS.map((rule) => numberField(rule, "any"))}
        </FieldGroup>
      </Section>
      <Section title="Night rest">
        <FieldGroup>
          {numberField(NIGHT_REST_DAYS)}
          {switchField(NIGHT_REST_SWITCH)}
        </FieldGroup>
      </Section>
      <Section title="Runs of shifts">
        <FieldGroup>
          {numberField(LONGEST_RUN)}
          {fullRunsApply(longest) && numberField(FULL_RUNS)}
          {numberField(AFTER_TWO_RUNS)}
          {switchField(MIXED_SWITCH)}
        </FieldGroup>
      </Section>
      <Section title="Fairness">
        <FieldGroup>
          <CodesField form={form} name="rules.fair_shifts" legend="Shifts to spread fairly" description={FAIR_SHIFTS_DESCRIPTION}
            options={withHeadcount.map((code) => ({ code, label: code }))} error={ruleErrors?.fair_shifts as FieldError | undefined} />
          {numberField(FAIR_TOLERANCE, "any")}
          {FAIR_SWITCHES.map(switchField)}
          {numberField(CARRY_CAP, "any")}
        </FieldGroup>
      </Section>
      <Section title="Weekends and switches">
        <FieldGroup>
          {LIMITS.map((rule) => numberField(rule))}
          {switchField(SWITCHES_HARD)}
        </FieldGroup>
      </Section>
      <Section title="Requests and solves">
        <FieldGroup>
          <FormField label="Requests per nurse per month" type="number" inputMode="numeric" description={REQUEST_CAP_DESCRIPTION}
            registration={form.register("request_cap", asNumber)} error={errors.request_cap} />
          <FormField label="Preferences per nurse per month" type="number" inputMode="numeric" description={PREFERENCE_CAP_DESCRIPTION}
            registration={form.register("preference_cap", asNumber)} error={errors.preference_cap} />
          <FormField label="Default time limit (seconds)" type="number" inputMode="numeric"
            description={`${TIME_LIMIT_DESCRIPTION} The System Admin's cap is ${state.time_limit_cap} seconds.`}
            registration={form.register("default_time_limit", asNumber)} error={errors.default_time_limit} />
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

const named = (codes: string[], none: string) => (codes.length ? codes.join(", ") : none)
const notChosen = "Not chosen"

function HeadcountsReadOnly({ rules }: { rules: UnitRulesAnswer }) {
  if (rules.headcounts.length === 0) return <p className="text-sm">No shift has a headcount.</p>
  return (
    <ul className="flex flex-col gap-3 text-sm">
      {rules.headcounts.map((row) => (
        <li key={row.shift} className="tabular-nums">
          <span className="font-medium">{row.shift}</span>: {row.weekday_min} to {row.weekday_max} on a weekday, {row.weekend_min} to {row.weekend_max} on a weekend day
          {row.also_counts.length > 0 && `, with ${row.also_counts.join(", ")} counting towards it`}
        </li>
      ))}
    </ul>
  )
}

function RulesReadOnly({ state }: { state: UnitRulesState }) {
  const { rules } = state
  const numbers = (items: Explained<NumberRule>[]) => items.map(({ name, label, description }) => ({ label, description, value: rules[name] }))
  const switches = (items: Explained<SwitchRule>[]) => items.map(({ name, label, description }) => ({ label, description, value: onOff(rules[name]) }))
  return (
    <div className="flex flex-col gap-4">
      <Section title="Shifts">
        <ReadOnlyList items={[
          { label: "Shifts this unit works", description: SHIFTS_DESCRIPTION, value: named(rules.shifts, "None chosen") },
          ...NIGHT_AND_DAY.map(({ name, label, description }) => ({ label, description, value: rules[name] || notChosen })),
        ]} />
      </Section>
      <Section title="Headcounts" description={HEADCOUNTS_DESCRIPTION}>
        <div className="flex flex-col gap-4">
          <ReadOnlyList items={switches([HEADCOUNT_SWITCH])} />
          <HeadcountsReadOnly rules={rules} />
        </div>
      </Section>
      <Section title="Who a shift needs"><ReadOnlyList items={switches(WHO_SWITCHES)} /></Section>
      <Section title="Score targets">
        <ReadOnlyList items={[
          ...numbers(SCORE_TARGETS),
          ...switches([SCORE_SWITCH]),
          { label: "Way of balancing", description: SCORE_MODE_DESCRIPTION, value: SCORE_MODES[rules.score_balance_mode] },
          ...numbers(SCORE_CEILINGS),
        ]} />
      </Section>
      <Section title="Night rest"><ReadOnlyList items={[...numbers([NIGHT_REST_DAYS]), ...switches([NIGHT_REST_SWITCH])]} /></Section>
      <Section title="Runs of shifts">
        <ReadOnlyList items={[
          ...numbers([LONGEST_RUN]),
          ...(fullRunsApply(rules.max_consecutive_shifts) ? numbers([FULL_RUNS]) : []),
          ...numbers([AFTER_TWO_RUNS]),
          ...switches([MIXED_SWITCH]),
        ]} />
      </Section>
      <Section title="Fairness">
        <ReadOnlyList items={[
          { label: "Shifts to spread fairly", description: FAIR_SHIFTS_DESCRIPTION, value: named(rules.fair_shifts, "None") },
          ...numbers([FAIR_TOLERANCE]),
          ...switches(FAIR_SWITCHES),
          ...numbers([CARRY_CAP]),
        ]} />
      </Section>
      <Section title="Weekends and switches"><ReadOnlyList items={[...numbers(LIMITS), ...switches([SWITCHES_HARD])]} /></Section>
      <Section title="Requests and solves">
        <ReadOnlyList items={[
          { label: "Requests per nurse per month", description: REQUEST_CAP_DESCRIPTION, value: state.request_cap },
          { label: "Preferences per nurse per month", description: PREFERENCE_CAP_DESCRIPTION, value: state.preference_cap },
          { label: "Default time limit (seconds)", description: TIME_LIMIT_DESCRIPTION, value: state.default_time_limit },
        ]} />
      </Section>
    </div>
  )
}

function ChosenUnitRules({ unitId, mayChange }: { unitId: string; mayChange: boolean }) {
  const query = useGetUnitRules(unitId)
  return (
    <>
      {query.isPending && <p>Loading…</p>}
      {query.isError && <p role="alert">The rules could not be read. Reload the page to try again.</p>}
      {query.data?.needs_review && (
        <div className="flex flex-col items-start gap-1">
          <Badge variant="secondary">Defaults, review before the first solve</Badge>
          {mayChange && <p className="text-sm">Saving this page marks them as reviewed, even with nothing changed.</p>}
        </div>
      )}
      {query.data && (mayChange
        ? <RulesForm key={unitId} unitId={unitId} state={query.data} />
        : <RulesReadOnly state={query.data} />)}
    </>
  )
}

function UnitRulesPage() {
  const { user } = useRouteContext({ from: "/_signed-in" })
  const { unit: inAddress } = Route.useSearch()
  const navigate = useNavigate({ from: Route.fullPath })
  const { units, chosen } = useChosenUnit(user, inAddress)
  const mayChange = user.role === Role.unit_manager

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-4">
      <h1 className="text-xl font-medium">{mayChange && chosen ? `Unit rules of ${chosen.name}` : "Unit rules"}</h1>
      <p className="text-muted-foreground">
        The rules this unit rosters by, on top of the hospital rules.
        {!mayChange && " Only the unit's manager can change these."}
      </p>
      {units.isPending && <p>Loading…</p>}
      {units.isError && <p role="alert">The units could not be read. Reload the page to try again.</p>}
      {units.data && !chosen && <p>{mayChange ? "No unit is assigned to you yet. The CNO assigns each unit its manager." : "There are no units yet."}</p>}
      {!mayChange && units.data && chosen && (
        <UnitPicker units={units.data} value={chosen.id} onChange={(unit) => void navigate({ search: { unit } })} />
      )}
      {chosen && <ChosenUnitRules unitId={chosen.id} mayChange={mayChange} />}
    </div>
  )
}

