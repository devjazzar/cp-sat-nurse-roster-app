import { QueryClientProvider } from "@tanstack/react-query"
import { createMemoryHistory, RouterProvider } from "@tanstack/react-router"
import { act, render, screen, waitFor, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, describe, expect, it, vi } from "vitest"

import { createAppRouter, createQueryClient } from "./router"

/** The real routes, the real generated client and the real fetcher, with only `fetch` replaced. */
type Answer = { status?: number; body?: unknown }
type Handler = (request: { url: string; method: string; body: unknown }) => Answer

const ME = { username: "admin", full_name: "System Admin", role: "system_admin", must_change_password: false }
const FORCED = { ...ME, must_change_password: true }
const NURSE = { ...ME, username: "h123", role: "staff_nurse" }
const SETTINGS = { time_limit_cap_seconds: 300, backup_time: "02:00", backup_retention_days: 30, close_time: "00:30" }
const HEALTH = {
  database: true,
  solver: { reachable: true, version: "0.1.0", workers: 8 },
  database_size_bytes: 5 * 1024 * 1024,
  disk: { total_bytes: 100 * 1024 ** 3, free_bytes: 60 * 1024 ** 3 },
  queue: { waiting: 2, running: 1, failed: 3, workers: 1 },
  last_backup: null,
}

function start(path: string, handlers: Record<string, Handler | Answer>) {
  const calls: { url: string; method: string; body: unknown; headers: Headers }[] = []
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init: RequestInit = {}) => {
      const method = init.method ?? "GET"
      const body = init.body ? JSON.parse(init.body as string) : undefined
      calls.push({ url, method, body, headers: new Headers(init.headers) })
      // An exact match first, then one that ignores the query string.
      const handler = handlers[`${method} ${url}`] ?? handlers[`${method} ${url.split("?")[0]}`]
      if (!handler) throw new Error(`no answer for ${method} ${url}`)
      const answer = typeof handler === "function" ? handler({ url, method, body }) : handler
      const status = answer.status ?? 200
      return new Response(status === 204 ? null : JSON.stringify(answer.body ?? {}), { status })
    }),
  )
  const queryClient = createQueryClient()
  queryClient.setDefaultOptions({ queries: { retry: false } })
  const router = createAppRouter(queryClient, createMemoryHistory({ initialEntries: [path] }))
  render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
  return { router, calls, user: userEvent.setup() }
}

const session = (user: unknown) => ({ "GET /api/auth/session": { body: { user } } })
const admin = (extra = {}) => ({
  ...session(ME),
  "GET /api/ops/health": { body: HEALTH },
  "GET /api/ops/technical-settings": { body: SETTINGS },
  ...extra,
})

afterEach(() => {
  vi.unstubAllGlobals()
  document.cookie = "csrftoken=; expires=Thu, 01 Jan 1970 00:00:00 GMT"
})

describe("route guards", () => {
  it.each(["/", "/health", "/settings", "/users", "/audit-log", "/hospital-rules", "/shifts", "/leave-types", "/holidays", "/units", "/change-password"])("%s sends a stranger to the login page", async (path) => {
    const { router } = start(path, session(null))

    expect(await screen.findByRole("button", { name: "Log in" })).toBeInTheDocument()
    expect(router.state.location.pathname).toBe("/login")
  })

  it.each(["/", "/health", "/settings", "/users", "/audit-log", "/hospital-rules", "/shifts", "/leave-types", "/holidays", "/units"])("%s sends a forced change to the password page", async (path) => {
    const { router } = start(path, session(FORCED))

    expect(await screen.findByText("Choose a new password")).toBeInTheDocument()
    expect(router.state.location.pathname).toBe("/change-password")
  })

  it("the System Admin's home is the health page", async () => {
    const { router } = start("/", admin())

    expect(await screen.findByRole("heading", { name: "Health" })).toBeInTheDocument()
    expect(router.state.location.pathname).toBe("/health")
  })

  it("the login page sends someone already signed in home", async () => {
    const { router } = start("/login", admin())

    expect(await screen.findByRole("heading", { name: "Health" })).toBeInTheDocument()
    expect(router.state.location.pathname).toBe("/health")
  })

  it.each(["/health", "/settings", "/users", "/audit-log", "/units"])("%s is not for another role", async (path) => {
    const { router, calls } = start(path, session(NURSE))

    expect(await screen.findByText(/approved roster will be shown here/)).toBeInTheDocument()
    expect(router.state.location.pathname).toBe("/")
    expect(screen.queryByRole("link", { name: "Technical settings" })).not.toBeInTheDocument()
    expect(calls.map((call) => call.url)).toEqual(["/api/auth/session"])
  })

  it("says so when the application cannot be reached", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => { throw new TypeError("network down") }))
    const queryClient = createQueryClient()
    queryClient.setDefaultOptions({ queries: { retry: false } })
    const router = createAppRouter(queryClient, createMemoryHistory({ initialEntries: ["/"] }))
    render(
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>,
    )

    expect(await screen.findByRole("alert")).toHaveTextContent("cannot be reached")
  })
})

describe("arriving on a page", () => {
  it("names the page in the title and moves focus to the new page", async () => {
    const { user } = start("/health", admin())
    await screen.findByText("Solver")
    expect(document.title).toBe("Health · Nurse roster")
    // Not on the first load: the keyboard starts from the top of the page.
    expect(document.activeElement).toBe(document.body)

    await user.click(screen.getByRole("link", { name: "Technical settings" }))

    await screen.findByLabelText("Backup time")
    await waitFor(() => expect(document.title).toBe("Technical settings · Nurse roster"))
    await waitFor(() => expect(document.activeElement).toBe(screen.getByRole("main")))
  })

  it("the login page keeps focus on its first field and has a heading", async () => {
    start("/login", session(null))

    expect(await screen.findByLabelText("Username")).toHaveFocus()
    expect(screen.getByRole("heading", { level: 1, name: "Nurse roster" })).toBeInTheDocument()
    await waitFor(() => expect(document.title).toBe("Log in · Nurse roster"))
  })

  it("shows that it is loading while the session is read", async () => {
    vi.stubGlobal("fetch", vi.fn(() => new Promise(() => {})))
    const queryClient = createQueryClient()
    const router = createAppRouter(queryClient, createMemoryHistory({ initialEntries: ["/"] }))
    render(
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>,
    )

    expect(await screen.findByText("Loading…")).toBeInTheDocument()
  })

  it("a page that does not exist offers the way home", async () => {
    start("/no-such-page", session(ME))

    expect(await screen.findByText("There is no such page.")).toBeInTheDocument()
    expect(screen.getByRole("link", { name: "Go to the home page" })).toHaveAttribute("href", "/")
  })
})

describe("login", () => {
  async function fill(user: ReturnType<typeof userEvent.setup>, username = "admin", password = "secret-password") {
    await user.type(await screen.findByLabelText("Username"), username)
    await user.type(screen.getByLabelText("Password"), password)
    await user.click(screen.getByRole("button", { name: "Log in" }))
  }

  it("posts the credentials with the CSRF token and lands on the home page", async () => {
    document.cookie = "csrftoken=the-token"
    const { user, calls, router } = start("/login", admin({
      ...session(null),
      "POST /api/auth/login": { body: ME },
    }))

    await fill(user)

    expect(await screen.findByRole("heading", { name: "Health" })).toBeInTheDocument()
    expect(router.state.location.pathname).toBe("/health")
    const post = calls.find((call) => call.method === "POST")!
    expect(post.body).toEqual({ username: "admin", password: "secret-password" })
    expect(post.headers.get("X-CSRFToken")).toBe("the-token")
  })

  it("a forced change lands on the password page", async () => {
    const { user, router } = start("/login", { ...session(null), "POST /api/auth/login": { body: FORCED } })

    await fill(user)

    expect(await screen.findByText("Choose a new password")).toBeInTheDocument()
    expect(router.state.location.pathname).toBe("/change-password")
  })

  it("shows a wrong password and stays", async () => {
    const { user, router } = start("/login", {
      ...session(null),
      "POST /api/auth/login": { status: 401, body: { detail: "Wrong username or password." } },
    })

    await fill(user)

    expect(await screen.findByRole("alert")).toHaveTextContent("Wrong username or password")
    expect(router.state.location.pathname).toBe("/login")
  })

  it("shows the lock", async () => {
    const { user } = start("/login", {
      ...session(null),
      "POST /api/auth/login": { status: 423, body: { detail: "locked", locked_until: "2026-11-05T10:15:00Z" } },
    })

    await fill(user)

    expect(await screen.findByRole("alert")).toHaveTextContent(/locked until/)
  })

  it("asks for both fields before calling anything", async () => {
    const { user, calls } = start("/login", session(null))

    await user.click(await screen.findByRole("button", { name: "Log in" }))

    expect(await screen.findByText("Enter your username.")).toBeInTheDocument()
    expect(screen.getByText("Enter your password.")).toBeInTheDocument()
    expect(calls.filter((call) => call.method === "POST")).toEqual([])
  })
})

describe("logout", () => {
  it("ends the session and forgets what was on screen", async () => {
    const { user, router, calls } = start("/health", admin({ "POST /api/auth/logout": { status: 204 } }))

    await user.click(await screen.findByRole("button", { name: "Log out" }))

    expect(await screen.findByRole("button", { name: "Log in" })).toBeInTheDocument()
    expect(router.state.location.pathname).toBe("/login")
    expect(calls.some((call) => call.method === "POST" && call.url === "/api/auth/logout")).toBe(true)
  })

  it("is available during a forced change", async () => {
    const { user } = start("/change-password", { ...session(FORCED), "POST /api/auth/logout": { status: 204 } })

    await user.click(await screen.findByRole("button", { name: "Log out" }))

    expect(await screen.findByRole("button", { name: "Log in" })).toBeInTheDocument()
  })
})

describe("an expired session", () => {
  it("a 401 on a page sends the user to the login page", async () => {
    const { router } = start("/health", { ...session(ME), "GET /api/ops/health": { status: 401, body: { detail: "Unauthorized" } } })

    expect(await screen.findByRole("button", { name: "Log in" })).toBeInTheDocument()
    expect(router.state.location.pathname).toBe("/login")
  })
})

