import type { UnitSolveRow } from "@/api/generated/model"

import { longDay } from "@/lib/utils"

/** What the unit's history and the System Admin's both say of a solve. The System Admin's row has nothing of a re-plan. */
export type SolveRow = Omit<UnitSolveRow, "in_draft" | "replan_from" | "replan_outcome">

/** What a re-plan's end did to the roster in force, in a few words, once it kept a roster. */
const REPLAN_ENDED: Record<NonNullable<UnitSolveRow["replan_outcome"]>, string> = {
  version: "in force",
  unchanged: "nothing changed",
  outdated: "not applied, the roster changed meanwhile",
  month_over: "not applied, the month had ended",
}

/** A re-plan's end, named as one, for the manager's history. */
export function replanStatus(row: Pick<UnitSolveRow, "state" | "failure" | "found_roster" | "replan_from" | "replan_outcome">): string {
  const ended = row.replan_outcome ? REPLAN_ENDED[row.replan_outcome] : solveStatus(row).toLowerCase()
  const stopped = row.state === "cancelled" && row.replan_outcome === "version" ? "stopped, " : ""
  return `Re-plan from ${longDay(row.replan_from!)}: ${stopped}${ended}`
}

/** A solve's end, in the manager's words. "Refused" is a matter of the rules and never reads as a failed solve. */
export function solveStatus({ state, failure, found_roster }: Pick<SolveRow, "state" | "failure" | "found_roster">): string {
  if (state === "queued") return "In the queue"
  if (state === "running") return "Solving"
  if (state === "failed") return failure === "refused" ? "Rules to review" : "Failed"
  if (state === "cancelled") return found_roster ? "Stopped, roster kept" : "Stopped, no roster"
  return found_roster ? "Finished" : "No roster to keep"
}

/** How long it searched. */
export function solveDuration({ attempts, elapsed_seconds }: Pick<SolveRow, "attempts" | "elapsed_seconds">): string {
  if (attempts === 0) return "Did not start"
  const seconds = Math.round(elapsed_seconds)
  return seconds < 60 ? `${seconds} s` : `${Math.floor(seconds / 60)} min ${seconds % 60} s`
}

const STOPPED_BY: Record<string, string> = {
  proof: "It proved no better roster exists",
  time_limit: "The time limit",
  cancelled: "It was stopped by hand",
}
/** What ended a search. An unknown word from a later solver is still readable. */
export const stoppedBy = (word: string | null) => (word ? STOPPED_BY[word] ?? word : "Unknown")
