import type { ReactNode } from "react"
import { z } from "zod"

import { buttonVariants } from "@/components/ui/button"
import { cn, monthAfter, monthName } from "@/lib/utils"

/** A month in the address. A hand-edited one is dropped rather than sent: the API would refuse it. */
export const monthInAddress = z.string().regex(/^\d{4}-(0[1-9]|1[0-2])$/).optional().catch(undefined)

/** How a link looks here, for a page's `link`. */
export const MONTH_LINK = cn(buttonVariants({ variant: "outline", size: "sm" }))

/** The month a page shows, with links either side, so the month stays in the address and focus stays on the link. The
 *  page draws its own links, because only it knows its route and what else its address holds. */
export function MonthNav({ month, link }: { month: string; link: (month: string, label: string) => ReactNode }) {
  return (
    <nav aria-label="Month" className="flex flex-wrap items-center gap-x-3 gap-y-2">
      {link(monthAfter(month, -1), "Previous month")}
      <h2 className="text-base font-medium tabular-nums">{monthName(month)}</h2>
      {link(monthAfter(month, 1), "Next month")}
    </nav>
  )
}
