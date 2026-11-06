import { execFileSync } from "node:child_process"
import { existsSync, readFileSync, writeFileSync } from "node:fs"

import { devices, expect, type Browser, type BrowserContextOptions, type Locator, type Page } from "@playwright/test"

/** What e2e/stack.sh wrote for a stack the checks run against: where it answers, the seeded users' password, and what the
 *  seed made (e2e/seed.py). An `--empty` stack has no seed: only its System Admin's first password. */
export type Stack = {
  project: string
  /** `web` over HTTP on localhost: the checks' origin, where a browser lets the service worker register. */
  baseURL: string
  /** Caddy in front, as a hospital reaches it, behind its self-signed certificate. */
  caddyURL: string
  seeded: boolean
  password: string
  /** INITIAL_ADMIN_PASSWORD: the System Admin's until the forced change at the first login. */
  initialAdminPassword: string
  /** Each seeded user's full name, by username: the sample's nurses go by their hospital ID, the System Admin is `admin`. */
  names: Record<string, string>
  unit: string
  /** Sixty-four nurses, one of them its manager Omar: a grid long enough to be windowed. */
  large_unit: string
  /** Last month, approved for ER and not closed when seeded. */
  past_month: string
  approved_month: string
  window_month: string
  /** A two-cell swap the app's own judging found sound: the proposer's shift goes to a colleague who is off that day. */
  swap: Swap
}

export type Swap = { proposer: string; colleague: string; date: string; shift: string }

function readStack(variable: string): Stack | undefined {
  const project = process.env[variable]
  if (!project) return undefined
  const path = new URL(`.stack/${project}.json`, import.meta.url)
  return { project, ...JSON.parse(readFileSync(path, "utf8")) }
}

/** A stack named by an environment variable, read once; touching it without the variable says what to set. */
function stackFrom(variable: string, what: string): Stack {
  const read = readStack(variable)
  return read ?? new Proxy({} as Stack, {
    get: (_, key) => {
      if (key === "then") return undefined
      throw new Error(`Set ${variable} to ${what}: ${variable}=<project> npx playwright test`)
    },
  })
}

/** The seeded stack (`e2e/stack.sh up <project>`): ticket 23's checks and ticket 24's that need data to start from. */
export const stack = stackFrom("E2E_STACK", "a project e2e/stack.sh up started")
/** The empty stack (`e2e/stack.sh up <project> --empty`) the journeys start from. */
export const journeyStack = stackFrom("E2E_JOURNEY_STACK", "a project e2e/stack.sh up --empty started")
export const has = { seeded: !!process.env.E2E_STACK, journey: !!process.env.E2E_JOURNEY_STACK }

/** Signs in through the login page, as a person would, and waits for the page past it. Whoever was signed in on this browser
 *  before is not any more: the login page sends a signed-in browser home. */
export async function signIn(page: Page, username: string, password = stack.password) {
  await page.context().clearCookies()
  await page.goto("/login")
  await page.getByLabel("Username").fill(username)
  await page.getByLabel("Password").fill(password)
  await page.getByRole("button", { name: "Log in" }).click()
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible()
  await expect(page).not.toHaveURL(/\/login/)
}

/** A first login with a password someone was given: the app asks for a new one before anything else, then goes home.
 *  Returns the new password. */
export async function firstSignIn(page: Page, username: string, given: string): Promise<string> {
  const chosen = `${username}-${Math.random().toString(36).slice(2, 10)}-Rota!`
  await page.context().clearCookies()
  await page.goto("/login")
  await page.getByLabel("Username").fill(username)
  await page.getByLabel("Password").fill(given)
  await page.getByRole("button", { name: "Log in" }).click()
  await expect(page.getByRole("heading", { level: 1, name: "Choose a new password" })).toBeVisible()
  await expect(page.getByText("You must replace the password you were given before going on.")).toBeVisible()
  await page.getByLabel("Current password").fill(given)
  await page.getByLabel("New password", { exact: true }).fill(chosen)
  await page.getByLabel("Repeat the new password").fill(chosen)
  await page.getByRole("button", { name: "Change password" }).click()
  await expect(page).not.toHaveURL(/\/change-password/)
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible()
  return chosen
}

