export { cn } from "cn"

/** A time the API sent with the hospital's offset, as the hospital's clock read it, whatever the
 *  browser's own time zone. The audit log's date filters mean the same days. */
export function hospitalTime(iso: string): string {
  return iso.slice(0, 19).replace("T", " ")
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