describe("changing the password", () => {
  async function fill(user: ReturnType<typeof userEvent.setup>, current: string, next: string, repeat = next) {
    await user.type(await screen.findByLabelText("Current password"), current)
    await user.type(screen.getByLabelText("New password"), next)
    await user.type(screen.getByLabelText("Repeat the new password"), repeat)
    await user.click(screen.getByRole("button", { name: "Change password" }))
  }

  it("clears the force and goes home", async () => {
    const { user, calls, router } = start("/change-password", admin({
      ...session(FORCED),
      "POST /api/auth/change-password": { body: ME },
    }))

    await fill(user, "one-time-password", "a-brand-new-passphrase")

    expect(await screen.findByRole("heading", { name: "Health" })).toBeInTheDocument()
    expect(router.state.location.pathname).toBe("/health")
    expect(calls.find((call) => call.method === "POST")!.body).toEqual({
      current_password: "one-time-password",
      new_password: "a-brand-new-passphrase",
    })
  })

  it("shows the server's policy refusal on the field", async () => {
    const { user, router } = start("/change-password", {
      ...session(FORCED),
      "POST /api/auth/change-password": {
        status: 400,
        body: { current_password: [], new_password: ["This password is too common."] },
      },
    })

    await fill(user, "one-time-password", "password1234")

    const refusal = await screen.findByText("This password is too common.")
    expect(router.state.location.pathname).toBe("/change-password")
    const field = screen.getByLabelText("New password")
    await waitFor(() => expect(field).toHaveFocus())
    expect(field).toHaveAttribute("aria-invalid", "true")
    expect(field.getAttribute("aria-describedby")?.split(" ")).toContain(refusal.id)
  })

  it("after a refusal the user can try again with a better password", async () => {
    let attempts = 0
    const { user, router } = start("/change-password", admin({
      ...session(FORCED),
      "POST /api/auth/change-password": () =>
        attempts++ === 0
          ? { status: 400, body: { current_password: [], new_password: ["This password is too common."] } }
          : { body: ME },
    }))

    await fill(user, "one-time-password", "password1234")
    await screen.findByText("This password is too common.")
    await user.clear(screen.getByLabelText("New password"))
    await user.type(screen.getByLabelText("New password"), "a-brand-new-passphrase")
    await user.clear(screen.getByLabelText("Repeat the new password"))
    await user.type(screen.getByLabelText("Repeat the new password"), "a-brand-new-passphrase{Enter}")

    expect(await screen.findByRole("heading", { name: "Health" })).toBeInTheDocument()
    expect(router.state.location.pathname).toBe("/health")
    expect(attempts).toBe(2)
  })

  it("shows a wrong current password on its field", async () => {
    const { user } = start("/change-password", {
      ...session(FORCED),
      "POST /api/auth/change-password": {
        status: 400,
        body: { current_password: ["This is not your current password."], new_password: [] },
      },
    })

    await fill(user, "nope", "a-brand-new-passphrase")

    expect(await screen.findByText("This is not your current password.")).toBeInTheDocument()
  })

  it("refuses a short password and a mismatch without calling anything", async () => {
    const { user, calls } = start("/change-password", session(FORCED))

    await fill(user, "one-time-password", "short", "different")

    expect(await screen.findByText("Use at least 10 characters.")).toBeInTheDocument()
    expect(screen.getByText("The two passwords differ.")).toBeInTheDocument()
    expect(calls.filter((call) => call.method === "POST")).toEqual([])
  })

  it("offers a way back when it is not forced", async () => {
    start("/change-password", session(ME))

    expect(await screen.findByText("Change your password")).toBeInTheDocument()
    expect(screen.getByRole("link", { name: "Back to home" })).toBeInTheDocument()
  })
})

describe("the health page", () => {
  it("shows the solver, the queue, the disk and the database size", async () => {
    start("/health", admin())

    expect(await screen.findByText("Solver")).toBeInTheDocument()
    expect(screen.getByRole("heading", { level: 2, name: "Services" })).toBeInTheDocument()
    expect(screen.getAllByText("Reachable")).toHaveLength(2)
    expect(screen.getByText("0.1.0")).toBeInTheDocument()
    expect(screen.getByText("Jobs waiting").nextSibling).toHaveTextContent("2")
    expect(screen.getByText("Jobs running").nextSibling).toHaveTextContent("1")
    expect(screen.getByText("Jobs failed").nextSibling).toHaveTextContent("3")
    expect(screen.getByText("Workers alive").nextSibling).toHaveTextContent("1")
    expect(screen.getByText("Database size").nextSibling).toHaveTextContent("5.0 MB")
    expect(screen.getByText("Disk free").nextSibling).toHaveTextContent("60.0 GB")
    expect(screen.getByText("Disk size").nextSibling).toHaveTextContent("100 GB")
    expect(screen.getByText("Last backup").nextSibling).toHaveTextContent("None yet")
  })

  it("shows a solver that is down and a disk it could not read", async () => {
    start("/health", admin({
      "GET /api/ops/health": {
        body: { ...HEALTH, solver: { reachable: false, version: null, workers: null }, disk: null },
      },
    }))

    expect(await screen.findByText("Unreachable")).toBeInTheDocument()
    expect(screen.getByText("Disk").nextSibling).toHaveTextContent("Unknown")
  })

  it("does not poll; Refresh reads it again", async () => {
    const { user, calls } = start("/health", admin())
    await screen.findByText("Solver")
    const reads = () => calls.filter((call) => call.url === "/api/ops/health").length
    expect(reads()).toBe(1)

    await user.click(screen.getByRole("button", { name: "Refresh" }))

    await waitFor(() => expect(reads()).toBe(2))
    expect(screen.getByRole("button", { name: "Refresh" })).toHaveFocus()
    expect(await screen.findByText("Checked.")).toHaveAttribute("role", "status")
  })

  it("says so when the health cannot be read", async () => {
    start("/health", admin({ "GET /api/ops/health": { status: 500, body: {} } }))

    expect(await screen.findByRole("alert")).toHaveTextContent("Refresh to try again")
  })
})

describe("the technical settings page", () => {
  it("shows the current values and saves a change", async () => {
    const saved = { ...SETTINGS, time_limit_cap_seconds: 600, close_time: "01:00" }
    const { user, calls } = start("/settings", admin({ "PUT /api/ops/technical-settings": { body: saved } }))

    const cap = await screen.findByLabelText("Time limit cap (seconds)")
    expect(cap).toHaveValue(300)
    expect(screen.getByLabelText("Backup time")).toHaveValue("02:00")
    expect(screen.getByLabelText("Backup retention (days)")).toHaveValue(30)
    expect(screen.getByLabelText("Month close time")).toHaveValue("00:30")
    expect(screen.getByRole("button", { name: "Save" })).toHaveAttribute("aria-disabled", "true")

    await user.clear(cap)
    await user.type(cap, "600")
    await user.clear(screen.getByLabelText("Month close time"))
    await user.type(screen.getByLabelText("Month close time"), "01:00")
    await user.click(screen.getByRole("button", { name: "Save" }))

    expect(await screen.findByText("Saved.")).toHaveAttribute("role", "status")
    // The button turned unavailable under the pointer or keyboard without dropping focus.
    expect(screen.getByRole("button", { name: "Save" })).toHaveFocus()
    expect(calls.find((call) => call.method === "PUT")!.body).toEqual(saved)
    expect(screen.getByRole("button", { name: "Save" })).toHaveAttribute("aria-disabled", "true")
  })

  it.each([["0", "At least 1 second."], ["86401", "At most 86400 seconds."]])("refuses a cap of %s", async (value, says) => {
    const { user, calls } = start("/settings", admin())

    const cap = await screen.findByLabelText("Time limit cap (seconds)")
    await user.clear(cap)
    await user.type(cap, value)
    await user.click(screen.getByRole("button", { name: "Save" }))

    expect(await screen.findByText(says)).toBeInTheDocument()
    expect(calls.filter((call) => call.method === "PUT")).toEqual([])
  })

  it("an empty number is an error, not a NaN sent to the server", async () => {
    const { user, calls } = start("/settings", admin())

    const days = await screen.findByLabelText("Backup retention (days)")
    await user.clear(days)
    await user.click(screen.getByRole("button", { name: "Save" }))

    expect(await screen.findByText("Enter a whole number of days.")).toBeInTheDocument()
    expect(calls.filter((call) => call.method === "PUT")).toEqual([])
  })

  it("says so when the save fails", async () => {
    const { user } = start("/settings", admin({ "PUT /api/ops/technical-settings": { status: 500, body: {} } }))

    const cap = await screen.findByLabelText("Time limit cap (seconds)")
    await user.clear(cap)
    await user.type(cap, "600")
    await user.click(screen.getByRole("button", { name: "Save" }))

    expect(await screen.findByRole("alert")).toHaveTextContent("save again")
  })
})

const RULES = {
  hours_per_day: 8,
  ramadan_hours_per_day: 6,
  breastfeeding_reduction: 1,
  weekend_weekdays: [4],
  forbidden_successions: [["N", "D"], ["D", "C"]],
  forbidden_successions_enabled: true,
  hours_rule_enabled: true,
  overtime_caps_enabled: true,
  overtime_month_cap: 40,
  overtime_year_cap: 720,
  dept_overtime_cap: 400,
  weights: {
    night_rest: 5, dept_overtime: 1, nurse_overtime: 1, nurse_shortfall: 1, avoidable_shortfall: 1000, fair_day: 1,
    fair_night: 1, fair_weekend: 1, score_deficit: 2, score_spread: 1, excess_weekend: 6, shift_switch: 8,
    undesired_day: 2, desired_day: 1, change: 3,
  },
}
const WEIGHT_COUNT = Object.keys(RULES.weights).length
const RULES_STATE = { rules: RULES, needs_review: true, shift_codes: ["D", "N", "A", "B", "C"] }
const CNO_ME = { ...ME, username: "cno", role: "cno" }
const DEPUTY = { ...ME, username: "deputy", role: "deputy_cno" }
const FLAG = "Defaults, review before the first solve"