/** Opens one of the role's pages from the header, as a person would: the one-row links on a wide screen, the Menu on a phone. */
export async function go(page: Page, name: string) {
  const menu = page.getByRole("button", { name: "Menu" })
  if (await menu.isVisible()) {
    await menu.click()
    await page.getByRole("navigation", { name: "Main menu" }).getByRole("link", { name, exact: true }).click()
  } else {
    await page.getByRole("navigation", { name: "Main", exact: true }).getByRole("link", { name, exact: true }).click()
  }
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible()
  await expect(page.getByText("Loading…")).toHaveCount(0)
  // On a phone, no page a journey opens makes the page itself scroll sideways.
  if (page.viewportSize()!.width < 640) await expectNoSidewaysScroll(page)
}

/** Chooses the one option of a select whose words match, whatever else its label says ("Rana Haddad (rana)"). */
export async function choose(select: Locator, words: RegExp) {
  const labels = (await select.locator("option").allTextContents()).filter((label) => words.test(label))
  expect(labels, `one option of ${await select.getAttribute("id")} matches ${words}`).toHaveLength(1)
  await select.selectOption({ label: labels[0] })
}

/** A desktop browser: a mouse, a 1280 × 800 window. */
export const desktop = { ...devices["Desktop Chrome"], viewport: { width: 1280, height: 800 } }
/** A phone at a width: a touch screen and a mobile Chrome's user agent. */
export const phone = (width: number, height: number) => ({ ...devices["Pixel 7"], viewport: { width, height } })

/** A browser of someone else's, the same kind and size as the test's, not yet signed in. */
export async function newBrowser(browser: Browser, page: Page, baseURL: string): Promise<Page> {
  const { width, height } = page.viewportSize()!
  const options: BrowserContextOptions = width < 640 ? phone(width, height) : { ...desktop, viewport: { width, height } }
  const context = await browser.newContext({ ...options, baseURL })
  return context.newPage()
}

/** Someone else on a browser of their own, the same kind and size as the test's, signed in on the seeded stack. */
export async function another(browser: Browser, page: Page, username: string): Promise<Page> {
  const theirs = await newBrowser(browser, page, stack.baseURL)
  await signIn(theirs, username)
  return theirs
}

/** A second person on their own phone: a context of their own, the same size as the test's. */
export const anotherPhone = (browser: Browser, page: Page, username: string) => another(browser, page, username)

/** The page itself never scrolls sideways: whatever is wider scrolls inside its own region. */
export async function expectNoSidewaysScroll(page: Page) {
  const widths = await page.evaluate(() => ({ scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth }))
  expect(widths.scroll, `${page.url()} is ${widths.scroll} px wide in a ${widths.client} px window`).toBeLessThanOrEqual(widths.client)
}

/** A control a thumb can hit: 44 px tall at least, as Apple's and WCAG's enhanced target size ask. */
export async function expectThumbSized(locator: Locator) {
  const box = await locator.boundingBox()
  expect(box, "the control is on screen").not.toBeNull()
  expect(box!.height, `${await locator.textContent()} is ${box!.height} px tall`).toBeGreaterThanOrEqual(44)
}

const stackScript = new URL("stack.sh", import.meta.url).pathname
const run = (...args: string[]) => execFileSync(stackScript, args, { encoding: "utf8" }).trim()

/** e2e/stack.sh redeploy: a new marker in index.html and a changed service worker, `web` restarted. Returns the marker. */
export const redeploy = (): string => run("redeploy", stack.project)
/** e2e/stack.sh reset: the empty stack's database emptied again, as on a first start. */
export const reset = (on: Stack) => run("reset", on.project)
/** e2e/stack.sh clock: the hospital's date moved by a number of days from the real one, for web and the worker. */
export const moveClock = (on: Stack, days: number) => run("clock", on.project, String(days))
/** e2e/stack.sh fire: a periodic job run now by the stack's own worker, and waited for. */
export const fire = (on: Stack, task: string) => run("fire", on.project, task)
/** e2e/stack.sh swap: a sound two-cell swap on a unit's approved month as the roster in force stands now, from tomorrow or
 *  from a later date. */
