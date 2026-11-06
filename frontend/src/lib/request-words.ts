import type { MyRequestRowState, RequestStepRow } from "@/api/generated/model"

/** What a request asked for, or promises: a shift's code, or "" for a day off. */
export function askedFor(code: string, names: Record<string, string> = {}): string {
  if (!code) return "A day off"
  return names[code] ? `${names[code]} (${code})` : code
}

/** The same within a sentence: "a day off", or the shift's name as it is ("Night (N)"). */
export const inSentence = (code: string, names: Record<string, string> = {}) => (code ? askedFor(code, names) : "a day off")

/** Said to the nurse whose request it is. */
export const MY_STATE: Record<MyRequestRowState, string> = {
  pending: "Waiting for a decision",
  accepted: "Accepted",
  rejected: "Rejected",
  withdrawn: "Withdrawn",
  cancelled: "Cancelled after it was accepted",
  replaced_by_leave: "Replaced by your leave",
  expired: "Expired",
}

/** Said to the unit's manager. */
export const UNIT_STATE: Record<MyRequestRowState, string> = {
  ...MY_STATE,
  replaced_by_leave: "Replaced by leave",
}

/** The manager's latest step on it (a decision, an edit, a cancel) or leave replacing it, whose reason is the one to read. */
export function lastDecision(steps: RequestStepRow[]): RequestStepRow | undefined {
  return [...steps].reverse().find((step) => step.step !== "made" && step.step !== "withdrawn")
}

/** The nurse's own reason, given when she made it. */
export const herReason = (steps: RequestStepRow[]) => steps.find((step) => step.step === "made")?.reason ?? ""

export const shiftNames = (shifts: { code: string; display_name: string }[]): Record<string, string> =>
  Object.fromEntries(shifts.map((shift) => [shift.code, shift.display_name]))

export const NO_CONNECTION = "That did not work. Check your connection and try again."