describe("the hospital rules page", () => {
  /** Answers a save with what was sent, as the API does. */
  const saves = { "PUT /api/hospital/rules": ({ body }: { body: unknown }) => ({ body: { ...RULES_STATE, rules: body, needs_review: false } }) }
  const asCno = (state: unknown = RULES_STATE, extra = {}) => ({
    ...session(CNO_ME),
    "GET /api/hospital/rules": { body: state },
    ...extra,
  })
  const put = (calls: { method: string; body: unknown }[]) => calls.find((call) => call.method === "PUT")?.body as typeof RULES

  it("shows every rule and every weight with its explanation, and flags the defaults", async () => {
    start("/hospital-rules", asCno())

    expect(await screen.findByText(FLAG)).toBeInTheDocument()
    expect(document.title).toBe("Hospital rules · Nurse roster")
    expect(screen.getByLabelText("Hours per day")).toHaveValue(8)
    expect(screen.getByLabelText("Hours per day")).toHaveAccessibleDescription(/owes for each working day/)
    expect(screen.getByLabelText("Ramadan hours per day")).toHaveValue(6)
    expect(screen.getByLabelText("Breastfeeding reduction (hours)")).toHaveValue(1)
    expect(screen.getByRole("checkbox", { name: "Friday" })).toBeChecked()
    expect(screen.getByRole("checkbox", { name: "Saturday" })).not.toBeChecked()
    expect(screen.getByRole("checkbox", { name: "Forbid these successions" })).toBeChecked()
    expect(screen.getByRole("checkbox", { name: "Count hours" })).toHaveAccessibleDescription(/any number of shifts/)
    expect(screen.getByRole("checkbox", { name: "Cap each nurse's overtime" })).toBeChecked()
    expect(screen.getByLabelText("Monthly overtime cap (hours)")).toHaveValue(40)
    expect(screen.getByLabelText("Yearly overtime cap (hours)")).toHaveValue(720)
    expect(screen.getByLabelText("Unit overtime cap (hours)")).toHaveValue(400)
    expect(within(screen.getByRole("group", { name: "Pair 1" })).getByLabelText("After")).toHaveValue("N")
    expect(within(screen.getByRole("group", { name: "Pair 1" })).getByLabelText("the next day cannot be")).toHaveValue("D")

    const weights = within(screen.getByRole("region", { name: "Weights" }))
    expect(weights.getByText(/0 switches the rule off/)).toBeInTheDocument()
    const inputs = weights.getAllByRole("spinbutton")
    expect(inputs).toHaveLength(WEIGHT_COUNT)
    for (const input of inputs) expect(input).toHaveAccessibleDescription(/\S/)
    expect(weights.getByLabelText("Night rest")).toHaveValue(5)
    expect(weights.getByLabelText("Changes in a re-plan")).toHaveAccessibleDescription(/Each cell that differs/)
  })

  it("saving the defaults untouched is the review: the button is open and the flag goes", async () => {
    const { user, calls } = start("/hospital-rules", asCno(RULES_STATE, saves))

    await screen.findByText(FLAG)
    await user.click(screen.getByRole("button", { name: "Save" }))

    expect(await screen.findByText("Saved.")).toHaveAttribute("role", "status")
    expect(put(calls)).toEqual(RULES)
    expect(screen.queryByText(FLAG)).not.toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Save" })).toHaveAttribute("aria-disabled", "true")
  })

  it("reviewed rules show no flag and need a change to save", async () => {
    start("/hospital-rules", asCno({ ...RULES_STATE, needs_review: false }))

    await screen.findByLabelText("Hours per day")
    expect(screen.queryByText(FLAG)).not.toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Save" })).toHaveAttribute("aria-disabled", "true")
  })

  it("saves every kind of change", async () => {
    const { user, calls } = start("/hospital-rules", asCno(RULES_STATE, saves))

    const hours = await screen.findByLabelText("Hours per day")
    await user.clear(hours)
    await user.type(hours, "7")
    await user.click(screen.getByRole("checkbox", { name: "Saturday" }))
    await user.click(screen.getByRole("checkbox", { name: "Count hours" }))
    const nightRest = screen.getByLabelText("Night rest")
    await user.clear(nightRest)
    await user.type(nightRest, "0")
    await user.selectOptions(within(screen.getByRole("group", { name: "Pair 1" })).getByLabelText("the next day cannot be"), "A")
    await user.click(within(screen.getByRole("group", { name: "Pair 2" })).getByRole("button", { name: "Remove pair 2" }))
    await user.click(screen.getByRole("button", { name: "Save" }))

    await screen.findByText("Saved.")
    expect(put(calls)).toEqual({
      ...RULES,
      hours_per_day: 7,
      weekend_weekdays: [4, 5],
      hours_rule_enabled: false,
      forbidden_successions: [["N", "A"]],
      weights: { ...RULES.weights, night_rest: 0 },
    })
  })

  it("adds a pair not yet listed, and moves focus to it", async () => {
    const { user, calls } = start("/hospital-rules", asCno(RULES_STATE, saves))

    await user.click(await screen.findByRole("button", { name: "Add a pair" }))

    const added = within(screen.getByRole("group", { name: "Pair 3" }))
    expect(added.getByLabelText("After")).toHaveFocus()
    await user.click(screen.getByRole("button", { name: "Save" }))
    await screen.findByText("Saved.")
    expect(put(calls).forbidden_successions).toEqual([["N", "D"], ["D", "C"], ["D", "N"]])
  })

  it("removing the last pair leaves focus on the way to add one", async () => {
    const one = { ...RULES_STATE, rules: { ...RULES, forbidden_successions: [["N", "D"]] } }
    const { user } = start("/hospital-rules", asCno(one))

    await user.click(await screen.findByRole("button", { name: "Remove pair 1" }))

    expect(screen.getByRole("button", { name: "Add a pair" })).toHaveFocus()
    expect(screen.getByText("No successions are forbidden.")).toBeInTheDocument()
  })

  it.each([
    ["Hours per day", "25", "Between 0 and 24."],
    ["Hours per day", "", "Enter a whole number."],
    ["Monthly overtime cap (hours)", "-1", "Between 0 and 1000000."],
    ["Night rest", "1000001", "Between 0 and 1000000."],
    ["Night rest", "1.5", "Enter a whole number."],
  ])("refuses %s of '%s' beside the field, unsent", async (label, value, says) => {
    const { user, calls } = start("/hospital-rules", asCno())

    const input = await screen.findByLabelText(label)
    await user.clear(input)
    if (value) await user.type(input, value)
    await user.click(screen.getByRole("button", { name: "Save" }))

    expect(await screen.findByText(says)).toBeInTheDocument()
    expect(input).toHaveAttribute("aria-invalid", "true")
    expect(input).toHaveFocus()
    expect(calls.some((call) => call.method === "PUT")).toBe(false)
  })

  it("refuses Ramadan hours above a normal day, and a reduction above Ramadan hours", async () => {
    const { user, calls } = start("/hospital-rules", asCno())

    const ramadan = await screen.findByLabelText("Ramadan hours per day")
    await user.clear(ramadan)
    await user.type(ramadan, "9")
    await user.click(screen.getByRole("button", { name: "Save" }))
    expect(await screen.findByText("Cannot be more than the hours per day.")).toBeInTheDocument()
    expect(ramadan).toHaveAttribute("aria-invalid", "true")

    await user.clear(ramadan)
    await user.type(ramadan, "1")
    const reduction = screen.getByLabelText("Breastfeeding reduction (hours)")
    await user.clear(reduction)
    await user.type(reduction, "2")
    await user.click(screen.getByRole("button", { name: "Save" }))
    expect(await screen.findByText("Cannot be more than the Ramadan hours per day.")).toBeInTheDocument()
    expect(calls.some((call) => call.method === "PUT")).toBe(false)
  })

  it("refuses the same pair twice and names it", async () => {
    const { user, calls } = start("/hospital-rules", asCno())

    const second = within(await screen.findByRole("group", { name: "Pair 2" }))
    await user.selectOptions(second.getByLabelText("After"), "N")
    await user.selectOptions(second.getByLabelText("the next day cannot be"), "D")
    await user.click(screen.getByRole("button", { name: "Save" }))

    expect(await screen.findByText("N then D is listed twice. Remove one.")).toBeInTheDocument()
    expect(calls.some((call) => call.method === "PUT")).toBe(false)
  })

  it("puts a refusal from the API beside the field it names", async () => {
    const { user } = start("/hospital-rules", asCno(RULES_STATE, {
      "PUT /api/hospital/rules": {
        status: 422,
        body: { detail: [{ loc: ["body", "body", "weights", "change"], msg: "Input should be less than 5", type: "x" }] },
      },
    }))

    await screen.findByText(FLAG)
    await user.click(screen.getByRole("button", { name: "Save" }))

    expect(await screen.findByText("Input should be less than 5")).toBeInTheDocument()
    expect(screen.getByLabelText("Changes in a re-plan")).toHaveAttribute("aria-invalid", "true")
    expect(screen.getByText(FLAG)).toBeInTheDocument()
  })

  it("shows a validator's refusal on a field the form cannot get wrong, in its own words", async () => {
    const { user } = start("/hospital-rules", asCno(RULES_STATE, {
      "PUT /api/hospital/rules": {
        status: 422,
        body: { detail: [{ loc: ["body", "body", "weekend_weekdays"], msg: "Value error, lists a day twice", type: "x" }] },
      },
    }))

    await screen.findByText(FLAG)
    await user.click(screen.getByRole("button", { name: "Save" }))

    expect(await screen.findByText("lists a day twice")).toBeInTheDocument()
    expect(screen.getByRole("group", { name: "Weekend days" })).toHaveFocus()
  })

  it("says so when a save fails", async () => {
    const { user } = start("/hospital-rules", asCno(RULES_STATE, { "PUT /api/hospital/rules": { status: 500 } }))

    await screen.findByText(FLAG)
    await user.click(screen.getByRole("button", { name: "Save" }))

    expect(await screen.findByRole("alert")).toHaveTextContent("save again")
    expect(screen.getByText(FLAG)).toBeInTheDocument()
  })

  it("says so when the rules cannot be read", async () => {
    start("/hospital-rules", asCno(RULES_STATE, { "GET /api/hospital/rules": { status: 500 } }))

    expect(await screen.findByRole("alert")).toHaveTextContent("could not be read")
  })

  it("the Deputy CNO reads every value and explanation, and can change nothing", async () => {
    start("/hospital-rules", { ...session(DEPUTY), "GET /api/hospital/rules": { body: RULES_STATE } })

    expect(await screen.findByText(FLAG)).toBeInTheDocument()
    expect(screen.getByText(/Only the CNO can change these/)).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Save" })).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Add a pair" })).not.toBeInTheDocument()
    expect(screen.queryAllByRole("spinbutton")).toEqual([])
    expect(screen.queryAllByRole("checkbox")).toEqual([])
    expect(screen.queryAllByRole("combobox")).toEqual([])

    const hours = screen.getByText("Hours per day").closest("div")!
    expect(hours).toHaveTextContent("8")
    expect(hours).toHaveTextContent(/owes for each working day/)
    expect(screen.getByText("Friday")).toBeInTheDocument()
    expect(screen.getByText("After N, not D")).toBeInTheDocument()
    expect(screen.getByText("Avoidable hours short").closest("div")).toHaveTextContent("1000")
    const weights = within(screen.getByRole("region", { name: "Weights" }))
    expect(weights.getAllByRole("definition").length).toBeGreaterThanOrEqual(WEIGHT_COUNT)
  })

  it.each(["system_admin", "unit_manager", "staff_nurse"])("is not for the %s", async (role) => {
    const { router } = start("/hospital-rules", {
      ...session({ ...ME, role }),
      "GET /api/ops/health": { body: HEALTH },
    })

    await waitFor(() => expect(router.state.location.pathname).not.toBe("/hospital-rules"))
  })

})

