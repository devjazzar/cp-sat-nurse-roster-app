export { cn } from "cn"

/** A time the API sent with the hospital's offset, as the hospital's clock read it, whatever the
 *  browser's own time zone. The audit log's date filters mean the same days. */
export function hospitalTime(iso: string): string {
  return iso.slice(0, 19).replace("T", " ")
}
