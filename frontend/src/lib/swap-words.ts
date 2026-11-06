import type { MySwapRowState, SwapColleagueAnswer } from "@/api/generated/model"

/** A cell as a swap shows it: a shift's name with its code, or Off for a day not worked, which is all a colleague's leave
 *  ever reads as. */
export function cellWords(code: string, names: Record<string, string> = {}): string {
  if (!code) return "Off"
  return names[code] ? `${names[code]} (${code})` : code
}

export const SWAP_STATE: Record<MySwapRowState, string> = {
  pending: "Waiting for its colleagues",
  awaiting_manager: "Waiting for the manager",
  approved: "Approved",
  rejected: "Rejected",
  withdrawn: "Withdrawn",
  expired: "Expired",
}

export const ANSWER: Record<SwapColleagueAnswer, string> = {
  pending: "not answered yet",
  accepted: "accepted",
  rejected: "rejected",
}

/** A swap still waiting on its colleagues or the manager. */
export const WAITING: MySwapRowState[] = ["pending", "awaiting_manager"]