const CATALOGUE_LINKS = ["Shifts", "Leave types", "Holidays and Ramadan"]

describe("each role's navigation and home", () => {
  const navLinks = () => within(screen.getByRole("navigation", { name: "Main" })).getAllByRole("link").map((link) => link.textContent)

  it("the System Admin reaches their pages and nothing of the roster", async () => {
    start("/", admin())

    await screen.findByRole("heading", { name: "Health" })
    expect(navLinks()).toEqual(["Health", "Technical settings", "Users", "Audit log", "Change password"])
    expect(screen.getByText("admin · System Admin")).toBeInTheDocument()
  })

  it.each([
    ["cno", "CNO", /under Hospital rules/, ["Home", "Units", "Hospital rules", ...CATALOGUE_LINKS, "Change password"], ["/api/units"]],
    ["deputy_cno", "Deputy CNO", /Submitted rosters waiting for your decision/, ["Home", "Hospital rules", ...CATALOGUE_LINKS, "Change password"], []],
    ["unit_manager", "Unit Manager", /No unit is assigned to you yet/, ["Home", ...CATALOGUE_LINKS, "Change password"], ["/api/units"]],
    ["staff_nurse", "Staff Nurse", /approved roster will be shown here/, ["Home", ...CATALOGUE_LINKS, "Change password"], []],
  ])("%s has a home of its own and none of the System Admin's pages", async (role, name, says, links, reads) => {
    const { router, calls } = start("/", {
      ...session({ ...ME, username: "someone", full_name: "Some One", role }),
      "GET /api/units": { body: [] },
    })

    expect(await screen.findByText(says)).toBeInTheDocument()
    expect(router.state.location.pathname).toBe("/")
    expect(screen.getByRole("heading", { level: 1, name: "Some One" })).toBeInTheDocument()
    expect(screen.getByText(`someone · ${name}`)).toBeInTheDocument()
    expect(navLinks()).toEqual(links)
    await waitFor(() => expect(calls.map((call) => call.url)).toEqual(["/api/auth/session", ...reads]))
  })
})

const CNO = {
  id: "019a0000-0000-7000-8000-000000000001", username: "fatimah", full_name: "Fatimah Al-Otaibi", role: "cno",
  is_active: true, must_change_password: false, last_login: null,
}
const MANAGER = { ...CNO, id: "019a0000-0000-7000-8000-000000000002", username: "khalid", full_name: "Khalid Omar", role: "unit_manager" }

describe("the users page", () => {
  const page = (users: unknown[], extra = {}) => admin({ "GET /api/users": { body: users }, ...extra })

  it("lists the users with their state", async () => {
    start("/users", page([CNO, { ...MANAGER, is_active: false, must_change_password: true }]))

    const row = (await screen.findByRole("cell", { name: "khalid" })).closest("tr")!
    expect(within(row).getByText("Deactivated")).toBeInTheDocument()
    expect(within(row).getByText("Password change due")).toBeInTheDocument()
    expect(within(row).getByText("Never")).toBeInTheDocument()
    expect(document.title).toBe("Users · Nurse roster")
  })

  it("offers no nurse and no second System Admin to create", async () => {
    start("/users", page([]))

    const options = within(await screen.findByLabelText("Role")).getAllByRole("option").map((option) => option.textContent)
    expect(options).toEqual(["Choose a role", "CNO", "Deputy CNO", "Unit Manager"])
    expect(screen.getByText(/There are no users yet/)).toBeInTheDocument()
  })

  it("a role already held cannot be chosen, and says who holds it", async () => {
    start("/users", page([CNO, MANAGER]))

    const select = await screen.findByLabelText("Role")
    expect(within(select).getByRole("option", { name: "CNO (fatimah holds this role)" })).toBeDisabled()
    expect(within(select).getByRole("option", { name: "Unit Manager" })).toBeEnabled()
  })

  async function fillNewUser(user: ReturnType<typeof userEvent.setup>, role = "cno") {
    await user.selectOptions(await screen.findByLabelText("Role"), role)
    await user.type(screen.getByLabelText("Full name"), "Fatimah Al-Otaibi")
    await user.type(screen.getByLabelText("Username"), "fatimah")
    await user.click(screen.getByRole("button", { name: "Create user" }))
  }

  it("creates a user and shows the password until Done, and then never again", async () => {
    let users: unknown[] = []
    const { user, calls, router } = start("/users", admin({
      "GET /api/users": () => ({ body: users }),
      "POST /api/users": () => {
        users = [CNO]
        return { status: 201, body: { user: { ...CNO, must_change_password: true }, generated_password: "abcd-efgh-jkmn-pqrs" } }
      },
    }))

    await fillNewUser(user)

    const dialog = await screen.findByRole("alertdialog", { name: "Password for fatimah" })
    expect(within(dialog).getByLabelText("Generated password")).toHaveValue("abcd-efgh-jkmn-pqrs")
    expect(within(dialog).getByText(/only time it is shown/)).toBeInTheDocument()
    expect(calls.find((call) => call.method === "POST")!.body).toEqual({ role: "cno", full_name: "Fatimah Al-Otaibi", username: "fatimah" })

    await user.keyboard("{Escape}")
    expect(screen.getByRole("alertdialog", { name: "Password for fatimah" })).toBeInTheDocument()
    // A blocked navigation never settles, so this one cannot be awaited.
    act(() => void router.navigate({ to: "/health" }))
    await new Promise((resolve) => setTimeout(resolve, 50))
    expect(router.state.location.pathname).toBe("/users")

    await user.click(within(dialog).getByRole("button", { name: "Done" }))

    await waitFor(() => expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument())
    expect(screen.queryByDisplayValue("abcd-efgh-jkmn-pqrs")).not.toBeInTheDocument()
    expect(await screen.findByRole("cell", { name: "fatimah" })).toBeInTheDocument()
    expect(screen.getByLabelText("Username")).toHaveValue("")
  })

  it("says the password was copied", async () => {
    const writeText = vi.fn(async () => {})
    const { user } = start("/users", page([], {
      "POST /api/users": { status: 201, body: { user: CNO, generated_password: "abcd-efgh-jkmn-pqrs" } },
    }))
    await fillNewUser(user)
    Object.defineProperty(navigator, "clipboard", { value: { writeText }, configurable: true })

    await user.click(await screen.findByRole("button", { name: "Copy password" }))

    expect(await screen.findByText("Copied.")).toBeInTheDocument()
    expect(writeText).toHaveBeenCalledWith("abcd-efgh-jkmn-pqrs")
  })

  it("checks the form before asking the server", async () => {
    const { user, calls } = start("/users", page([]))

    await user.click(await screen.findByRole("button", { name: "Create user" }))

    expect(await screen.findByText("Choose a role.")).toBeInTheDocument()
    expect(screen.getByText("Enter their full name.")).toBeInTheDocument()
    expect(screen.getByText("Enter a username.")).toBeInTheDocument()
    await user.type(screen.getByLabelText("Username"), "has space")
    expect(await screen.findByText(/only letters, digits/)).toBeInTheDocument()
    expect(calls.some((call) => call.method === "POST")).toBe(false)
  })

  it("shows a second CNO's refusal on the role, focused", async () => {
    const { user } = start("/users", page([], {
      "POST /api/users": { status: 409, body: { role: ["fatimah is already the CNO. Deactivate that user first."], username: [] } },
    }))

    await fillNewUser(user)

    expect(await screen.findByText(/fatimah is already the CNO/)).toBeInTheDocument()
    expect(screen.getByLabelText("Role")).toHaveFocus()
    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument()
  })

  it("shows a taken username on the username, focused", async () => {
    const { user } = start("/users", page([], {
      "POST /api/users": { status: 409, body: { role: [], username: ["This username is taken."] } },
    }))

    await fillNewUser(user)

    expect(await screen.findByText("This username is taken.")).toBeInTheDocument()
    expect(screen.getByLabelText("Username")).toHaveFocus()
  })

  it("deactivates after asking, and Cancel does nothing", async () => {
    let users = [CNO]
    const url = `/api/users/${CNO.id}/deactivate`
    const { user, calls } = start("/users", admin({
      "GET /api/users": () => ({ body: users }),
      [`POST ${url}`]: () => {
        users = [{ ...CNO, is_active: false }]
        return { body: users[0] }
      },
    }))

    await user.click(await screen.findByRole("button", { name: "Deactivate fatimah" }))
    expect(screen.getByRole("alertdialog", { name: "Deactivate fatimah?" })).toBeInTheDocument()
    await user.click(screen.getByRole("button", { name: "Cancel" }))
    await waitFor(() => expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument())
    expect(calls.some((call) => call.method === "POST")).toBe(false)

    await user.click(screen.getByRole("button", { name: "Deactivate fatimah" }))
    await user.click(within(await screen.findByRole("alertdialog")).getByRole("button", { name: "Deactivate" }))

    expect(await screen.findByRole("button", { name: "Reactivate fatimah" })).toBeInTheDocument()
    expect(screen.getByRole("status")).toHaveTextContent("fatimah is deactivated.")
  })

  it("a refused reactivation says why and stays open", async () => {
    const { user } = start("/users", page([{ ...CNO, is_active: false }], {
      [`POST /api/users/${CNO.id}/reactivate`]: { status: 409, body: { detail: "successor is already the CNO. Deactivate that user first." } },
    }))

    await user.click(await screen.findByRole("button", { name: "Reactivate fatimah" }))
    await user.click(within(await screen.findByRole("alertdialog")).getByRole("button", { name: "Reactivate" }))

    expect(await screen.findByRole("alert")).toHaveTextContent("successor is already the CNO")
    expect(screen.getByRole("alertdialog", { name: "Reactivate fatimah?" })).toBeInTheDocument()
  })

  it("a reset shows the new password once", async () => {
    const { user } = start("/users", page([CNO], {
      [`POST /api/users/${CNO.id}/reset-password`]: { body: { user: CNO, generated_password: "wxyz-wxyz-wxyz-wxyz" } },
    }))

    await user.click(await screen.findByRole("button", { name: "Reset password of fatimah" }))
    await user.click(within(await screen.findByRole("alertdialog")).getByRole("button", { name: "Reset password" }))

    const dialog = await screen.findByRole("alertdialog", { name: "Password for fatimah" })
    expect(within(dialog).getByLabelText("Generated password")).toHaveValue("wxyz-wxyz-wxyz-wxyz")
    await user.click(within(dialog).getByRole("button", { name: "Done" }))
    await waitFor(() => expect(screen.queryByDisplayValue("wxyz-wxyz-wxyz-wxyz")).not.toBeInTheDocument())
  })
})

