import type { ThrottleRefusal } from "@/api/generated/model"

/** The 429 of the login and Change password: too many failed logins from the client's address (the throttle). The time
 *  is read off the server's answer, which carries the hospital's offset, so it is the hospital's clock whatever the
 *  browser's time zone. */
export function throttledWords(refusal: ThrottleRefusal): string {
  return `Too many failed logins from this network. Try again at ${refusal.throttled_until.slice(11, 16)}.`
}
