import { execFileSync } from "node:child_process"
import { readFileSync } from "node:fs"

import { devices, expect, type Browser, type Page } from "@playwright/test"

/** What e2e/stack.sh wrote for the stack the checks run against: where it answers, the seeded users' password, and what the
 *  seed made (e2e/seed.py). */
export type Stack = {
  project: string
  /** `web` over HTTP on localhost: the checks' origin, where a browser lets the service worker register. */
  baseURL: string
  /** Caddy in front, as a hospital reaches it, behind its self-signed certificate. */
  caddyURL: string
  password: string
  /** Each seeded user's full name, by username: the sample's nurses go by their hospital ID, the System Admin is `admin`. */
  names: Record<string, string>
  unit: string
  approved_month: string
  window_month: string
  /** A two-cell swap the app's own judging found sound: the proposer's shift goes to a colleague who is off that day. */
  swap: { proposer: string; colleague: string; date: string; shift: string }
}

function readStack(): Stack {
  const project = process.env.E2E_STACK
  if (!project) throw new Error("Set E2E_STACK to a project e2e/stack.sh started: E2E_STACK=<project> npx playwright test")
  const path = new URL(`.stack/${project}.json`, import.meta.url)
  return { project, ...JSON.parse(readFileSync(path, "utf8")) }
}

export const stack = readStack()

/** Signs in through the login page, as a person would, and waits for the page past it. */
export async function signIn(page: Page, username: string) {
  await page.goto("/login")
  await page.getByLabel("Username").fill(username)
  await page.getByLabel("Password").fill(stack.password)
  await page.getByRole("button", { name: "Log in" }).click()
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible()
  await expect(page).not.toHaveURL(/\/login/)
}

/** A phone at a width: a touch screen and a mobile Chrome's user agent. */
export const phone = (width: number, height: number) => ({ ...devices["Pixel 7"], viewport: { width, height } })

/** A second person on their own phone: a context of their own, the same size as the test's. */
export async function anotherPhone(browser: Browser, page: Page, username: string): Promise<Page> {
  const { width, height } = page.viewportSize()!
  const context = await browser.newContext({ ...phone(width, height), baseURL: stack.baseURL })
  const theirs = await context.newPage()
  await signIn(theirs, username)
  return theirs
}

/** The page itself never scrolls sideways: whatever is wider scrolls inside its own region. */
export async function expectNoSidewaysScroll(page: Page) {
  const widths = await page.evaluate(() => ({ scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth }))
  expect(widths.scroll, `${page.url()} is ${widths.scroll} px wide in a ${widths.client} px window`).toBeLessThanOrEqual(widths.client)
}

/** A control a thumb can hit: 44 px tall at least, as Apple's and WCAG's enhanced target size ask. */
export async function expectThumbSized(locator: ReturnType<Page["locator"]>) {
  const box = await locator.boundingBox()
  expect(box, "the control is on screen").not.toBeNull()
  expect(box!.height, `${await locator.textContent()} is ${box!.height} px tall`).toBeGreaterThanOrEqual(44)
}

/** e2e/stack.sh redeploy: a new marker in index.html and a changed service worker, `web` restarted. Returns the marker. */
export function redeploy(): string {
  return execFileSync(new URL("stack.sh", import.meta.url).pathname, ["redeploy", stack.project], { encoding: "utf8" }).trim()
}

/** "2026-12" as a month's name, as the pages write it. */
export const monthName = (month: string) =>
  new Intl.DateTimeFormat("en-GB", { month: "long", year: "numeric", timeZone: "UTC" }).format(new Date(`${month}-01T00:00:00Z`))
/** "2026-12-01" as the pages write a date: "1 Dec 2026". */
export const shortDay = (iso: string) =>
  new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" }).format(new Date(`${iso}T00:00:00Z`))