describe("the audit log page", () => {
  const ENTRY = {
    id: 7, at: "2026-11-06T00:30:15+03:00", actor: "admin", action: "user.deactivated", target: "fatimah",
    before: { is_active: true }, after: { is_active: false }, ip: "10.1.2.3",
  }
  const OPTIONS = { "GET /api/audit/filter-options": { body: { actions: ["auth.login", "user.deactivated", "later.action"], users: ["admin", "fatimah"] } } }
  function auditStart(path: string, answer: (params: URLSearchParams) => Answer) {
    return start(path, admin({
      ...OPTIONS,
      "GET /api/audit/entries": ({ url }: { url: string }) => answer(new URL(url, "http://x").searchParams),
    }))
  }

  it("shows each entry in hospital time, with what changed", async () => {
    auditStart("/audit-log", () => ({ body: { entries: [ENTRY, { ...ENTRY, id: 6, actor: null, action: "auth.login_failed", target: "nobody", before: null, after: null, ip: null }, { ...ENTRY, id: 5, actor: null, action: "later.action" }], older_than: null } }))

    const row = (await screen.findAllByText("2026-11-06 00:30:15"))[0].closest("tr")!
    expect(within(row).getByText("admin")).toBeInTheDocument()
    expect(within(row).getByText("Deactivated user")).toBeInTheDocument()
    expect(within(row).getByText("fatimah")).toBeInTheDocument()
    expect(within(row).getByText("is_active: true → false")).toBeInTheDocument()
    expect(within(row).getByText("10.1.2.3")).toBeInTheDocument()
    expect(screen.getByText("Unknown")).toBeInTheDocument()
    expect(screen.getByText("System")).toBeInTheDocument()
    expect(document.title).toBe("Audit log · Nurse roster")
  })

  it("applies the filters to the address and the request, and clears them", async () => {
    const seen: string[] = []
    const { user, router } = auditStart("/audit-log", (params) => {
      seen.push(params.toString())
      return { body: { entries: [ENTRY], older_than: null } }
    })

    await user.type(await screen.findByLabelText("User"), "fatimah")
    await waitFor(() => expect(within(screen.getByLabelText("Action")).getByRole("option", { name: "Logged in" })).toBeInTheDocument())
    await user.selectOptions(screen.getByLabelText("Action"), "auth.login")
    await user.type(screen.getByLabelText("From"), "2026-11-01")
    await user.type(screen.getByLabelText("To"), "2026-11-05")
    await user.click(screen.getByRole("button", { name: "Apply filters" }))

    await waitFor(() => expect(seen.at(-1)).toBe("user=fatimah&action=auth.login&date_from=2026-11-01&date_to=2026-11-05"))
    expect(router.state.location.search).toEqual({ user: "fatimah", action: "auth.login", date_from: "2026-11-01", date_to: "2026-11-05" })

    await user.click(screen.getByRole("link", { name: "Clear filters" }))

    await waitFor(() => expect(seen.at(-1)).toBe(""))
    expect(screen.getByLabelText("User")).toHaveValue("")
  })

  it("the form follows the address, including a username of digits", async () => {
    const seen: string[] = []
    auditStart("/audit-log?user=12345&action=auth.login", (params) => {
      seen.push(params.toString())
      return { body: { entries: [], older_than: null } }
    })

    expect(await screen.findByText(/No entries match/)).toBeInTheDocument()
    expect(screen.getByLabelText("User")).toHaveValue("12345")
    expect(screen.getByLabelText("Action")).toHaveValue("auth.login")
    expect(seen.at(-1)).toBe("user=12345&action=auth.login")
  })

  it("drops a date that is not one from the address", async () => {
    const seen: string[] = []
    auditStart("/audit-log?date_from=nonsense&date_to=2026-11-05", (params) => {
      seen.push(params.toString())
      return { body: { entries: [], older_than: null } }
    })

    await screen.findByText(/No entries match/)
    expect(seen.at(-1)).toBe("date_to=2026-11-05")
  })

  it("the table can be scrolled from the keyboard", async () => {
    auditStart("/audit-log", () => ({ body: { entries: [ENTRY], older_than: null } }))

    expect(await screen.findByRole("region", { name: "Audit entries" })).toHaveAttribute("tabindex", "0")
  })

  it("refuses an end date before the start date", async () => {
    const seen: string[] = []
    const { user } = auditStart("/audit-log", (params) => {
      seen.push(params.toString())
      return { body: { entries: [], older_than: null } }
    })

    await user.type(await screen.findByLabelText("From"), "2026-11-05")
    await user.type(screen.getByLabelText("To"), "2026-11-01")
    await user.click(screen.getByRole("button", { name: "Apply filters" }))

    expect(await screen.findByText("This is before the start date.")).toBeInTheDocument()
    expect(seen.every((params) => params === "")).toBe(true)
  })

  it("walks to older entries keeping the filters, and back to the newest", async () => {
    const seen: string[] = []
    const { user } = auditStart("/audit-log?action=auth.login", (params) => {
      seen.push(params.toString())
      return params.get("older_than")
        ? { body: { entries: [{ ...ENTRY, id: 3, target: "older-one" }], older_than: null } }
        : { body: { entries: [ENTRY], older_than: 7 } }
    })

    await user.click(await screen.findByRole("link", { name: "Older entries" }))

    expect(await screen.findByText("older-one")).toBeInTheDocument()
    expect(seen.at(-1)).toBe("action=auth.login&older_than=7")
    expect(screen.queryByRole("link", { name: "Older entries" })).not.toBeInTheDocument()
    await waitFor(() => expect(screen.getByRole("heading", { name: "Entries" })).toHaveFocus())

    await user.click(screen.getByRole("link", { name: "Newest entries" }))

    await waitFor(() => expect(seen.at(-1)).toBe("action=auth.login"))
  })
})

const SHIFT_D = { id: "s1", code: "D", display_name: "Day", hours: 12, start_time: "07:00", end_time: "19:00", colour: "#0284c7", active: true, renames: [] }
const SHIFT_N = { id: "s2", code: "N", display_name: "Night", hours: 12, start_time: "19:00", end_time: "07:00", colour: "#4338ca", active: true, renames: [] }
const refusal = (field: (string | number)[], msg: string) => ({ status: 422, body: { detail: [{ loc: ["body", "body", ...field], msg: `Value error, ${msg}`, type: "value_error" }] } })
const asCno = (extra = {}) => ({ ...session(CNO_ME), ...extra })

