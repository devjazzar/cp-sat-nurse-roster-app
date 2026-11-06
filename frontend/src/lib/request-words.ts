import type { RequestStepRow } from "@/api/generated/model"

/** What a request asked for, or promises: a shift's code, or "" for a day off. */
export function askedFor(code: string, names: Record<string, string> = {}): string {
  if (!code) return "A day off"
  return names[code] ? `${names[code]} (${code})` : code
}

/** Said to the nurse whose request it is. */
export const MY_STATE: Record<string, string> = {
  pending: "Waiting for a decision",
  accepted: "Accepted",
  rejected: "Rejected",
  withdrawn: "Withdrawn",
  cancelled: "Cancelled after it was accepted",
  replaced_by_leave: "Replaced by your leave",
}

/** Said to the unit's manager. */
export const UNIT_STATE: Record<string, string> = {
  ...MY_STATE,
  replaced_by_leave: "Replaced by leave",
}

/** The latest step with a reason the manager gave: the decision a nurse wants to read. */
export function lastDecision(steps: RequestStepRow[]): RequestStepRow | undefined {
  return [...steps].reverse().find((step) => step.step !== "made" && step.step !== "withdrawn")
}

/** The nurse's own reason, given when she made it. */
export const herReason = (steps: RequestStepRow[]) => steps.find((step) => step.step === "made")?.reason ?? ""
