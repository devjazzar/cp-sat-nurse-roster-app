export { cn } from "cn"

/** A time the API sent with the hospital's offset, as the hospital's clock read it, whatever the
 *  browser's own time zone. The audit log's date filters mean the same days. */
export function hospitalTime(iso: string): string {
  return iso.slice(0, 19).replace("T", " ")
}

/** Dates are calendar days with no time zone, so they are read and printed as UTC whatever the browser's is. */
export const asDate = (iso: string) => new Date(`${iso}T00:00:00Z`)
const monthAndYear = new Intl.DateTimeFormat("en-GB", { month: "long", year: "numeric", timeZone: "UTC" })
/** "January 2027" from "2027-01". */
export const monthName = (month: string) => monthAndYear.format(asDate(`${month}-01`))

const dayOfMonth = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "long", timeZone: "UTC" })
/** "10 November" from "2026-11-10", where the month and its year are said already. */
export const longDay = (iso: string) => dayOfMonth.format(asDate(iso))

const shortDate = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" })
/** "10 Nov 2026" from "2026-11-10". */
export const shortDay = (iso: string) => shortDate.format(asDate(iso))
/** "10 Nov 2026", "10 to 13 Nov 2026", or both in full across a month's end. */
export function dayRange(first: string, last: string): string {
  if (first === last) return shortDay(first)
  if (first.slice(0, 7) === last.slice(0, 7)) return `${asDate(first).getUTCDate()} to ${shortDay(last)}`
  return `${shortDay(first)} to ${shortDay(last)}`
}

/** "2026-12" from "2026-11" and 1. */
export function monthAfter(month: string, by: number): string {
  const day = asDate(`${month}-01`)
  day.setUTCMonth(day.getUTCMonth() + by)
  return day.toISOString().slice(0, 7)
}

/** `Table`'s container when nothing in the table can take focus, because a keyboard still has to scroll it. */
export function scrollableRegion(label: string) {
  return {
    tabIndex: 0,
    role: "region",
    "aria-label": label,
    className: "rounded-sm outline-none focus-visible:ring-3 focus-visible:ring-ring",
  }
}

/** Black or white, whichever reads better on a shift's colour ("#0284c7"), by WCAG's relative luminance. */
export function readableOn(colour: string): "#000000" | "#ffffff" {
  const [r, g, b] = [1, 3, 5].map((at) => {
    const channel = parseInt(colour.slice(at, at + 2), 16) / 255
    return channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4
  })
  const luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
  return 1.05 / (luminance + 0.05) >= (luminance + 0.05) / 0.05 ? "#ffffff" : "#000000"
}