describe("the shifts page", () => {
  const listed = { "GET /api/hospital/shifts": { body: [SHIFT_D, SHIFT_N] } }

  it("lists the catalogue for the CNO, with a shift's former codes", async () => {
    const renamed = { ...SHIFT_D, code: "DAY", renames: [{ old_code: "D", new_code: "DAY", at: "2026-11-05T10:00:00+03:00" }] }
    start("/shifts", asCno({ "GET /api/hospital/shifts": { body: [renamed, { ...SHIFT_N, active: false }] } }))

    const row = (await screen.findByText("DAY")).closest("tr") as HTMLElement
    expect(within(row).getByText("Day")).toBeInTheDocument()
    expect(within(row).getByText("07:00 to 19:00")).toBeInTheDocument()
    expect(within(row).getByText(/until 2026-11-05/)).toHaveTextContent("Was D until 2026-11-05")
    expect(within(row).getByText("Active")).toBeInTheDocument()
    expect(screen.getByText("Retired")).toBeInTheDocument()
  })

  it("adds a shift", async () => {
    const { user, calls } = start("/shifts", asCno({
      ...listed,
      "POST /api/hospital/shifts": ({ body }: { body: unknown }) => ({ status: 201, body: { ...(body as object), id: "s3", renames: [] } }),
    }))

    await user.type(await screen.findByLabelText("Code"), "T")
    await user.type(screen.getByLabelText("Display name"), "Twilight")
    await user.type(screen.getByLabelText("Hours"), "6")
    await user.type(screen.getByLabelText("Start time"), "16:00")
    await user.type(screen.getByLabelText("End time"), "22:00")
    await user.click(screen.getByRole("button", { name: "Add shift" }))

    expect(await screen.findByText("T is added.")).toBeInTheDocument()
    expect(calls.find((call) => call.method === "POST")?.body).toEqual({
      code: "T", display_name: "Twilight", hours: 6, start_time: "16:00", end_time: "22:00", colour: "#64748b", active: true,
    })
    expect(screen.getByLabelText("Code")).toHaveValue("")
  })

  it("says what is wrong before asking the API", async () => {
    const { user, calls } = start("/shifts", asCno(listed))

    await user.type(await screen.findByLabelText("Code"), "=X")
    await user.click(screen.getByRole("button", { name: "Add shift" }))

    expect(await screen.findByText(/starting with a letter or digit/)).toBeInTheDocument()
    expect(screen.getByText("Enter a name.")).toBeInTheDocument()
    expect(screen.getByText(/whole hours from 1 to 24/)).toBeInTheDocument()
    expect(calls.some((call) => call.method === "POST")).toBe(false)
  })

  it("edits a shift in the form and gives focus back to its button", async () => {
    const { user, calls } = start("/shifts", asCno({
      ...listed,
      "PUT /api/hospital/shifts/s1": ({ body }: { body: unknown }) => ({ body: { ...SHIFT_D, ...(body as object) } }),
    }))

    const edit = await screen.findByRole("button", { name: "Edit D" })
    await user.click(edit)
    expect(screen.getByRole("heading", { name: "Edit D" })).toBeInTheDocument()
    expect(screen.getByLabelText("Code")).toHaveFocus()
    expect(screen.getByLabelText("Code")).toHaveAccessibleDescription(/forbidden successions change with it/)

    await user.clear(screen.getByLabelText("Code"))
    await user.type(screen.getByLabelText("Code"), "DAY")
    await user.click(screen.getByRole("button", { name: "Save shift" }))

    expect(await screen.findByText("DAY is saved.")).toBeInTheDocument()
    expect(calls.find((call) => call.method === "PUT")?.body).toEqual({
      code: "DAY", display_name: "Day", hours: 12, start_time: "07:00", end_time: "19:00", colour: "#0284c7", active: true,
    })
    expect(screen.getByRole("heading", { name: "Add a shift" })).toBeInTheDocument()
    await waitFor(() => expect(edit).toHaveFocus())
  })

  it("cancelling leaves the form empty and changes nothing", async () => {
    const { user, calls } = start("/shifts", asCno(listed))

    const edit = await screen.findByRole("button", { name: "Edit N" })
    await user.click(edit)
    await user.click(screen.getByRole("button", { name: "Cancel" }))

    expect(screen.getByLabelText("Code")).toHaveValue("")
    await waitFor(() => expect(edit).toHaveFocus())
    expect(calls.some((call) => call.method === "PUT")).toBe(false)
  })

  it("shows why a shift cannot be retired beside the switch", async () => {
    const { user } = start("/shifts", asCno({
      ...listed,
      "PUT /api/hospital/shifts/s2": refusal(["active"], "N is named in the forbidden successions of the hospital rules. Remove those pairs first."),
    }))

    await user.click(await screen.findByRole("button", { name: "Edit N" }))
    await user.click(screen.getByLabelText("Active"))
    await user.click(screen.getByRole("button", { name: "Save shift" }))

    await waitFor(() => expect(screen.getByLabelText("Active")).toHaveFocus())
    expect(screen.getByLabelText("Active")).toHaveAccessibleDescription(/Remove those pairs first/)
    expect(screen.getByLabelText("Active")).toBeInvalid()
  })

  it("shows a taken code beside its field", async () => {
    const { user } = start("/shifts", asCno({ ...listed, "POST /api/hospital/shifts": refusal(["code"], "D is already in use") }))

    await user.type(await screen.findByLabelText("Code"), "D")
    await user.type(screen.getByLabelText("Display name"), "Other")
    await user.type(screen.getByLabelText("Hours"), "6")
    await user.type(screen.getByLabelText("Start time"), "16:00")
    await user.type(screen.getByLabelText("End time"), "22:00")
    await user.click(screen.getByRole("button", { name: "Add shift" }))

    await waitFor(() => expect(screen.getByLabelText("Code")).toHaveFocus())
    expect(screen.getByLabelText("Code")).toHaveAccessibleDescription(/D is already in use/)
  })

  it.each(["deputy_cno", "unit_manager", "staff_nurse", "system_admin"])("%s reads the catalogue and can change nothing", async (role) => {
    start("/shifts", { ...session({ ...ME, role }), ...listed })

    expect(await screen.findByText("Night")).toBeInTheDocument()
    expect(screen.getByText(/Only the CNO can change these/)).toBeInTheDocument()
    expect(screen.getByRole("region", { name: "Shifts" })).toHaveAttribute("tabindex", "0")
    expect(screen.queryByRole("button", { name: /Edit/ })).not.toBeInTheDocument()
    expect(screen.queryByLabelText("Code")).not.toBeInTheDocument()
  })
})

describe("the leave types page", () => {
  const SICK = { id: "l1", name: "Sick", active: true }
  const listed = { "GET /api/hospital/leave-types": { body: [SICK, { id: "l2", name: "Hajj", active: false }] } }

  it("adds a type and shows a taken name beside its field", async () => {
    const answers = [refusal(["name"], "Sick is already a leave type"), { status: 201, body: { id: "l3", name: "Study", active: true } }]
    const { user } = start("/leave-types", asCno({ ...listed, "POST /api/hospital/leave-types": () => answers.shift() as Answer }))

    await user.type(await screen.findByLabelText("Name"), "Sick")
    await user.click(screen.getByRole("button", { name: "Add leave type" }))
    await waitFor(() => expect(screen.getByLabelText("Name")).toHaveAccessibleDescription(/already a leave type/))

    await user.clear(screen.getByLabelText("Name"))
    await user.type(screen.getByLabelText("Name"), "Study")
    await user.click(screen.getByRole("button", { name: "Add leave type" }))

    expect(await screen.findByText("Study is added.")).toBeInTheDocument()
  })

  it("edits and retires a type", async () => {
    const { user, calls } = start("/leave-types", asCno({
      ...listed,
      "PUT /api/hospital/leave-types/l1": ({ body }: { body: unknown }) => ({ body: { id: "l1", ...(body as object) } }),
    }))

    const edit = await screen.findByRole("button", { name: "Edit Sick" })
    await user.click(edit)
    await user.click(screen.getByLabelText("Active"))
    await user.click(screen.getByRole("button", { name: "Save leave type" }))

    expect(await screen.findByText("Sick is saved.")).toBeInTheDocument()
    expect(calls.find((call) => call.method === "PUT")?.body).toEqual({ name: "Sick", active: false })
    await waitFor(() => expect(edit).toHaveFocus())
  })

  it("another role reads and can change nothing", async () => {
    start("/leave-types", { ...session(NURSE), ...listed })

    expect(await screen.findByText("Sick")).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /Edit/ })).not.toBeInTheDocument()
    expect(screen.queryByLabelText("Name")).not.toBeInTheDocument()
  })
})