export const soundSwap = (on: Stack, unit: string, month: string, from = ""): Swap => JSON.parse(run("swap", on.project, unit, month, from))
/** A compose command on a stack, as e2e/stack.sh runs them: `compose(stack, "stop", "solver")`. */
export function compose(on: Stack, ...args: string[]) {
  const here = new URL(".", import.meta.url).pathname
  return execFileSync("docker", ["compose", ...args], {
    encoding: "utf8",
    env: { ...process.env, COMPOSE_PROJECT_NAME: on.project, COMPOSE_FILE: `${here}../deploy/compose.yaml:${here}compose.e2e.yaml`,
      COMPOSE_ENV_FILES: `${here}.stack/${on.project}.env` },
  }).trim()
}

/** What a journey keeps between its checks: who was made, with the password they chose. In e2e/.stack, gitignored. */
export class Notebook<T extends object> {
  constructor(private readonly on: Stack, private readonly name: string) {}
  private get path() { return new URL(`.stack/${this.on.project}.${this.name}.json`, import.meta.url) }
  read(): T {
    if (!existsSync(this.path)) throw new Error(`Nothing written yet in ${this.path.pathname}: run the journey first`)
    return JSON.parse(readFileSync(this.path, "utf8"))
  }
  write(entries: Partial<T>) {
    const before = existsSync(this.path) ? JSON.parse(readFileSync(this.path, "utf8")) : {}
    writeFileSync(this.path, JSON.stringify({ ...before, ...entries }, null, 2), { mode: 0o600 })
  }
  clear() { writeFileSync(this.path, "{}", { mode: 0o600 }) }
}

/** Today on the hospital's clock as the stacks keep it (TIME_ZONE, Asia/Riyadh by default), unmoved: "2026-11-07". */
export const hospitalToday = (days = 0) => {
  const today = new Intl.DateTimeFormat("en-CA", { timeZone: process.env.TIME_ZONE ?? "Asia/Riyadh" }).format(new Date())
  return addDays(today, days)
}
/** An ISO date some days on: "2026-11-07", 3 → "2026-11-10". */
export function addDays(iso: string, days: number) {
  const day = new Date(`${iso}T00:00:00Z`)
  day.setUTCDate(day.getUTCDate() + days)
  return day.toISOString().slice(0, 10)
}
/** The day before a month begins: "2027-01" → "2026-12-31". */
export const dayBefore = (month: string) => addDays(`${month}-01`, -1)

/** "2026-12" as a month's name, as the pages write it. */
export const monthName = (month: string) =>
  new Intl.DateTimeFormat("en-GB", { month: "long", year: "numeric", timeZone: "UTC" }).format(new Date(`${month}-01T00:00:00Z`))
/** "2026-12-01" as the pages write a date: "1 Dec 2026". */
export const shortDay = (iso: string) =>
  new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" }).format(new Date(`${iso}T00:00:00Z`))
/** "2026-12-02" as a version's reason writes a date: "2 December 2026". */
export const longDay = (iso: string) =>
  new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "long", year: "numeric", timeZone: "UTC" }).format(new Date(`${iso}T00:00:00Z`))
/** A month's first day, `months` after the one of an ISO date: "2026-11-07", 1 → "2026-12". */
export function monthAfter(iso: string, months: number) {
  const day = new Date(`${iso.slice(0, 7)}-01T00:00:00Z`)
  day.setUTCMonth(day.getUTCMonth() + months)
  return day.toISOString().slice(0, 7)
}
/** Whole days from one ISO date to another. */
export const daysBetween = (from: string, to: string) =>
  Math.round((Date.parse(`${to}T00:00:00Z`) - Date.parse(`${from}T00:00:00Z`)) / 86_400_000)