describe("the holidays and Ramadan page", () => {
  const NATIONAL = { id: "h1", date: "2026-09-23", name: "National Day" }
  const days = (first: number, last: number) =>
    Array.from({ length: last - first + 1 }, (_, index) => `2026-03-${String(first + index).padStart(2, "0")}`)
  const MARCH = { month: "2026-03", source: "derived", dates: days(1, 19), derived_dates: days(1, 19) }
  const months = (march: unknown = MARCH) => Array.from({ length: 12 }, (_, index) => {
    const month = `2026-${String(index + 1).padStart(2, "0")}`
    return month === "2026-03" ? march : { month, source: "derived", dates: [], derived_dates: [] }
  })
  const year2026 = (march?: unknown, holidays: unknown[] = [NATIONAL]) => ({
    "GET /api/hospital/public-holidays": { body: holidays },
    "GET /api/hospital/ramadan": { body: months(march) },
  })
  const row = async (name: string) => (await screen.findByRole("cell", { name })).closest("tr") as HTMLElement

  it("shows the year's holidays and each month's Ramadan days", async () => {
    const { calls } = start("/holidays?year=2026", asCno(year2026()))

    expect(await screen.findByText(/23 September 2026/)).toBeInTheDocument()
    const march = await row("March 2026")
    expect(within(march).getByText("1 to 19")).toBeInTheDocument()
    expect(within(march).getByText("The calendar")).toBeInTheDocument()
    expect(within(await row("April 2026")).getByText("None")).toBeInTheDocument()
    expect(calls.map((call) => call.url)).toContain("/api/hospital/ramadan?year=2026")
    expect(calls.map((call) => call.url)).toContain("/api/hospital/public-holidays?year=2026")
  })

  it("moves between years", async () => {
    const { user, router, calls } = start("/holidays?year=2026", asCno(year2026()))

    await user.click(await screen.findByRole("link", { name: "2027" }))

    await waitFor(() => expect(router.state.location.search).toEqual({ year: 2027 }))
    await waitFor(() => expect(calls.map((call) => call.url)).toContain("/api/hospital/ramadan?year=2027"))
    expect(await screen.findByRole("heading", { name: "Public holidays in 2027" })).toBeInTheDocument()
  })

  it("drops a hand-edited year from the address", async () => {
    const { calls } = start("/holidays?year=1800", asCno(year2026()))

    await screen.findByRole("heading", { name: "Holidays and Ramadan" })
    await waitFor(() => expect(calls.some((call) => call.url.includes("year=1800"))).toBe(false))
  })

  it("adds a holiday, and a date entered twice is refused beside the date", async () => {
    const answers = [refusal(["date"], "2026-09-23 is already a public holiday"), { status: 201, body: { id: "h2", date: "2026-02-22", name: "Founding Day" } }]
    const { user, calls } = start("/holidays?year=2026", asCno({ ...year2026(), "POST /api/hospital/public-holidays": () => answers.shift() as Answer }))

    await user.type(await screen.findByLabelText("Date"), "2026-09-23")
    await user.type(screen.getByLabelText("Name"), "Again")
    await user.click(screen.getByRole("button", { name: "Add holiday" }))
    await waitFor(() => expect(screen.getByLabelText("Date")).toHaveAccessibleDescription(/already a public holiday/))

    await user.clear(screen.getByLabelText("Date"))
    await user.type(screen.getByLabelText("Date"), "2026-02-22")
    await user.click(screen.getByRole("button", { name: "Add holiday" }))

    expect(await screen.findByText("Again is added.".replace("Again", "Founding Day"))).toBeInTheDocument()
    expect(calls.filter((call) => call.method === "POST").at(-1)?.body).toEqual({ date: "2026-02-22", name: "Again" })
  })

  it("refuses a date outside the year on the page, before asking the API", async () => {
    const { user, calls } = start("/holidays?year=2026", asCno(year2026()))

    await user.type(await screen.findByLabelText("Date"), "2027-01-01")
    await user.type(screen.getByLabelText("Name"), "New Year")
    await user.click(screen.getByRole("button", { name: "Add holiday" }))

    expect(await screen.findByText(/not in 2026/)).toBeInTheDocument()
    expect(calls.some((call) => call.method === "POST")).toBe(false)
  })

  it("edits a holiday and removes one, with focus staying on the form", async () => {
    const { user, calls } = start("/holidays?year=2026", asCno({
      ...year2026(),
      "PUT /api/hospital/public-holidays/h1": ({ body }: { body: unknown }) => ({ body: { id: "h1", ...(body as object) } }),
      "DELETE /api/hospital/public-holidays/h1": { status: 204 },
    }))

    await user.click(await screen.findByRole("button", { name: "Edit National Day" }))
    expect(screen.getByLabelText("Date")).toHaveFocus()
    await user.clear(screen.getByLabelText("Name"))
    await user.type(screen.getByLabelText("Name"), "Saudi National Day")
    await user.click(screen.getByRole("button", { name: "Save holiday" }))
    expect(await screen.findByText("Saudi National Day is saved.")).toBeInTheDocument()

    await user.click(screen.getByRole("button", { name: "Remove National Day" }))
    expect(calls.some((call) => call.method === "DELETE")).toBe(false)
    await user.click(within(await screen.findByRole("alertdialog")).getByRole("button", { name: "Remove holiday" }))

    expect(await screen.findByText("National Day is removed.")).toBeInTheDocument()
    await waitFor(() => expect(screen.getByLabelText("Date")).toHaveFocus())
    expect(calls.some((call) => call.method === "DELETE")).toBe(true)
  })

  it("fixes a month as a range, starting from what is in force", async () => {
    const fixed = { ...MARCH, source: "fixed", dates: days(2, 20) }
    const { user, calls } = start("/holidays?year=2026", asCno({ ...year2026(), "PUT /api/hospital/ramadan/2026-03": { body: fixed } }))

    const button = await screen.findByRole("button", { name: "Fix the dates of March 2026" })
    await user.click(button)
    expect(screen.getByRole("heading", { name: "Fix the Ramadan dates of March 2026" })).toHaveFocus()
    expect(screen.getByLabelText("First day")).toHaveValue("2026-03-01")
    expect(screen.getByLabelText("Last day")).toHaveValue("2026-03-19")

    await user.clear(screen.getByLabelText("First day"))
    await user.type(screen.getByLabelText("First day"), "2026-03-02")
    await user.clear(screen.getByLabelText("Last day"))
    await user.type(screen.getByLabelText("Last day"), "2026-03-20")
    await user.click(within(screen.getByRole("heading", { name: /Fix the Ramadan dates/ }).closest("[data-slot=card]") as HTMLElement).getByRole("button", { name: "Fix dates" }))

    expect(await screen.findByText("The Ramadan dates of March 2026 are fixed.")).toBeInTheDocument()
    expect(calls.find((call) => call.method === "PUT")?.body).toEqual({ first: "2026-03-02", last: "2026-03-20" })
    await waitFor(() => expect(button).toHaveFocus())
  })

  it("refuses a backwards range on the page", async () => {
    const { user, calls } = start("/holidays?year=2026", asCno(year2026()))

    await user.click(await screen.findByRole("button", { name: "Fix the dates of March 2026" }))
    await user.clear(screen.getByLabelText("Last day"))
    await user.type(screen.getByLabelText("Last day"), "2026-02-20")
    const card = screen.getByRole("heading", { name: /Fix the Ramadan dates/ }).closest("[data-slot=card]") as HTMLElement
    await user.click(within(card).getByRole("button", { name: "Fix dates" }))

    expect(await screen.findByText("Enter a day in March 2026.")).toBeInTheDocument()
    expect(calls.some((call) => call.method === "PUT")).toBe(false)
  })

  it("fixes a month as a list, and none ticked means no Ramadan days", async () => {
    const { user, calls } = start("/holidays?year=2026", asCno({ ...year2026(), "PUT /api/hospital/ramadan/2026-03": { body: { ...MARCH, source: "fixed", dates: [] } } }))

    await user.click(await screen.findByRole("button", { name: "Fix the dates of March 2026" }))
    await user.click(screen.getByLabelText("A list of days"))
    const days31 = within(screen.getByRole("group", { name: "Days of March 2026" })).getAllByRole("checkbox")
    expect(days31).toHaveLength(31)
    for (const box of days31.filter((box) => (box as HTMLInputElement).checked)) await user.click(box)
    await user.click(within(screen.getByRole("heading", { name: /Fix the Ramadan dates/ }).closest("[data-slot=card]") as HTMLElement).getByRole("button", { name: "Fix dates" }))

    await screen.findByText("The Ramadan dates of March 2026 are fixed.")
    expect(calls.find((call) => call.method === "PUT")?.body).toEqual({ dates: [] })
  })

  it("a fixed month shows the calendar's days too and can return to them", async () => {
    const fixed = { ...MARCH, source: "fixed", dates: days(2, 20) }
    const { user, calls } = start("/holidays?year=2026", asCno({ ...year2026(fixed), "DELETE /api/hospital/ramadan/2026-03": { body: MARCH } }))

    const march = await row("March 2026")
    expect(within(march).getByText("2 to 20")).toBeInTheDocument()
    expect(within(march).getByText("The calendar says: 1 to 19")).toBeInTheDocument()
    expect(within(march).getByText("The CNO")).toBeInTheDocument()

    await user.click(within(march).getByRole("button", { name: "Use the calendar for March 2026" }))
    const dialog = await screen.findByRole("alertdialog")
    expect(dialog).toHaveTextContent("The fixed dates (2 to 20) are dropped")
    expect(calls.some((call) => call.method === "DELETE")).toBe(false)
    await user.click(within(dialog).getByRole("button", { name: "Use the calendar" }))

    expect(await screen.findByText("March 2026 follows the calendar again.")).toBeInTheDocument()
    expect(calls.some((call) => call.method === "DELETE")).toBe(true)
    await waitFor(() => expect(screen.getByRole("button", { name: "Fix the dates of March 2026" })).toHaveFocus())
  })

  it("cancelling a removal changes nothing and keeps a failure from going unnoticed", async () => {
    const { user, calls } = start("/holidays?year=2026", asCno({ ...year2026(), "DELETE /api/hospital/public-holidays/h1": { status: 500 } }))

    const remove = await screen.findByRole("button", { name: "Remove National Day" })
    await user.click(remove)
    const dialog = await screen.findByRole("alertdialog")
    await user.click(within(dialog).getByRole("button", { name: "Remove holiday" }))
    expect(await within(dialog).findByRole("alert")).toHaveTextContent(/did not work/)
    await user.click(within(dialog).getByRole("button", { name: "Cancel" }))

    await waitFor(() => expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument())
    await waitFor(() => expect(remove).toHaveFocus())
    expect(screen.getByText("National Day")).toBeInTheDocument()
    expect(calls.filter((call) => call.method === "DELETE")).toHaveLength(1)
  })

  it("a month fixed to no days reopens as a list", async () => {
    const { user } = start("/holidays?year=2026", asCno(year2026({ ...MARCH, source: "fixed", dates: [] })))

    await user.click(await screen.findByRole("button", { name: "Fix the dates of March 2026" }))

    expect(screen.getByLabelText("A list of days")).toBeChecked()
  })

  it("another role reads and can change nothing", async () => {
    start("/holidays?year=2026", { ...session(NURSE), ...year2026() })

    expect(await screen.findByText("National Day")).toBeInTheDocument()
    expect(await screen.findByRole("cell", { name: "March 2026" })).toBeInTheDocument()
    expect(screen.getByRole("region", { name: "Ramadan dates in 2026" })).toHaveAttribute("tabindex", "0")
    expect(screen.queryByRole("button", { name: /Fix|Edit|Remove|Add/ })).not.toBeInTheDocument()
    expect(screen.queryByLabelText("Date")).not.toBeInTheDocument()
  })
})

const ER = { id: "u1", name: "ER", archived: false, manager: null, rules_need_review: true }
const MONA = { id: "m1", username: "mona", full_name: "Mona Ali" }
const OMAR = { id: "m2", username: "omar", full_name: "Omar Said" }

describe("a unit manager's home", () => {
  const asManager = (units: Answer) => ({
    ...session({ ...ME, username: "mona", full_name: "Mona Ali", role: "unit_manager" }),
    "GET /api/units": units,
  })

  it("shows the unit they hold and that its rules are still to be reviewed", async () => {
    start("/", asManager({ body: [{ ...ER, manager: MONA }] }))

    expect(await screen.findByText("Your unit is ER.")).toBeInTheDocument()
    expect(screen.getByText(/still the seeded defaults/)).toBeInTheDocument()
    expect(screen.queryByText(/No unit is assigned/)).not.toBeInTheDocument()
  })

  it("says nothing of a review once the rules are saved", async () => {
    start("/", asManager({ body: [{ ...ER, manager: MONA, rules_need_review: false }] }))

    expect(await screen.findByText("Your unit is ER.")).toBeInTheDocument()
    expect(screen.queryByText(/seeded defaults/)).not.toBeInTheDocument()
  })

  it("says no unit is assigned", async () => {
    start("/", asManager({ body: [] }))

    expect(await screen.findByText(/No unit is assigned to you yet/)).toBeInTheDocument()
  })

  it("does not claim no unit when the answer could not be read", async () => {
    start("/", asManager({ status: 500 }))

    expect(await screen.findByRole("alert")).toHaveTextContent(/could not be read/)
    expect(screen.queryByText(/No unit is assigned/)).not.toBeInTheDocument()
  })
})

describe("the CNO's home", () => {
  it("names the units with no manager and links to them", async () => {
    start("/", asCno({ "GET /api/units": { body: [ER, { ...ER, id: "u2", name: "ICU", manager: MONA }, { ...ER, id: "u3", name: "Old", archived: true }] } }))

    const warning = await screen.findByText(/have no manager|has no manager/)
    expect(warning).toHaveTextContent("ER has no manager.")
    expect(within(warning).getByRole("link", { name: "Assign one under Units" })).toHaveAttribute("href", "/units")
  })

  it("says nothing when every unit has one", async () => {
    start("/", asCno({ "GET /api/units": { body: [{ ...ER, manager: MONA }] } }))

    await screen.findByText(/under Hospital rules/)
    await waitFor(() => expect(vi.mocked(fetch)).toHaveBeenCalledWith("/api/units", expect.anything()))
    expect(screen.queryByText(/no manager/)).not.toBeInTheDocument()
  })
})

describe("the CNO's home when the units cannot be read", () => {
  it("says so rather than looking as though every unit has a manager", async () => {
    start("/", asCno({ "GET /api/units": { status: 500 } }))

    expect(await screen.findByRole("alert")).toHaveTextContent(/could not be read/)
  })
})

describe("the units page", () => {
  const CHOICES = [{ ...MONA, unit: "ICU" }, { ...OMAR, unit: null }]
  const ICU = { ...ER, id: "u2", name: "ICU", manager: MONA }
  const OLD = { ...ER, id: "u3", name: "Old", archived: true }
  const page = (extra = {}, units: unknown[] = [ER, ICU, OLD]) => asCno({
    "GET /api/units": { body: units },
    "GET /api/units/managers": { body: CHOICES },
    ...extra,
  })

  it("lists the units with their managers, and which have none", async () => {
    start("/units", page())

    const er = (await screen.findByRole("cell", { name: "ER" })).closest("tr")!
    expect(within(er).getByText("No manager")).toBeInTheDocument()
    const icu = screen.getByRole("cell", { name: "ICU" }).closest("tr")!
    expect(within(icu).getByText("Mona Ali")).toBeInTheDocument()
    expect(document.title).toBe("Units · Nurse roster")
  })

  it("an archived unit is on record and has nothing left to do", async () => {
    start("/units", page())

    const old = (await screen.findByRole("cell", { name: "Old" })).closest("tr")!
    expect(within(old).getByText("Archived")).toBeInTheDocument()
    expect(within(old).queryByRole("button")).not.toBeInTheDocument()
    expect(within(old).queryByText("No manager")).not.toBeInTheDocument()
  })

  it("says so when there are no units yet", async () => {
    start("/units", page({}, []))

    expect(await screen.findByText(/There are no units yet/)).toBeInTheDocument()
  })

  it("a manager who holds another unit cannot be chosen, and says which", async () => {
    start("/units", page())

    const select = await screen.findByLabelText("Manager")
    expect(within(select).getByRole("option", { name: "No manager yet" })).toBeEnabled()
    expect(within(select).getByRole("option", { name: "Mona Ali (mona, manages ICU)" })).toBeDisabled()
    expect(within(select).getByRole("option", { name: "Omar Said (omar)" })).toBeEnabled()
  })

  it("says who to ask when there are no manager accounts to choose", async () => {
    start("/units", page({ "GET /api/units/managers": { body: [] } }))

    expect(await screen.findByLabelText("Manager")).toHaveAccessibleDescription(/The System Admin creates unit manager accounts/)
  })

  it("adds a unit with its manager, and shows a taken name beside its field", async () => {
    const answers = [refusal(["name"], "ER is already a unit"), { status: 201, body: { ...ER, id: "u4", name: "CCU", manager: OMAR } }]
    const { user, calls } = start("/units", page({ "POST /api/units": () => answers.shift() as Answer }))

    await user.type(await screen.findByLabelText("Name"), "ER")
    await user.selectOptions(screen.getByLabelText("Manager"), "m2")
    await user.click(screen.getByRole("button", { name: "Add unit" }))
    await waitFor(() => expect(screen.getByLabelText("Name")).toHaveAccessibleDescription(/already a unit/))
    expect(screen.getByLabelText("Name")).toHaveFocus()

    await user.clear(screen.getByLabelText("Name"))
    await user.type(screen.getByLabelText("Name"), "CCU")
    await user.click(screen.getByRole("button", { name: "Add unit" }))

    expect(await screen.findByText("CCU is added.")).toBeInTheDocument()
    expect(calls.filter((call) => call.method === "POST").at(-1)?.body).toEqual({ name: "CCU", manager_id: "m2" })
    expect(screen.getByLabelText("Name")).toHaveValue("")
  })

  it("adding sends no manager as none, and needs a name", async () => {
    const { user, calls } = start("/units", page({ "POST /api/units": { status: 201, body: { ...ER, name: "CCU" } } }))

    await screen.findByLabelText("Name")
    await user.click(screen.getByRole("button", { name: "Add unit" }))
    expect(await screen.findByText("Enter a name.")).toBeInTheDocument()
    expect(calls.some((call) => call.method === "POST")).toBe(false)

    await user.type(screen.getByLabelText("Name"), "CCU")
    await user.click(screen.getByRole("button", { name: "Add unit" }))

    await screen.findByText("CCU is added.")
    expect(calls.find((call) => call.method === "POST")?.body).toEqual({ name: "CCU", manager_id: null })
  })

  it("renames and reassigns a unit, with its current manager offered and focus returned", async () => {
    const { user, calls } = start("/units", page({
      "PUT /api/units/u2": { body: { ...ICU, name: "Intensive care", manager: OMAR } },
    }))

    const edit = await screen.findByRole("button", { name: "Edit ICU" })
    await user.click(edit)
    expect(screen.getByRole("heading", { name: "Edit ICU" })).toBeInTheDocument()
    expect(screen.getByLabelText("Manager")).toHaveValue("m1")
    expect(within(screen.getByLabelText("Manager")).getByRole("option", { name: /Mona Ali/ })).toBeEnabled()

    await user.clear(screen.getByLabelText("Name"))
    await user.type(screen.getByLabelText("Name"), "Intensive care")
    await user.selectOptions(screen.getByLabelText("Manager"), "m2")
    await user.click(screen.getByRole("button", { name: "Save unit" }))

    expect(await screen.findByText("Intensive care is saved.")).toBeInTheDocument()
    expect(calls.find((call) => call.method === "PUT")?.body).toEqual({ name: "Intensive care", manager_id: "m2" })
    await waitFor(() => expect(edit).toHaveFocus())
  })

  it("shows a refused manager beside the select", async () => {
    const { user } = start("/units", page({
      "PUT /api/units/u1": refusal(["manager_id"], "omar already manages CCU."),
    }))

    await user.click(await screen.findByRole("button", { name: "Edit ER" }))
    await user.selectOptions(screen.getByLabelText("Manager"), "m2")
    await user.click(screen.getByRole("button", { name: "Save unit" }))

    await waitFor(() => expect(screen.getByLabelText("Manager")).toHaveAccessibleDescription(/already manages CCU/))
    expect(screen.getByLabelText("Manager")).toHaveFocus()
  })

  it("archives after asking, and focus lands where the next unit is entered", async () => {
    const { user, calls } = start("/units", page({ "POST /api/units/u2/archive": { body: { ...ICU, archived: true, manager: null } } }))

    await user.click(await screen.findByRole("button", { name: "Archive ICU" }))
    const dialog = screen.getByRole("alertdialog", { name: "Archive ICU?" })
    expect(within(dialog).getByText(/Mona Ali can then hold another unit/)).toBeInTheDocument()
    expect(calls.some((call) => call.url.endsWith("/archive"))).toBe(false)

    await user.click(within(dialog).getByRole("button", { name: "Archive" }))

    expect(await screen.findByText("ICU is archived.")).toBeInTheDocument()
    await waitFor(() => expect(screen.getByLabelText("Name")).toHaveFocus())
  })

  it("cancelling an archive changes nothing and returns focus to the row", async () => {
    const { user, calls } = start("/units", page())

    const button = await screen.findByRole("button", { name: "Archive ER" })
    await user.click(button)
    await user.click(within(screen.getByRole("alertdialog")).getByRole("button", { name: "Cancel" }))

    await waitFor(() => expect(button).toHaveFocus())
    expect(calls.some((call) => call.method === "POST")).toBe(false)
  })

  it("shows why an archive was refused and keeps the question open", async () => {
    const { user } = start("/units", page({
      "POST /api/units/u1/archive": refusal(["archived"], "2 nurses belong to ER. Transfer or deactivate them first."),
    }))

    await user.click(await screen.findByRole("button", { name: "Archive ER" }))
    await user.click(within(screen.getByRole("alertdialog")).getByRole("button", { name: "Archive" }))

    expect(await within(screen.getByRole("alertdialog")).findByRole("alert")).toHaveTextContent("2 nurses belong to ER")
  })

  it("leaves the form when the unit it is editing is archived", async () => {
    const { user } = start("/units", page({ "POST /api/units/u1/archive": { body: { ...ER, archived: true } } }))

    await user.click(await screen.findByRole("button", { name: "Edit ER" }))
    await user.click(screen.getByRole("button", { name: "Archive ER" }))
    await user.click(within(screen.getByRole("alertdialog")).getByRole("button", { name: "Archive" }))

    expect(await screen.findByRole("heading", { name: "Add a unit" })).toBeInTheDocument()
  })
})

describe("deactivating a manager who holds a unit", () => {
  it("the users page says which unit they hold and what becomes of it", async () => {
    const { user } = start("/users", admin({ "GET /api/users": { body: [{ ...MANAGER, unit: "ER" }] } }))

    expect(await screen.findByText("ER")).toBeInTheDocument()
    await user.click(screen.getByRole("button", { name: "Deactivate khalid" }))

    const dialog = screen.getByRole("alertdialog", { name: "Deactivate khalid?" })
    expect(within(dialog).getByText(/ER is left with no manager until the CNO assigns one/)).toBeInTheDocument()
    expect(within(dialog).getByText(/Reactivating them does not give it back/)).toBeInTheDocument()
  })

  it("says nothing of a unit for anyone else", async () => {
    const { user } = start("/users", admin({ "GET /api/users": { body: [{ ...MANAGER, unit: null }] } }))

    await user.click(await screen.findByRole("button", { name: "Deactivate khalid" }))

    expect(within(screen.getByRole("alertdialog")).queryByText(/no manager/)).not.toBeInTheDocument()
  })
})
