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
      const body = init.body instanceof FormData ? init.body : init.body ? JSON.parse(init.body as string) : undefined
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
  it.each(["/", "/health", "/settings", "/users", "/audit-log", "/hospital-rules", "/shifts", "/leave-types", "/holidays", "/units", "/unit-rules", "/rostering-attributes", "/nurses", "/leave", "/my-leave", "/change-password"])("%s sends a stranger to the login page", async (path) => {
    const { router } = start(path, session(null))

    expect(await screen.findByRole("button", { name: "Log in" })).toBeInTheDocument()
    expect(router.state.location.pathname).toBe("/login")
  })

  it.each(["/", "/health", "/settings", "/users", "/audit-log", "/hospital-rules", "/shifts", "/leave-types", "/holidays", "/units", "/unit-rules", "/rostering-attributes", "/nurses", "/leave", "/my-leave"])("%s sends a forced change to the password page", async (path) => {
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

  it.each(["/health", "/settings", "/users", "/audit-log", "/units", "/nurses"])("%s is not for another role", async (path) => {
    const { router, calls } = start(path, { ...session(NURSE), "GET /api/nurses/my-unit": { body: { id: "u1", name: "ER" } } })

    expect(await screen.findByText("No roster yet.")).toBeInTheDocument()
    expect(router.state.location.pathname).toBe("/")
    expect(screen.queryByRole("link", { name: "Technical settings" })).not.toBeInTheDocument()
    expect(calls.map((call) => call.url)).toEqual(["/api/auth/session", "/api/nurses/my-unit"])
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
    ["cno", "CNO", /under Hospital rules/, ["Home", "Units", "Unit rules", "Rostering attributes", "Nurses", "Leave", "Hospital rules", ...CATALOGUE_LINKS, "Change password"], ["/api/units"]],
    ["deputy_cno", "Deputy CNO", /Submitted rosters waiting for your decision/, ["Home", "Unit rules", "Rostering attributes", "Leave", "Hospital rules", ...CATALOGUE_LINKS, "Change password"], []],
    ["unit_manager", "Unit Manager", /No unit is assigned to you yet/, ["Home", "Unit rules", "Rostering attributes", "Nurses", "Leave", ...CATALOGUE_LINKS, "Change password"], ["/api/units"]],
    ["staff_nurse", "Staff Nurse", "No roster yet.", ["Home", "My leave", ...CATALOGUE_LINKS, "Change password"], ["/api/nurses/my-unit"]],
  ])("%s has a home of its own and none of the System Admin's pages", async (role, name, says, links, reads) => {
    const { router, calls } = start("/", {
      ...session({ ...ME, username: "someone", full_name: "Some One", role }),
      "GET /api/units": { body: [] },
      "GET /api/nurses/my-unit": { body: { id: "u1", name: "ER" } },
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

  describe("correcting a name", () => {
    const url = `/api/users/${MANAGER.id}/full-name`

    it("saves the name, says so and puts focus back on the row, with the create form back too", async () => {
      let users = [CNO, MANAGER]
      const { user, calls } = start("/users", admin({
        "GET /api/users": () => ({ body: users }),
        [`PUT ${url}`]: () => {
          users = [CNO, { ...MANAGER, full_name: "Khalid Omari" }]
          return { body: users[1] }
        },
      }))

      const button = await screen.findByRole("button", { name: "Correct name of khalid" })
      await user.click(button)

      expect(screen.getByRole("heading", { name: "Correct the name of khalid" })).toBeInTheDocument()
      expect(screen.queryByRole("heading", { name: "Create a user" })).not.toBeInTheDocument()
      const field = screen.getByLabelText("Full name")
      expect(field).toHaveValue("Khalid Omar")
      expect(field).toHaveFocus()
      expect(screen.getByText("khalid", { selector: "span" })).toBeInTheDocument()

      await user.clear(field)
      await user.type(field, "  Khalid Omari ")
      await user.click(screen.getByRole("button", { name: "Save name" }))

      expect(await screen.findByRole("status")).toHaveTextContent("The name of khalid is now Khalid Omari.")
      expect(calls.find((call) => call.method === "PUT")?.body).toEqual({ full_name: "Khalid Omari" })
      expect(await screen.findByRole("cell", { name: "Khalid Omari" })).toBeInTheDocument()
      expect(screen.getByRole("heading", { name: "Create a user" })).toBeInTheDocument()
      await waitFor(() => expect(screen.getByRole("button", { name: "Correct name of khalid" })).toHaveFocus())
    })

    it("says so when nothing changed", async () => {
      const { user } = start("/users", page([CNO, MANAGER], { [`PUT ${url}`]: { body: MANAGER } }))

      await user.click(await screen.findByRole("button", { name: "Correct name of khalid" }))
      await user.click(screen.getByRole("button", { name: "Save name" }))

      expect(await screen.findByRole("status")).toHaveTextContent("Nothing changed for khalid.")
    })

    it("refuses a blank name itself, beside the field with focus on it", async () => {
      const { user, calls } = start("/users", page([CNO, MANAGER]))

      await user.click(await screen.findByRole("button", { name: "Correct name of khalid" }))
      await user.clear(screen.getByLabelText("Full name"))
      await user.click(screen.getByRole("button", { name: "Save name" }))

      expect(await screen.findByText("Enter their full name.")).toBeInTheDocument()
      expect(screen.getByLabelText("Full name")).toHaveFocus()
      expect(calls.some((call) => call.method === "PUT")).toBe(false)
    })

    it("shows the API's refusal beside the field with focus on it", async () => {
      const { user } = start("/users", page([CNO, MANAGER], {
        [`PUT ${url}`]: { status: 422, body: { detail: [{ loc: ["body", "body", "full_name"], msg: "Value error, not a possible name" }] } },
      }))

      await user.click(await screen.findByRole("button", { name: "Correct name of khalid" }))
      await user.click(screen.getByRole("button", { name: "Save name" }))

      expect(await screen.findByText("not a possible name")).toBeInTheDocument()
      expect(screen.getByLabelText("Full name")).toHaveFocus()
      expect(screen.queryByRole("alert")).not.toBeInTheDocument()
    })

    it("says so when the save fails for any other reason, and stays open", async () => {
      const { user } = start("/users", page([CNO, MANAGER], { [`PUT ${url}`]: { status: 500, body: {} } }))

      await user.click(await screen.findByRole("button", { name: "Correct name of khalid" }))
      await user.click(screen.getByRole("button", { name: "Save name" }))

      expect(await screen.findByRole("alert")).toHaveTextContent("The name could not be saved.")
      expect(screen.getByRole("heading", { name: "Correct the name of khalid" })).toBeInTheDocument()
    })

    it("Cancel saves nothing and puts focus back on the row", async () => {
      const { user, calls } = start("/users", page([CNO, MANAGER]))

      await user.click(await screen.findByRole("button", { name: "Correct name of khalid" }))
      await user.click(screen.getByRole("button", { name: "Cancel" }))

      expect(screen.getByRole("heading", { name: "Create a user" })).toBeInTheDocument()
      expect(screen.getByRole("button", { name: "Correct name of khalid" })).toHaveFocus()
      expect(calls.some((call) => call.method === "PUT")).toBe(false)
    })

    it("is offered for a deactivated account", async () => {
      start("/users", page([{ ...MANAGER, is_active: false }]))

      expect(await screen.findByRole("button", { name: "Correct name of khalid" })).toBeEnabled()
    })
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

describe("a staff nurse's home", () => {
  it("shows their unit and that there is no roster yet", async () => {
    start("/", { ...session(NURSE), "GET /api/nurses/my-unit": { body: { id: "u1", name: "ER" } } })

    expect(await screen.findByText("Your unit is ER.")).toBeInTheDocument()
    expect(screen.getByText("No roster yet.")).toBeInTheDocument()
  })

  it("does not claim a unit or a roster when the answer could not be read", async () => {
    start("/", { ...session(NURSE), "GET /api/nurses/my-unit": { status: 500 } })

    expect(await screen.findByRole("alert")).toHaveTextContent(/could not be read/)
    expect(screen.queryByText("No roster yet.")).not.toBeInTheDocument()
  })
})

describe("the nurses page", () => {
  const UNIT_ER = { id: "u1", name: "ER", archived: false, manager: null, rules_need_review: true }
  const UNIT_ICU = { ...UNIT_ER, id: "u2", name: "ICU" }
  const UNIT_OLD = { ...UNIT_ER, id: "u3", name: "Old", archived: true }
  const AMAL = {
    id: "n1", hospital_id: "h123", full_name: "Amal Saleh", role: "staff_nurse", gender: "F", start_date: "2026-01-10",
    end_date: null, is_active: true, must_change_password: false, unit: { id: "u1", name: "ER" }, transfers: [],
  }
  const BADR = { ...AMAL, id: "n2", hospital_id: "h124", full_name: "Badr Omar", gender: "M", unit: { id: "u2", name: "ICU" } }
  const MONA_NURSE = { ...AMAL, id: "n3", hospital_id: "mona", full_name: "Mona Ali", role: "unit_manager" }
  const CHOICE = { id: "m1", username: "mona", full_name: "Mona Ali", unit: { id: "u1", name: "ER" } }
  const refusal = (loc: string[], msg: string) => ({ status: 422, body: { detail: [{ type: "value_error", loc: ["body", "body", ...loc], msg }] } })

  const asCnoHere = (extra = {}, nurses: unknown[] = [AMAL, BADR]) => ({
    ...session({ ...ME, username: "chief", full_name: "The Chief", role: "cno" }),
    "GET /api/nurses": { body: nurses },
    "GET /api/nurses/managers": { body: [CHOICE] },
    "GET /api/units": { body: [UNIT_ER, UNIT_ICU, UNIT_OLD] },
    ...extra,
  })
  const asManagerHere = (nurses: unknown[], units: unknown[] = [UNIT_ER], extra = {}) => ({
    ...session({ ...ME, username: "mona", full_name: "Mona Ali", role: "unit_manager" }),
    "GET /api/nurses": { body: nurses },
    "GET /api/units": { body: units },
    ...extra,
  })

  it("lists every nurse with their unit for the CNO, and names the page", async () => {
    start("/nurses", asCnoHere())

    const row = (await screen.findByText("Amal Saleh")).closest("tr") as HTMLElement
    expect(within(row).getByText("h123")).toBeInTheDocument()
    expect(within(row).getByText("ER")).toBeInTheDocument()
    expect(within(row).getByText("Female")).toBeInTheDocument()
    expect(within(row).getByText("10 Jan 2026")).toBeInTheDocument()
    expect(within(row).getByText("Active")).toBeInTheDocument()
    expect(screen.getByRole("heading", { level: 1, name: "Nurses" })).toBeInTheDocument()
    expect(document.title).toBe("Nurses · Nurse roster")
  })

  it("narrows the list to one unit", async () => {
    const { user, router } = start("/nurses", asCnoHere())
    await screen.findByText("Amal Saleh")

    await user.selectOptions(screen.getByLabelText("Show"), "ICU")

    expect(screen.queryByText("Amal Saleh")).not.toBeInTheDocument()
    expect(screen.getByText("Badr Omar")).toBeInTheDocument()
    await waitFor(() => expect(router.state.location.search).toEqual({ unit: "u2" }))
  })

  it("keeps the unit it narrows to in the address, and counts a nurse due to join", async () => {
    start("/nurses?unit=u2", asCnoHere({}, [{ ...AMAL, transfers: [{ from_month: "2027-01", unit: { id: "u2", name: "ICU" } }] }, MONA_NURSE]))

    expect(await screen.findByText("Amal Saleh")).toBeInTheDocument()
    expect(screen.getByLabelText("Show")).toHaveValue("u2")
    expect(screen.queryByText("Mona Ali")).not.toBeInTheDocument()
  })

  it("does not take a unit in the address that is not there", async () => {
    start("/nurses?unit=gone", asCnoHere())

    expect(await screen.findByText("Amal Saleh")).toBeInTheDocument()
    expect(screen.getByText("Badr Omar")).toBeInTheDocument()
    expect(screen.getByLabelText("Show")).toHaveValue("")
  })

  it("says so when a unit it narrows to has nobody this month", async () => {
    const { user } = start("/nurses", asCnoHere({}, [AMAL]))
    await screen.findByText("Amal Saleh")

    await user.selectOptions(screen.getByLabelText("Show"), "ICU")

    expect(screen.getByText("No nurse is in this unit or due to join it.")).toBeInTheDocument()
    expect(screen.queryByRole("table")).not.toBeInTheDocument()
  })

  it("says so when the nurses cannot be read", async () => {
    start("/nurses", asCnoHere({ "GET /api/nurses": { status: 500 } }))

    expect(await screen.findByRole("alert")).toHaveTextContent(/could not be read/)
  })

  it("says so when there are no nurses yet", async () => {
    start("/nurses", asCnoHere({}, []))

    expect(await screen.findByText(/There are no nurses yet/)).toBeInTheDocument()
  })

  it("adds a nurse, shows the password once and then forgets it", async () => {
    const { user, calls } = start("/nurses", asCnoHere({
      "POST /api/nurses": { status: 201, body: { nurse: AMAL, generated_password: "abcd-efgh-jkmn-pqrs" } },
    }))

    const opener = await screen.findByRole("button", { name: "Add a nurse" })
    await user.click(opener)
    await waitFor(() => expect(screen.getByLabelText("Hospital ID")).toHaveFocus())
    await user.type(screen.getByLabelText("Hospital ID"), "h123")
    await user.type(screen.getByLabelText("Full name"), "Amal Saleh")
    await user.selectOptions(screen.getByLabelText("Gender"), "Female")
    expect(within(screen.getByLabelText("Unit")).queryByRole("option", { name: "Old" })).not.toBeInTheDocument()
    await user.selectOptions(screen.getByLabelText("Unit"), "ER")
    await user.type(screen.getByLabelText("Start date"), "2026-01-10")
    await user.click(screen.getByRole("button", { name: "Add nurse" }))

    const dialog = await screen.findByRole("alertdialog", { name: "Password for h123" })
    expect(within(dialog).getByLabelText("Generated password")).toHaveValue("abcd-efgh-jkmn-pqrs")
    expect(calls.find((call) => call.method === "POST")?.body).toEqual({
      hospital_id: "h123", full_name: "Amal Saleh", gender: "F", unit_id: "u1", start_date: "2026-01-10",
    })

    await user.click(within(dialog).getByRole("button", { name: "Done" }))

    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument()
    expect(screen.queryByDisplayValue("abcd-efgh-jkmn-pqrs")).not.toBeInTheDocument()
    expect(screen.queryByLabelText("Hospital ID")).not.toBeInTheDocument()
  })

  it("asks for what is missing before sending anything", async () => {
    const { user, calls } = start("/nurses", asCnoHere())

    await user.click(await screen.findByRole("button", { name: "Add a nurse" }))
    await user.click(screen.getByRole("button", { name: "Add nurse" }))

    expect(await screen.findByText("Enter their hospital ID.")).toBeInTheDocument()
    expect(screen.getByText("Choose a unit.")).toBeInTheDocument()
    expect(calls.some((call) => call.method === "POST")).toBe(false)
  })

  it("puts a taken hospital ID beside its field with focus on it", async () => {
    const { user } = start("/nurses", asCnoHere({
      "POST /api/nurses": refusal(["hospital_id"], "h123 is already in use."),
    }))

    await user.click(await screen.findByRole("button", { name: "Add a nurse" }))
    await user.type(screen.getByLabelText("Hospital ID"), "h123")
    await user.type(screen.getByLabelText("Full name"), "Amal Saleh")
    await user.selectOptions(screen.getByLabelText("Gender"), "Male")
    await user.selectOptions(screen.getByLabelText("Unit"), "ICU")
    await user.type(screen.getByLabelText("Start date"), "2026-01-10")
    await user.click(screen.getByRole("button", { name: "Add nurse" }))

    expect(await screen.findByText("h123 is already in use.")).toBeInTheDocument()
    expect(screen.getByLabelText("Hospital ID")).toHaveFocus()
  })

  it("gives a unit manager a nurse profile, starting from the unit they hold, with no password", async () => {
    const { user, calls } = start("/nurses", asCnoHere({
      "POST /api/nurses/managers": { status: 201, body: MONA_NURSE },
    }))

    await user.click(await screen.findByRole("button", { name: "Give a unit manager a nurse profile" }))
    await user.selectOptions(await screen.findByLabelText("Unit manager"), "Mona Ali (mona)")
    expect(screen.getByLabelText("Unit")).toHaveValue("u1")
    await user.selectOptions(screen.getByLabelText("Gender"), "Female")
    await user.type(screen.getByLabelText("Start date"), "2026-01-10")
    await user.click(screen.getByRole("button", { name: "Give profile" }))

    expect(await screen.findByText(/Mona Ali now has a nurse profile/)).toBeInTheDocument()
    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument()
    expect(calls.find((call) => call.method === "POST")?.body).toEqual({
      user_id: "m1", gender: "F", unit_id: "u1", start_date: "2026-01-10",
    })
  })

  it("transfers from a chosen month and returns focus to the row", async () => {
    const waiting = { ...AMAL, transfers: [{ from_month: "2027-01", unit: { id: "u2", name: "ICU" } }] }
    const { user, calls } = start("/nurses", asCnoHere({ "POST /api/nurses/n1/transfer": { body: waiting } }))

    const opener = await screen.findByRole("button", { name: "Transfer Amal Saleh" })
    await user.click(opener)
    await waitFor(() => expect(screen.getByLabelText("To unit")).toHaveFocus())
    expect(within(screen.getByLabelText("To unit")).queryByRole("option", { name: "Old" })).not.toBeInTheDocument()
    await user.selectOptions(screen.getByLabelText("To unit"), "ICU")
    const months = within(screen.getByLabelText("Effective from")).getAllByRole("option")
    await user.selectOptions(screen.getByLabelText("Effective from"), months[2])
    await user.click(screen.getByRole("button", { name: "Transfer" }))

    await waitFor(() => expect(calls.find((call) => call.method === "POST")?.body).toMatchObject({ unit_id: "u2" }))
    const body = calls.find((call) => call.method === "POST")?.body as { from_month: string }
    expect(body.from_month).toMatch(/^\d{4}-\d{2}$/)
    expect(await screen.findByText(/Amal Saleh transfers to ICU from/)).toBeInTheDocument()
    await waitFor(() => expect(opener).toHaveFocus())
  })

  it("shows a transfer waiting on the row", async () => {
    start("/nurses", asCnoHere({}, [{ ...AMAL, transfers: [{ from_month: "2027-01", unit: { id: "u2", name: "ICU" } }] }]))

    expect(await screen.findByText("ICU from January 2027")).toBeInTheDocument()
  })

  it("puts a refused transfer beside its field", async () => {
    const { user } = start("/nurses", asCnoHere({
      "POST /api/nurses/n1/transfer": refusal(["unit_id"], "Amal Saleh is already in ER from that month."),
    }))

    await user.click(await screen.findByRole("button", { name: "Transfer Amal Saleh" }))
    await user.selectOptions(screen.getByLabelText("To unit"), "ER")
    await user.selectOptions(screen.getByLabelText("Effective from"), within(screen.getByLabelText("Effective from")).getAllByRole("option")[1])
    await user.click(screen.getByRole("button", { name: "Transfer" }))

    expect(await screen.findByText(/already in ER from that month/)).toBeInTheDocument()
  })

  it("sets an end date and says what became of the account", async () => {
    const { user, calls } = start("/nurses", asCnoHere({
      "PUT /api/nurses/n1/end-date": { body: { ...AMAL, end_date: "2026-11-05", is_active: false } },
    }))

    await user.click(await screen.findByRole("button", { name: "Set end date of Amal Saleh" }))
    expect(screen.getByText(/deactivates them at once/)).toBeInTheDocument()
    await user.type(screen.getByLabelText("End date"), "2026-11-05")
    await user.click(screen.getByRole("button", { name: "Save end date" }))

    expect(await screen.findByText("Amal Saleh is deactivated.")).toBeInTheDocument()
    expect(calls.find((call) => call.method === "PUT")?.body).toEqual({ end_date: "2026-11-05" })
  })

  it("says a later end date leaves them active until then", async () => {
    const { user } = start("/nurses", asCnoHere({
      "PUT /api/nurses/n1/end-date": { body: { ...AMAL, end_date: "2076-11-05" } },
    }))

    await user.click(await screen.findByRole("button", { name: "Set end date of Amal Saleh" }))
    await user.type(screen.getByLabelText("End date"), "2076-11-05")
    await user.click(screen.getByRole("button", { name: "Save end date" }))

    expect(await screen.findByText(/stays active until 5 Nov 2076/)).toBeInTheDocument()
  })

  it("says a manager's profile ends with their account as it was", async () => {
    const { user } = start("/nurses", asCnoHere({
      "PUT /api/nurses/n3/end-date": { body: { ...MONA_NURSE, end_date: "2026-01-20" } },
    }, [MONA_NURSE]))

    await user.click(await screen.findByRole("button", { name: "Set end date of Mona Ali" }))
    expect(screen.getByText(/Their account stays as it is/)).toBeInTheDocument()
    await user.type(screen.getByLabelText("End date"), "2026-01-20")
    await user.click(screen.getByRole("button", { name: "Save end date" }))

    expect(await screen.findByText("The end date of Mona Ali is 20 Jan 2026. Their account stays active.")).toBeInTheDocument()
  })

  it("clears an end date, and a refusal stays on the field", async () => {
    const ended = { ...AMAL, end_date: "2026-11-05", is_active: false }
    const { user, calls } = start("/nurses", asCnoHere({
      "PUT /api/nurses/n1/end-date": refusal(["end_date"], "ER is archived. Transfer Amal Saleh first."),
    }, [ended]))

    expect(await screen.findByText("Deactivated")).toBeInTheDocument()
    expect(screen.getByText("End date 5 Nov 2026")).toBeInTheDocument()
    await user.click(screen.getByRole("button", { name: "Change end date of Amal Saleh" }))
    expect(screen.getByLabelText("End date")).toHaveValue("2026-11-05")
    await user.click(screen.getByRole("button", { name: "Clear end date" }))

    expect(await screen.findByText(/ER is archived/)).toBeInTheDocument()
    expect(calls.find((call) => call.method === "PUT")?.body).toEqual({ end_date: null })
  })

  it("opens with what the nurse has, corrects all three and says so, with focus back on the row", async () => {
    const { user, calls } = start("/nurses", asCnoHere({
      "PUT /api/nurses/n1/details": { body: { nurse: { ...AMAL, full_name: "Amal Salih", gender: "M", start_date: "2026-02-01" }, first_placement_extended: null } },
    }))

    const opener = await screen.findByRole("button", { name: "Correct details of Amal Saleh" })
    await user.click(opener)
    expect(screen.getByRole("heading", { name: "Correct the details of Amal Saleh" })).toBeInTheDocument()
    expect(screen.getByLabelText("Full name")).toHaveFocus()
    expect(screen.getByLabelText("Full name")).toHaveValue("Amal Saleh")
    expect(screen.getByLabelText("Gender")).toHaveValue("F")
    expect(screen.getByLabelText("Start date")).toHaveValue("2026-01-10")
    expect(screen.getByText(/cannot be corrected, because it is their username/)).toHaveTextContent("Hospital ID h123")
    expect(screen.queryByRole("textbox", { name: /Hospital ID/ })).not.toBeInTheDocument()

    await user.clear(screen.getByLabelText("Full name"))
    await user.type(screen.getByLabelText("Full name"), "  Amal Salih ")
    await user.selectOptions(screen.getByLabelText("Gender"), "Male")
    await user.clear(screen.getByLabelText("Start date"))
    await user.type(screen.getByLabelText("Start date"), "2026-02-01")
    await user.click(screen.getByRole("button", { name: "Save details" }))

    expect(await screen.findByText("The details of Amal Salih are corrected.")).toBeInTheDocument()
    expect(calls.find((call) => call.method === "PUT")?.body).toEqual({ full_name: "Amal Salih", gender: "M", start_date: "2026-02-01" })
    expect(screen.queryByRole("heading", { name: /Correct the details/ })).not.toBeInTheDocument()
    await waitFor(() => expect(opener).toHaveFocus())
  })

  it("keeps focus on the row when a new name moves it down the list", async () => {
    const renamed = { ...AMAL, full_name: "Zaina Saleh" }
    const nurses = { body: [AMAL, BADR] }
    const { user } = start("/nurses", asCnoHere({
      "GET /api/nurses": nurses,
      "PUT /api/nurses/n1/details": () => { nurses.body = [BADR, renamed]; return { body: { nurse: renamed, first_placement_extended: null } } },
    }))

    const opener = await screen.findByRole("button", { name: "Correct details of Amal Saleh" })
    await user.click(opener)
    await user.clear(screen.getByLabelText("Full name"))
    await user.type(screen.getByLabelText("Full name"), "Zaina Saleh")
    await user.click(screen.getByRole("button", { name: "Save details" }))

    const moved = await screen.findByRole("button", { name: "Correct details of Zaina Saleh" })
    await waitFor(() => expect(moved).toHaveFocus())
  })

  it("says when a start date began their time in a unit earlier", async () => {
    const { user } = start("/nurses", asCnoHere({
      "PUT /api/nurses/n1/details": { body: { nurse: { ...AMAL, start_date: "2025-10-05" }, first_placement_extended: { unit: { id: "u1", name: "ER" }, from_month: "2025-10" } } },
    }))

    await user.click(await screen.findByRole("button", { name: "Correct details of Amal Saleh" }))
    expect(screen.getByText(/before their first month in a unit/)).toBeInTheDocument()
    await user.clear(screen.getByLabelText("Start date"))
    await user.type(screen.getByLabelText("Start date"), "2025-10-05")
    await user.click(screen.getByRole("button", { name: "Save details" }))

    expect(await screen.findByText("The details of Amal Saleh are corrected. Their time in ER now begins in October 2025.")).toBeInTheDocument()
  })

  it("says when a save changed nothing", async () => {
    const { user } = start("/nurses", asCnoHere({
      "PUT /api/nurses/n1/details": { body: { nurse: AMAL, first_placement_extended: null } },
    }))

    await user.click(await screen.findByRole("button", { name: "Correct details of Amal Saleh" }))
    await user.click(screen.getByRole("button", { name: "Save details" }))

    expect(await screen.findByText("Nothing changed for Amal Saleh.")).toBeInTheDocument()
  })

  it("asks for what is empty, without calling the API", async () => {
    const { user, calls } = start("/nurses", asCnoHere())

    await user.click(await screen.findByRole("button", { name: "Correct details of Amal Saleh" }))
    await user.clear(screen.getByLabelText("Full name"))
    await user.clear(screen.getByLabelText("Start date"))
    await user.click(screen.getByRole("button", { name: "Save details" }))

    expect(await screen.findByText("Enter their full name.")).toBeInTheDocument()
    expect(screen.getByText("Enter the start date.")).toBeInTheDocument()
    expect(screen.getByLabelText("Full name")).toHaveFocus()
    expect(calls.some((call) => call.method === "PUT")).toBe(false)
  })

  it("puts a refused start date beside its field, with focus on it, and stays open", async () => {
    const { user } = start("/nurses", asCnoHere({
      "PUT /api/nurses/n1/details": refusal(["start_date"], "The start date cannot be after the end date. Change the end date first."),
    }))

    await user.click(await screen.findByRole("button", { name: "Correct details of Amal Saleh" }))
    await user.clear(screen.getByLabelText("Start date"))
    await user.type(screen.getByLabelText("Start date"), "2027-01-01")
    await user.click(screen.getByRole("button", { name: "Save details" }))

    expect(await screen.findByText(/cannot be after the end date/)).toBeInTheDocument()
    expect(screen.getByLabelText("Start date")).toHaveFocus()
    expect(screen.getByLabelText("Start date")).toHaveAttribute("aria-invalid", "true")
  })

  it("says plainly when a correction could not be saved", async () => {
    const { user } = start("/nurses", asCnoHere({ "PUT /api/nurses/n1/details": { status: 500, body: {} } }))

    await user.click(await screen.findByRole("button", { name: "Correct details of Amal Saleh" }))
    await user.click(screen.getByRole("button", { name: "Save details" }))

    expect(await screen.findByRole("alert")).toHaveTextContent("That did not work")
  })

  it("keeps a manager's name as it is, because it is on their account, and starts from their gender", async () => {
    const { user, calls } = start("/nurses", asCnoHere({
      "PUT /api/nurses/n3/details": { body: { nurse: { ...MONA_NURSE, gender: "M" }, first_placement_extended: null } },
    }, [MONA_NURSE]))

    await user.click(await screen.findByRole("button", { name: "Correct details of Mona Ali" }))
    expect(screen.getByLabelText("Full name")).toHaveAttribute("readonly")
    expect(screen.getByLabelText("Full name")).toHaveAccessibleDescription(/The System Admin can correct it/)
    expect(screen.getByLabelText("Gender")).toHaveFocus()
    await user.selectOptions(screen.getByLabelText("Gender"), "Male")
    await user.click(screen.getByRole("button", { name: "Save details" }))

    expect(await screen.findByText("The details of Mona Ali are corrected.")).toBeInTheDocument()
    expect(calls.find((call) => call.method === "PUT")?.body).toEqual({ gender: "M", start_date: MONA_NURSE.start_date })
  })

  it("offers a manager no correction", async () => {
    start("/nurses", asManagerHere([AMAL]))

    expect(await screen.findByRole("button", { name: "Reset password of Amal Saleh" })).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /Correct details/ })).not.toBeInTheDocument()
  })

  it("asks before resetting a password, then shows the new one once", async () => {
    const { user, calls } = start("/nurses", asCnoHere({
      "POST /api/nurses/n1/reset-password": { body: { nurse: AMAL, generated_password: "wxyz-wxyz-wxyz-wxyz" } },
    }))

    await user.click(await screen.findByRole("button", { name: "Reset password of Amal Saleh" }))
    const question = screen.getByRole("alertdialog", { name: "Reset the password of h123?" })
    expect(calls.some((call) => call.method === "POST")).toBe(false)
    await user.click(within(question).getByRole("button", { name: "Reset password" }))

    const dialog = await screen.findByRole("alertdialog", { name: "Password for h123" })
    expect(within(dialog).getByLabelText("Generated password")).toHaveValue("wxyz-wxyz-wxyz-wxyz")
  })

  it("offers no reset for a manager, whose account is the System Admin's", async () => {
    start("/nurses", asCnoHere({}, [MONA_NURSE]))

    expect(await screen.findByText("Unit Manager")).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Reset password of Mona Ali" })).not.toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Transfer Mona Ali" })).toBeInTheDocument()
  })

  it("gives a manager their unit's list with resets only, and nothing the CNO changes", async () => {
    const { calls } = start("/nurses", asManagerHere([AMAL]))

    expect(await screen.findByRole("heading", { level: 1, name: "Nurses of ER" })).toBeInTheDocument()
    expect(await screen.findByRole("button", { name: "Reset password of Amal Saleh" })).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Add a nurse" })).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /Transfer/ })).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /end date/ })).not.toBeInTheDocument()
    expect(screen.queryByRole("columnheader", { name: "Unit" })).not.toBeInTheDocument()
    expect(calls.some((call) => call.url === "/api/nurses/managers")).toBe(false)
  })

  it("tells a manager who is joining and who is leaving, and offers no reset for one not yet theirs", async () => {
    start("/nurses", asManagerHere([
      { ...AMAL, unit: null, transfers: [{ from_month: "2027-01", unit: { id: "u1", name: "ER" } }] },
      { ...BADR, unit: { id: "u1", name: "ER" }, transfers: [{ from_month: "2027-02", unit: null }] },
    ]))

    expect(await screen.findByText("Joins from January 2027")).toBeInTheDocument()
    expect(screen.getByText("Leaves from February 2027")).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Reset password of Amal Saleh" })).not.toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Reset password of Badr Omar" })).toBeInTheDocument()
  })

  it("says nothing to a manager of transfers that do not touch their unit", async () => {
    start("/nurses", asManagerHere([{
      ...AMAL,
      unit: null,
      transfers: [{ from_month: "2027-01", unit: null }, { from_month: "2027-03", unit: { id: "u1", name: "ER" } }],
    }]))

    expect(await screen.findByText("Joins from March 2027")).toBeInTheDocument()
    expect(screen.queryByText(/Leaves from/)).not.toBeInTheDocument()
  })

  it("lets a keyboard scroll a manager's table when nothing in it can take focus", async () => {
    start("/nurses", asManagerHere([MONA_NURSE]))

    expect(await screen.findByRole("region", { name: "Nurses of ER" })).toHaveAttribute("tabindex", "0")
  })

  it("says so to a manager with no unit, or with no nurses yet", async () => {
    start("/nurses", asManagerHere([], []))

    expect(await screen.findByText(/No unit is assigned to you yet/)).toBeInTheDocument()
  })

  it("says so to a manager whose unit has no nurses yet", async () => {
    start("/nurses", asManagerHere([]))

    expect(await screen.findByText(/ER has no nurses yet/)).toBeInTheDocument()
  })
})

describe("importing nurses", () => {
  const CHIEF = { ...ME, username: "chief", full_name: "The Chief", role: "cno" }
  const here = (extra = {}) => ({ ...session(CHIEF), ...extra })
  const ROW = { line: 2, hospital_id: "h1", full_name: "Amal Saleh", gender: "F", unit: "ER", start_date: "2026-01-10", problems: [] }
  const ROW_2 = { ...ROW, line: 3, hospital_id: "h2", full_name: "Badr Omar", gender: "M" }
  const BAD = { ...ROW_2, gender: "X", problems: [{ column: "gender", message: "Use F or M." }, { column: null, message: "Something about the line." }] }
  const GOOD = { rows: [ROW, ROW_2], token: "the-token" }
  const SHEET = { rows: [
    { hospital_id: "h1", full_name: "Amal Saleh", unit: "ER", generated_password: "aaaa-bbbb-cccc-dddd" },
    { hospital_id: "h2", full_name: "=Badr\t=1+1", unit: "ER", generated_password: "eeee-ffff-gggg-hhhh" },
  ] }
  const csv = (content = "a file", name = "nurses.csv") => new File([content], name, { type: "text/csv" })

  async function check(user: ReturnType<typeof userEvent.setup>, file = csv()) {
    await user.upload(await screen.findByLabelText("CSV file"), file)
    await user.click(screen.getByRole("button", { name: "Check file" }))
  }

  it("offers the CNO the template", async () => {
    const { router } = start("/nurses/import", here())

    const link = await screen.findByRole("link", { name: "Download the template" })
    expect(link).toHaveAttribute("href", "/api/nurses/import/template")
    expect(link).toHaveAttribute("download")
    expect(document.title).toBe("Import nurses · Nurse roster")
    expect(router.state.location.pathname).toBe("/nurses/import")
  })

  it("sends a unit manager home", async () => {
    const { router } = start("/nurses/import", {
      ...session({ ...ME, username: "mona", role: "unit_manager" }),
      "GET /api/units": { body: [] },
    })

    await waitFor(() => expect(router.state.location.pathname).toBe("/"))
  })

  it("asks for a file, and refuses a large one before sending it", async () => {
    const { user, calls } = start("/nurses/import", here())
    await screen.findByLabelText("CSV file")

    await user.click(screen.getByRole("button", { name: "Check file" }))
    expect(await screen.findByText("Choose a CSV file.")).toBeInTheDocument()

    await check(user, csv("x".repeat(1024 * 1024 + 1)))
    expect(await screen.findByText(/larger than 1 MB/)).toBeInTheDocument()
    expect(screen.getByLabelText("CSV file")).toHaveFocus()
    expect(calls.filter((call) => call.method === "POST")).toEqual([])
  })

  it("shows a refusal of the whole file beside the field", async () => {
    const { user } = start("/nurses/import", here({
      "POST /api/nurses/import/preview": { status: 422, body: { detail: [{ type: "value_error", loc: ["body", "body", "file"], msg: "This is not a CSV file in UTF-8." }] } },
    }))

    await check(user)

    expect(await screen.findByText("This is not a CSV file in UTF-8.")).toBeInTheDocument()
    expect(screen.getByLabelText("CSV file")).toHaveFocus()
  })

  it("says so when the check itself fails", async () => {
    const { user } = start("/nurses/import", here({ "POST /api/nurses/import/preview": { status: 500 } }))

    await check(user)

    expect(await screen.findByRole("alert")).toHaveTextContent("That did not work")
  })

  it("shows only the lines with problems, each named, and offers nothing to confirm", async () => {
    const { user, calls } = start("/nurses/import", here({
      "POST /api/nurses/import/preview": { body: { rows: [ROW, BAD], token: null } },
    }))

    await check(user)

    const heading = await screen.findByRole("heading", { name: "1 of 2 lines has a problem" })
    expect(heading).toHaveFocus()
    expect(screen.getByText("Gender: Use F or M.")).toBeInTheDocument()
    expect(screen.getByText("Something about the line.")).toBeInTheDocument()
    expect(screen.getByText("Badr Omar")).toBeInTheDocument()
    expect(screen.queryByText("Amal Saleh")).not.toBeInTheDocument()
    expect(screen.getByText(/The other line has no problem/)).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /^Add/ })).not.toBeInTheDocument()
    const sent = calls.find((call) => call.method === "POST")
    expect((sent?.body as FormData).get("file")).toBeInstanceOf(Blob)
    expect(sent?.headers.has("Content-Type")).toBe(false)
  })

  it("confirms the very bytes it checked, with the preview's token, and shows the sheet with no way back to it", async () => {
    let confirmed: FormData | undefined
    const { user, calls } = start("/nurses/import", here({
      "POST /api/nurses/import/preview": { body: GOOD },
      "POST /api/nurses/import/confirm": ({ body }: { body: unknown }) => { confirmed = body as FormData; return { status: 201, body: SHEET } },
    }))

    await check(user, csv("the bytes"))
    expect(await screen.findByRole("heading", { name: "2 nurses ready to add" })).toHaveFocus()
    expect(calls.filter((call) => call.url.includes("confirm"))).toEqual([])
    await user.click(screen.getByRole("button", { name: "Add 2 nurses" }))

    expect(await screen.findByRole("heading", { name: "Passwords for 2 nurses" })).toHaveFocus()
    expect(screen.getByText("aaaa-bbbb-cccc-dddd")).toBeInTheDocument()
    expect(confirmed?.get("token")).toBe("the-token")
    expect(await (confirmed?.get("file") as Blob).text()).toBe("the bytes")

    await user.click(screen.getByRole("button", { name: "Done" }))
    const dialog = await screen.findByRole("alertdialog")
    await user.click(within(dialog).getByRole("button", { name: "Stay" }))
    expect(screen.getByText("aaaa-bbbb-cccc-dddd")).toBeInTheDocument()

    await user.click(screen.getByRole("button", { name: "Done" }))
    await user.click(within(await screen.findByRole("alertdialog")).getByRole("button", { name: "Close passwords" }))

    await waitFor(() => expect(screen.queryByText("aaaa-bbbb-cccc-dddd")).not.toBeInTheDocument())
    expect(screen.getByText("2 nurses added.")).toBeInTheDocument()
    expect(screen.getByRole("heading", { name: "Import nurses" })).toHaveFocus()
  })

  it("asks before leaving a sheet, and leaves only when told to", async () => {
    const { user, router } = start("/nurses/import", here({
      "POST /api/nurses/import/preview": { body: GOOD },
      "POST /api/nurses/import/confirm": { status: 201, body: SHEET },
      "GET /api/nurses": { body: [] },
      "GET /api/units": { body: [] },
    }))
    await check(user)
    await user.click(await screen.findByRole("button", { name: "Add 2 nurses" }))
    await screen.findByText("aaaa-bbbb-cccc-dddd")

    await user.click(screen.getByRole("link", { name: "Home" }))
    const dialog = await screen.findByRole("alertdialog")
    expect(within(dialog).getByText("Leave without the passwords?")).toBeInTheDocument()
    await user.click(within(dialog).getByRole("button", { name: "Stay" }))
    expect(router.state.location.pathname).toBe("/nurses/import")
    expect(screen.getByText("aaaa-bbbb-cccc-dddd")).toBeInTheDocument()

    await user.click(screen.getByRole("link", { name: "Home" }))
    await user.click(within(await screen.findByRole("alertdialog")).getByRole("button", { name: "Leave" }))
    await waitFor(() => expect(router.state.location.pathname).toBe("/"))
  })

  it("copies the sheet with any cell that looks like a formula made safe", async () => {
    const { user } = start("/nurses/import", here({
      "POST /api/nurses/import/preview": { body: GOOD },
      "POST /api/nurses/import/confirm": { status: 201, body: SHEET },
    }))
    await check(user)
    await user.click(await screen.findByRole("button", { name: "Add 2 nurses" }))
    await screen.findByText("aaaa-bbbb-cccc-dddd")
    const writeText = vi.fn(async () => {})
    Object.defineProperty(navigator, "clipboard", { value: { writeText }, configurable: true })

    await user.click(screen.getByRole("button", { name: "Copy all" }))

    expect(await screen.findByText("Copied.")).toBeInTheDocument()
    expect(writeText).toHaveBeenCalledWith(
      "Hospital ID\tFull name\tUnit\tPassword\nh1\tAmal Saleh\tER\taaaa-bbbb-cccc-dddd\nh2\t'=Badr =1+1\tER\teeee-ffff-gggg-hhhh")
  })

  it("prints the sheet", async () => {
    const print = vi.fn()
    vi.stubGlobal("print", print)
    const { user } = start("/nurses/import", here({
      "POST /api/nurses/import/preview": { body: GOOD },
      "POST /api/nurses/import/confirm": { status: 201, body: SHEET },
    }))
    await check(user)
    await user.click(await screen.findByRole("button", { name: "Add 2 nurses" }))

    await user.click(await screen.findByRole("button", { name: "Print" }))

    expect(print).toHaveBeenCalled()
  })

  it("shows what changed when the file no longer means what was previewed, and saves nothing", async () => {
    const { user } = start("/nurses/import", here({
      "POST /api/nurses/import/preview": { body: GOOD },
      "POST /api/nurses/import/confirm": { status: 409, body: { rows: [ROW, BAD], token: null } },
    }))
    await check(user)

    await user.click(await screen.findByRole("button", { name: "Add 2 nurses" }))

    expect(await screen.findByRole("alert")).toHaveTextContent("Something changed since the last check, so nothing was saved.")
    expect(await screen.findByRole("heading", { name: "1 of 2 lines has a problem" })).toHaveFocus()
    expect(screen.queryByRole("button", { name: /^Add/ })).not.toBeInTheDocument()
  })

  it("lets a changed file that is still good be confirmed with its new token", async () => {
    const tokens: unknown[] = []
    const { user } = start("/nurses/import", here({
      "POST /api/nurses/import/preview": { body: GOOD },
      "POST /api/nurses/import/confirm": ({ body }: { body: unknown }) => {
        tokens.push((body as FormData).get("token"))
        return tokens.length === 1 ? { status: 409, body: { ...GOOD, token: "new-token" } } : { status: 201, body: SHEET }
      },
    }))
    await check(user)
    await user.click(await screen.findByRole("button", { name: "Add 2 nurses" }))
    await screen.findByRole("alert")

    await user.click(screen.getByRole("button", { name: "Add 2 nurses" }))

    await screen.findByText("aaaa-bbbb-cccc-dddd")
    expect(tokens).toEqual(["the-token", "new-token"])
  })

  it("says plainly when it cannot tell whether the nurses were added", async () => {
    const { user } = start("/nurses/import", here({
      "POST /api/nurses/import/preview": { body: GOOD },
      "POST /api/nurses/import/confirm": { status: 502 },
    }))
    await check(user)

    await user.click(await screen.findByRole("button", { name: "Add 2 nurses" }))

    expect(await screen.findByRole("alert")).toHaveTextContent("It is not known whether these nurses were added.")
  })

  it("asks before leaving while the nurses are being added", async () => {
    let finish: (answer: Answer) => void = () => {}
    const { user, calls, router } = start("/nurses/import", here({
      "POST /api/nurses/import/preview": { body: GOOD },
    }))
    await check(user)
    await screen.findByRole("button", { name: "Add 2 nurses" })
    vi.stubGlobal("fetch", vi.fn(() => new Promise((resolve) => {
      finish = (answer) => resolve(new Response(JSON.stringify(answer.body), { status: answer.status }))
    })))

    await user.click(screen.getByRole("button", { name: "Add 2 nurses" }))
    expect(await screen.findByText(/can take a few minutes/)).toBeInTheDocument()
    await user.click(screen.getByRole("link", { name: "Home" }))

    expect(await screen.findByRole("alertdialog")).toBeInTheDocument()
    expect(router.state.location.pathname).toBe("/nurses/import")
    expect(calls.length).toBeGreaterThan(0)
    await user.click(within(screen.getByRole("alertdialog")).getByRole("button", { name: "Stay" }))
    await act(async () => finish({ status: 201, body: SHEET }))
    expect(await screen.findByText("aaaa-bbbb-cccc-dddd")).toBeInTheDocument()
  })

  it("links the CNO to the import and the staff list from the nurses page, and not a manager", async () => {
    start("/nurses", here({ "GET /api/nurses": { body: [] }, "GET /api/units": { body: [] } }))

    expect(await screen.findByRole("link", { name: "Import from a file" })).toHaveAttribute("href", "/nurses/import")
    expect(screen.getByRole("link", { name: "Export staff list" })).toHaveAttribute("href", "/api/nurses/export")
  })

  it("has neither for a unit manager", async () => {
    start("/nurses", {
      ...session({ ...ME, username: "mona", role: "unit_manager" }),
      "GET /api/nurses": { body: [] },
      "GET /api/units": { body: [] },
    })

    await screen.findByRole("heading", { name: "Nurses" })
    expect(screen.queryByRole("link", { name: "Import from a file" })).not.toBeInTheDocument()
    expect(screen.queryByRole("link", { name: "Export staff list" })).not.toBeInTheDocument()
  })
})

const HEADCOUNT = { weekday_min: 7, weekday_max: 9, weekend_min: 8, weekend_max: 9, also_counts: [] as string[] }
const UNIT_RULES = {
  shifts: ["D", "N"],
  headcounts: [{ shift: "D", ...HEADCOUNT }, { shift: "N", ...HEADCOUNT }],
  headcount_enabled: true,
  require_team_leader: true,
  require_both_genders: true,
  score_target: 0.7,
  score_target_weekend: 0.8,
  score_balance: true,
  score_balance_mode: "band",
  score_band_hi: 0.78,
  score_band_hi_weekend: 0.88,
  night_shift: "N",
  day_shift: "D",
  night_rest_days: 2,
  night_rest_hard: true,
  fair_shifts: ["D", "N"],
  fair_tolerance: 0.5,
  fair_weekends: true,
  carry_fairness: true,
  carry_cap: 2,
  max_consecutive_shifts: 3,
  double_cycle_rest: 2,
  max_weekends: 3,
  no_mixed_blocks: true,
  max_switches: 2,
  switches_hard: false,
}
const UNIT_RULES_STATE = {
  rules: UNIT_RULES,
  needs_review: true,
  request_cap: 3,
  default_time_limit: 60,
  time_limit_cap: 300,
  active_shifts: [
    { code: "D", display_name: "Day", hours: 12 },
    { code: "N", display_name: "Night", hours: 12 },
    { code: "A", display_name: "Morning", hours: 8 },
  ],
}
const ER_UNIT = { id: "er", name: "ER", archived: false, manager: null, rules_need_review: true }
const ICU = { id: "icu", name: "ICU", archived: false, manager: null, rules_need_review: false }
const CLOSED = { id: "old", name: "Old", archived: true, manager: null, rules_need_review: false }
const ME_MANAGER = { ...ME, username: "mona", full_name: "Mona Saleh", role: "unit_manager" }
const ME_CNO = { ...ME, username: "chief", full_name: "Fatimah", role: "cno" }
const ME_DEPUTY = { ...ME, username: "deputy", full_name: "Deputy", role: "deputy_cno" }
const apiRefusal = (loc: (string | number)[], msg: string) => ({ status: 422, body: { detail: [{ type: "value_error", loc: ["body", "body", ...loc], msg: `Value error, ${msg}` }] } })

describe("the unit rules page", () => {
  const FLAG = "Defaults, review before the first solve"
  const saves = { "PUT /api/units/er/rules": ({ body }: { body: unknown }) => ({ body: { ...UNIT_RULES_STATE, ...(body as object), needs_review: false } }) }
  const asManager = (state: unknown = UNIT_RULES_STATE, extra = {}) => ({
    ...session(ME_MANAGER),
    "GET /api/units": { body: [ER_UNIT] },
    "GET /api/units/er/rules": { body: state },
    ...extra,
  })
  const put = (calls: { method: string; body: unknown }[]) => calls.find((call) => call.method === "PUT")?.body as { rules: typeof UNIT_RULES; request_cap: number; default_time_limit: number }

  it("shows every field of the solver's block with its explanation, and flags the defaults", async () => {
    start("/unit-rules", asManager())

    expect(await screen.findByText(FLAG)).toBeInTheDocument()
    expect(document.title).toBe("Unit rules · Nurse roster")
    expect(screen.getByRole("heading", { level: 1, name: "Unit rules of ER" })).toBeInTheDocument()
    expect(screen.getByRole("checkbox", { name: "D, Day, 12 hours" })).toBeChecked()
    expect(screen.getByRole("checkbox", { name: "A, Morning, 8 hours" })).not.toBeChecked()
    expect(screen.getByLabelText("Night shift")).toHaveValue("N")
    expect(screen.getByLabelText("Day shift")).toHaveValue("D")
    const day = within(screen.getByRole("region", { name: "D, Day" }))
    expect(day.getByLabelText("Weekday, at least")).toHaveValue(7)
    expect(day.getByLabelText("Weekend day, at most")).toHaveValue(9)
    expect(day.getByRole("checkbox", { name: "N" })).not.toBeChecked()
    for (const [name, value] of [["Score target on a weekday", 0.7], ["Score target on a weekend day", 0.8], ["Score ceiling on a weekday", 0.78],
      ["Score ceiling on a weekend day", 0.88], ["Days off after a night shift", 2], ["Longest run of shifts", 3], ["Days off after two runs", 2],
      ["Free difference from a fair share (shifts)", 0.5], ["Most a month's share can move (shifts)", 2], ["Weekend days a month", 3],
      ["Switches between day and night a month", 2], ["Requests per nurse per month", 3], ["Default time limit (seconds)", 60]] as const) {
      expect(screen.getByLabelText(name)).toHaveValue(value)
      expect(screen.getByLabelText(name)).toHaveAccessibleDescription(/\S/)
    }
    for (const name of ["Hold every shift to its headcount", "A team leader on every shift", "Both genders on every shift", "Keep the strength of shifts balanced",
      "Never break the night rest", "Keep runs unmixed", "Spread weekend days fairly", "Carry fairness between months"]) {
      expect(screen.getByRole("checkbox", { name })).toBeChecked()
      expect(screen.getByRole("checkbox", { name })).toHaveAccessibleDescription(/\S/)
    }
    expect(screen.getByRole("checkbox", { name: "Never go over the switch limit" })).not.toBeChecked()
    expect(screen.getByLabelText("Way of balancing")).toHaveValue("band")
    expect(screen.getByLabelText("Default time limit (seconds)")).toHaveAccessibleDescription(/cap is 300 seconds/)
  })

  it("saving the defaults untouched is the review and sends the solver's block", async () => {
    const { user, calls } = start("/unit-rules", asManager(UNIT_RULES_STATE, saves))

    await screen.findByText(FLAG)
    await user.click(screen.getByRole("button", { name: "Save" }))

    expect(await screen.findByText("Saved.")).toHaveAttribute("role", "status")
    expect(put(calls)).toEqual({ rules: UNIT_RULES, request_cap: 3, default_time_limit: 60 })
    expect(screen.queryByText(FLAG)).not.toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Save" })).toHaveAttribute("aria-disabled", "true")
  })

  it("a refusal from the API appears beside its field, with focus on it", async () => {
    const { user } = start("/unit-rules", asManager(UNIT_RULES_STATE, {
      "PUT /api/units/er/rules": apiRefusal(["rules", "night_shift"], "A is not one of this unit's shifts."),
    }))

    await user.selectOptions(await screen.findByLabelText("Night shift"), "A")
    await user.click(screen.getByRole("button", { name: "Save" }))

    expect(await screen.findByText("A is not one of this unit's shifts.")).toBeInTheDocument()
    expect(screen.getByLabelText("Night shift")).toHaveFocus()
    expect(screen.getByLabelText("Night shift")).toHaveAccessibleDescription(/not one of this unit's shifts/)
    expect(screen.getByRole("alert")).toHaveTextContent("Some values were refused")
  })

  it("a refusal on the unit's shifts appears on the list, with its position dropped, and takes focus", async () => {
    const { user } = start("/unit-rules", asManager(UNIT_RULES_STATE, {
      "PUT /api/units/er/rules": apiRefusal(["rules", "shifts", 1], "Amal Saleh (h1) could work none of these shifts. Change their allowed shifts first."),
    }))

    await screen.findByText(FLAG)
    await user.click(screen.getByRole("button", { name: "Save" }))

    const message = await screen.findByText(/could work none of these shifts/)
    expect(message).toBeInTheDocument()
    expect(screen.getByRole("group", { name: "Shifts this unit works" })).toHaveFocus()
  })

  it("a refusal on a shift counting towards another appears on that shift's list", async () => {
    const { user } = start("/unit-rules", asManager(UNIT_RULES_STATE, {
      "PUT /api/units/er/rules": apiRefusal(["rules", "headcounts", 0, "also_counts", 0], "N cannot count."),
    }))

    await screen.findByText(FLAG)
    await user.click(screen.getByRole("button", { name: "Save" }))
    await screen.findByText("N cannot count.")

    const day = within(screen.getByRole("region", { name: "D, Day" }))
    expect(within(day.getByRole("group", { name: "Shifts that also count towards it" })).getByText("N cannot count.")).toBeInTheDocument()
  })

  it("says what is wrong before asking the API", async () => {
    const { user, calls } = start("/unit-rules", asManager())

    const target = await screen.findByLabelText("Score target on a weekday")
    await user.clear(target)
    await user.type(target, "1.5")
    const low = within(screen.getByRole("region", { name: "D, Day" })).getByLabelText("Weekday, at most")
    await user.clear(low)
    await user.type(low, "1")
    await user.selectOptions(screen.getByLabelText("Day shift"), "N")
    const limit = screen.getByLabelText("Default time limit (seconds)")
    await user.clear(limit)
    await user.type(limit, "301")
    await user.click(screen.getByRole("button", { name: "Save" }))

    expect(await screen.findByText("Between 0 and 1.")).toBeInTheDocument()
    expect(screen.getByText("Cannot be below the weekday minimum.")).toBeInTheDocument()
    expect(screen.getByText("Cannot be the night shift too.")).toBeInTheDocument()
    expect(screen.getByText("Between 1 and 300.")).toBeInTheDocument()
    expect(calls.some((call) => call.method === "PUT")).toBe(false)
  })

  it("a ceiling below its target is refused only when the ceilings apply", async () => {
    const { user, calls } = start("/unit-rules", asManager(UNIT_RULES_STATE, saves))

    const ceiling = await screen.findByLabelText("Score ceiling on a weekday")
    await user.clear(ceiling)
    await user.type(ceiling, "0.5")
    await user.click(screen.getByRole("button", { name: "Save" }))
    expect(await screen.findByText("Cannot be below the weekday score target.")).toBeInTheDocument()
    expect(calls.some((call) => call.method === "PUT")).toBe(false)

    await user.selectOptions(screen.getByLabelText("Way of balancing"), "spread")
    await user.click(screen.getByRole("button", { name: "Save" }))

    await screen.findByText("Saved.")
    expect(put(calls).rules.score_balance_mode).toBe("spread")
  })

  it("a shift the unit stops working leaves its headcount, fair shares and what counts towards others", async () => {
    const state = { ...UNIT_RULES_STATE, rules: { ...UNIT_RULES, headcounts: [{ shift: "D", ...HEADCOUNT, also_counts: ["N"] }, { shift: "N", ...HEADCOUNT }] } }
    const { user, calls } = start("/unit-rules", asManager(state, saves))

    await user.click(await screen.findByRole("checkbox", { name: "N, Night, 12 hours" }))
    expect(screen.queryByRole("region", { name: "N, Night" })).not.toBeInTheDocument()
    await user.selectOptions(screen.getByLabelText("Night shift"), "A")
    await user.click(screen.getByRole("checkbox", { name: "A, Morning, 8 hours" }))
    await user.click(screen.getByRole("button", { name: "Save" }))

    await screen.findByText("Saved.")
    const { rules } = put(calls)
    expect(rules.shifts).toEqual(["D", "A"])
    expect(rules.headcounts).toEqual([{ shift: "D", ...HEADCOUNT }])
    expect(rules.fair_shifts).toEqual(["D"])
    expect(rules.night_shift).toBe("A")
  })

  it("a headcount is added and removed with focus staying in its shift, and a shift without one cannot be spread fairly", async () => {
    const { user, calls } = start("/unit-rules", asManager(UNIT_RULES_STATE, saves))

    await user.click(await screen.findByRole("checkbox", { name: "A, Morning, 8 hours" }))
    const morning = within(screen.getByRole("region", { name: "A, Morning" }))
    const fair = within(screen.getByRole("group", { name: "Shifts to spread fairly" }))
    expect(fair.queryByRole("checkbox", { name: "A" })).not.toBeInTheDocument()
    await user.click(morning.getByRole("button", { name: "Add a headcount for A" }))
    await waitFor(() => expect(morning.getByLabelText("Weekday, at least")).toHaveFocus())
    await user.click(fair.getByRole("checkbox", { name: "A" }))
    await user.click(morning.getByRole("button", { name: "Remove the headcount of A" }))
    await waitFor(() => expect(morning.getByRole("button", { name: "Add a headcount for A" })).toHaveFocus())
    await user.click(screen.getByRole("button", { name: "Save" }))

    await screen.findByText("Saved.")
    expect(put(calls).rules.headcounts.map((row) => row.shift)).toEqual(["D", "N"])
    expect(put(calls).rules.fair_shifts).toEqual(["D", "N"])
  })

  it("a unit seeded with a gap opens from blank choices and cannot be saved until they are made", async () => {
    const gap = { ...UNIT_RULES, shifts: [], headcounts: [], fair_shifts: [], night_shift: "", day_shift: "" }
    const { user, calls } = start("/unit-rules", asManager({ ...UNIT_RULES_STATE, rules: gap }))

    expect(await screen.findByLabelText("Night shift")).toHaveValue("")
    expect(screen.getByLabelText("Day shift")).toHaveValue("")
    expect(screen.getByText("Choose the unit's shifts first.")).toBeInTheDocument()
    await user.click(screen.getByRole("button", { name: "Save" }))

    expect(await screen.findByText("Choose at least one shift.")).toBeInTheDocument()
    expect(screen.getByText("Choose the night shift.")).toBeInTheDocument()
    expect(screen.getByText("Choose the day shift.")).toBeInTheDocument()
    expect(calls.some((call) => call.method === "PUT")).toBe(false)
  })

  it("a failure that is no refusal says to try again", async () => {
    const { user } = start("/unit-rules", asManager(UNIT_RULES_STATE, { "PUT /api/units/er/rules": { status: 500 } }))

    await screen.findByText(FLAG)
    await user.click(screen.getByRole("button", { name: "Save" }))

    expect(await screen.findByRole("alert")).toHaveTextContent("could not be saved")
  })

  it("a manager with no unit is told so", async () => {
    start("/unit-rules", { ...session(ME_MANAGER), "GET /api/units": { body: [] } })

    expect(await screen.findByText(/No unit is assigned to you yet/)).toBeInTheDocument()
  })

  it.each([["the CNO", ME_CNO], ["the Deputy CNO", ME_DEPUTY]])("%s reads with no input, and chooses the unit in the address", async (_name, me) => {
    const { user, router } = start("/unit-rules", {
      ...session(me),
      "GET /api/units": { body: [CLOSED, ER_UNIT, ICU] },
      "GET /api/units/er/rules": { body: UNIT_RULES_STATE },
      "GET /api/units/icu/rules": { body: { ...UNIT_RULES_STATE, needs_review: false, rules: { ...UNIT_RULES, score_target: 0.42 } } },
    })

    const longest = await screen.findByText("Longest run of shifts")
    expect(longest).toBeInTheDocument()
    expect(screen.getByLabelText("Unit")).toHaveValue("er")
    expect(within(screen.getByLabelText("Unit")).getByRole("option", { name: "Old (archived)" })).toBeInTheDocument()
    expect(screen.getByText("Defaults, review before the first solve")).toBeInTheDocument()
    expect(screen.queryByText(/Saving this page/)).not.toBeInTheDocument()
    expect(screen.queryByRole("spinbutton")).not.toBeInTheDocument()
    expect(screen.queryByRole("checkbox")).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Save" })).not.toBeInTheDocument()
    expect(screen.getByText(/Only the unit's manager can change these/)).toBeInTheDocument()

    await user.selectOptions(screen.getByLabelText("Unit"), "icu")

    expect(await screen.findByText("0.42")).toBeInTheDocument()
    expect(router.state.location.search).toEqual({ unit: "icu" })
  })

  it("a read-only unit with a gap says what is not chosen", async () => {
    const gap = { ...UNIT_RULES, shifts: [], headcounts: [], fair_shifts: [], night_shift: "", day_shift: "" }
    start("/unit-rules", { ...session(ME_DEPUTY), "GET /api/units": { body: [ER_UNIT] }, "GET /api/units/er/rules": { body: { ...UNIT_RULES_STATE, rules: gap } } })

    expect(await screen.findByText("None chosen")).toBeInTheDocument()
    expect(screen.getAllByText("Not chosen")).toHaveLength(2)
    expect(screen.getByText("No shift has a headcount.")).toBeInTheDocument()
  })

  it("a staff nurse and the System Admin have no way in", async () => {
    const { router } = start("/unit-rules", { ...session(NURSE), "GET /api/nurses/my-unit": { body: { id: "er", name: "ER" } } })

    await screen.findByText("No roster yet.")
    expect(router.state.location.pathname).toBe("/")
  })

  it("the manager's home links to the form while the defaults wait", async () => {
    start("/", { ...session(ME_MANAGER), "GET /api/units": { body: [ER_UNIT] } })

    expect(await screen.findByRole("link", { name: "Review them before its first solve" })).toHaveAttribute("href", "/unit-rules")
  })
})

describe("the rostering attributes page", () => {
  const AMAL = {
    id: "n1", hospital_id: "h1", full_name: "Amal Saleh", is_active: true, gender: "F", joins_from: null, leaves_from: null,
    team_leader: true, score: 0.9, ramadan_reduced: false, breastfeeding: true, ytd_overtime: 12, hours_balance: -3, night_balance: 1.5, friday_balance: -0.5,
    allowed_shifts: ["D"], allowed_shifts_to_check: false,
  }
  const BADR = {
    ...AMAL, id: "n2", hospital_id: "h2", full_name: "Badr Omar", gender: "M", joins_from: "2030-01", team_leader: false, score: 0.8, breastfeeding: false,
    ytd_overtime: 0, hours_balance: 0, night_balance: 0, friday_balance: 0, allowed_shifts: null, allowed_shifts_to_check: true,
  }
  const pageOf = (me: unknown, nurses: unknown[] = [AMAL, BADR], extra = {}) => ({
    ...session(me),
    "GET /api/units": { body: [ER_UNIT] },
    "GET /api/units/er/nurses": { body: nurses },
    "GET /api/units/er/rules": { body: UNIT_RULES_STATE },
    ...extra,
  })
  const put = (calls: { method: string; url: string; body: unknown }[]) => calls.find((call) => call.method === "PUT")!

  it("lists what the solver needs to know of each nurse", async () => {
    start("/rostering-attributes", pageOf(ME_MANAGER))

    const row = within((await screen.findByRole("cell", { name: "Amal Saleh" })).closest("tr")!)
    expect(document.title).toBe("Rostering attributes · Nurse roster")
    expect(row.getAllByRole("cell").map((cell) => cell.textContent)).toEqual(
      ["Amal Saleh", "Set attributes", "h1", "In the unit", "Female", "Yes", "0.9", "D", "No", "Yes", "12", "-3", "1.5", "-0.5"])
    const badr = within(screen.getByRole("cell", { name: "Badr Omar" }).closest("tr")!)
    expect(badr.getByText("Joins from January 2030")).toBeInTheDocument()
    expect(badr.getByText("Any")).toBeInTheDocument()
    expect(badr.getByText("To check")).toBeInTheDocument()
    expect(screen.getByText(/Badr Omar came with allowed shifts this unit does not work/)).toBeInTheDocument()
  })

  it("saves everything, with focus returning to the row's button", async () => {
    const { user, calls } = start("/rostering-attributes", pageOf(ME_MANAGER, [AMAL], { "PUT /api/units/er/nurses/n1/attributes": { body: AMAL } }))

    const button = await screen.findByRole("button", { name: "Set attributes of Amal Saleh" })
    await user.click(button)
    expect(screen.getByRole("checkbox", { name: "Team leader" })).toHaveFocus()
    expect(screen.getByLabelText("Score")).toHaveValue(0.9)
    await user.click(screen.getByRole("checkbox", { name: "Team leader" }))
    await user.clear(screen.getByLabelText("Score"))
    await user.type(screen.getByLabelText("Score"), "0.61")
    await user.click(screen.getByRole("checkbox", { name: "N" }))
    await user.click(screen.getByRole("checkbox", { name: "Ramadan-reduced" }))
    await user.clear(screen.getByLabelText("Overtime this year (hours)"))
    await user.type(screen.getByLabelText("Overtime this year (hours)"), "40")
    await user.clear(screen.getByLabelText("Weekend fairness balance (shifts)"))
    await user.type(screen.getByLabelText("Weekend fairness balance (shifts)"), "-2.5")
    await user.click(screen.getByRole("button", { name: "Save" }))

    expect(await screen.findByText("The rostering attributes of Amal Saleh are saved.")).toHaveAttribute("role", "status")
    expect(put(calls).url).toBe("/api/units/er/nurses/n1/attributes")
    expect(put(calls).body).toEqual({
      team_leader: false, score: 0.61, ramadan_reduced: true, breastfeeding: true, allowed_shifts: ["D", "N"], ytd_overtime: 40, hours_balance: -3, night_balance: 1.5, friday_balance: -2.5,
    })
    await waitFor(() => expect(screen.getByRole("button", { name: "Set attributes of Amal Saleh" })).toHaveFocus())
  })

  it("offers only the unit's shifts, and ticking none means any", async () => {
    const { user, calls } = start("/rostering-attributes", pageOf(ME_MANAGER, [AMAL], { "PUT /api/units/er/nurses/n1/attributes": { body: AMAL } }))

    await user.click(await screen.findByRole("button", { name: "Set attributes of Amal Saleh" }))
    const shifts = within(screen.getByRole("group", { name: "Allowed shifts" }))
    expect(shifts.getAllByRole("checkbox").map((box) => box.closest("label")!.textContent)).toEqual(["D", "N"])
    expect(screen.getByRole("group", { name: "Allowed shifts" })).toHaveAccessibleDescription(/Tick none for any shift/)
    await user.click(shifts.getByRole("checkbox", { name: "D" }))
    await user.click(screen.getByRole("button", { name: "Save" }))

    await screen.findByText("The rostering attributes of Amal Saleh are saved.")
    expect((put(calls).body as { allowed_shifts: unknown }).allowed_shifts).toBeNull()
  })

  it("says what is wrong before asking the API, and a refusal appears beside its field", async () => {
    const { user, calls } = start("/rostering-attributes", pageOf(ME_MANAGER, [AMAL], {
      "PUT /api/units/er/nurses/n1/attributes": apiRefusal(["allowed_shifts", 0], "A is not one of this unit's shifts."),
    }))

    await user.click(await screen.findByRole("button", { name: "Set attributes of Amal Saleh" }))
    await user.clear(screen.getByLabelText("Score"))
    await user.type(screen.getByLabelText("Score"), "2")
    await user.clear(screen.getByLabelText("Hours balance (hours)"))
    await user.type(screen.getByLabelText("Hours balance (hours)"), "1.5")
    await user.click(screen.getByRole("button", { name: "Save" }))
    expect(await screen.findByText("Between 0 and 1.")).toBeInTheDocument()
    expect(screen.getByText("Enter a whole number of hours.")).toBeInTheDocument()
    expect(calls.some((call) => call.method === "PUT")).toBe(false)

    await user.clear(screen.getByLabelText("Score"))
    await user.type(screen.getByLabelText("Score"), "0.5")
    await user.clear(screen.getByLabelText("Hours balance (hours)"))
    await user.type(screen.getByLabelText("Hours balance (hours)"), "1")
    await user.click(screen.getByRole("button", { name: "Save" }))

    expect(await screen.findByText("A is not one of this unit's shifts.")).toBeInTheDocument()
    expect(screen.getByRole("group", { name: "Allowed shifts" })).toHaveFocus()
  })

  it("a nurse due to join shows only their allowed shifts", async () => {
    const { user, calls } = start("/rostering-attributes", pageOf(ME_MANAGER, [BADR], { "PUT /api/units/er/nurses/n2/allowed-shifts": { body: BADR } }))

    await user.click(await screen.findByRole("button", { name: "Set allowed shifts of Badr Omar" }))
    expect(screen.getByText(/joins from January 2030/)).toBeInTheDocument()
    expect(screen.queryByLabelText("Score")).not.toBeInTheDocument()
    expect(screen.getByRole("group", { name: "Allowed shifts" })).toHaveFocus()
    await user.click(screen.getByRole("checkbox", { name: "N" }))
    await user.click(screen.getByRole("button", { name: "Save" }))

    expect(await screen.findByText("The allowed shifts of Badr Omar are saved.")).toBeInTheDocument()
    expect(put(calls)).toMatchObject({ url: "/api/units/er/nurses/n2/allowed-shifts", body: { allowed_shifts: ["N"] } })
  })

  it("a manager setting their own is told who can see it", async () => {
    const { user } = start("/rostering-attributes", pageOf(ME_MANAGER, [{ ...AMAL, hospital_id: "mona", full_name: "Mona Saleh" }]))

    await user.click(await screen.findByRole("button", { name: "Set attributes of Mona Saleh" }))

    expect(screen.getByText(/These are your own/)).toBeInTheDocument()
  })

  it("cancelling returns focus to the row", async () => {
    const { user } = start("/rostering-attributes", pageOf(ME_MANAGER, [AMAL]))

    await user.click(await screen.findByRole("button", { name: "Set attributes of Amal Saleh" }))
    await user.click(screen.getByRole("button", { name: "Cancel" }))

    expect(screen.getByRole("button", { name: "Set attributes of Amal Saleh" })).toHaveFocus()
    expect(screen.queryByLabelText("Score")).not.toBeInTheDocument()
  })

  it("a unit with no shifts says where to choose them", async () => {
    start("/rostering-attributes", pageOf(ME_MANAGER, [AMAL], {
      "GET /api/units/er/rules": { body: { ...UNIT_RULES_STATE, rules: { ...UNIT_RULES, shifts: [] } } },
    }))

    expect(await screen.findByRole("link", { name: "Choose them under Unit rules" })).toHaveAttribute("href", "/unit-rules")
  })

  it("a unit with no nurses says who adds them", async () => {
    start("/rostering-attributes", pageOf(ME_MANAGER, []))

    expect(await screen.findByText("ER has no nurses yet. The CNO adds them.")).toBeInTheDocument()
  })

  it.each([["the CNO", ME_CNO], ["the Deputy CNO", ME_DEPUTY]])("%s reads with no way to change anything, by keyboard too", async (_name, me) => {
    start("/rostering-attributes", pageOf(me))

    await screen.findByRole("cell", { name: "Amal Saleh" })
    expect(screen.queryByRole("button", { name: /Set / })).not.toBeInTheDocument()
    expect(screen.getByRole("region", { name: "Rostering attributes of ER" })).toHaveAttribute("tabindex", "0")
    expect(screen.getByText(/Only the unit's manager can change these/)).toBeInTheDocument()
    expect(screen.queryByText(/came with allowed shifts/)).not.toBeInTheDocument()
  })

  it("a staff nurse has no way in", async () => {
    const { router } = start("/rostering-attributes", { ...session(NURSE), "GET /api/nurses/my-unit": { body: { id: "er", name: "ER" } } })

    await screen.findByText("No roster yet.")
    expect(router.state.location.pathname).toBe("/")
  })
})

describe("the leave pages", () => {
  const AMAL = { id: "n1", hospital_id: "h1", full_name: "Amal Saleh" }
  const BADR = { id: "n2", hospital_id: "h2", full_name: "Badr Omar" }
  const SICK = { id: "sick", name: "Sick", active: true }
  const OLD = { id: "old", name: "Study", active: false }
  const ANNUAL = { id: "annual", name: "Annual", active: true }
  const RUN = { leave_ids: ["l1", "l2"], nurse: AMAL, leave_type: SICK, first: "2026-11-10", last: "2026-11-11", days: 2, outside_dates: false }
  const BADR_RUN = { leave_ids: ["l3"], nurse: BADR, leave_type: OLD, first: "2026-11-20", last: "2026-11-20", days: 1, outside_dates: true }
  const MONTH = { month: "2026-11", nurses: [AMAL, BADR], runs: [RUN, BADR_RUN] }
  const pageOf = (extra = {}) => ({
    ...session(ME_MANAGER),
    "GET /api/units": { body: [ER_UNIT] },
    "GET /api/units/er/leave": { body: MONTH },
    "GET /api/hospital/leave-types": { body: [ANNUAL, SICK, OLD] },
    ...extra,
  })
  const refused = (field: string, msg: string) => ({ status: 422, body: { detail: [{ loc: ["body", "body", field], msg }] } })

  it("lists the unit's month with what a manager can do to each leave", async () => {
    start("/leave", pageOf())

    const row = within((await screen.findByRole("link", { name: "Amal Saleh" })).closest("tr")!)
    expect(document.title).toBe("Leave · Nurse roster")
    expect(screen.getByRole("heading", { name: "November 2026" })).toBeInTheDocument()
    expect(row.getAllByRole("cell").map((cell) => cell.textContent).slice(0, 4)).toEqual(["Amal Saleh", "10 to 11 Nov 2026", "2", "Sick"])
    expect(row.getByRole("button", { name: "Change leave of Amal Saleh, 10 to 11 Nov 2026" })).toBeInTheDocument()
    expect(row.getByRole("button", { name: "Remove leave of Amal Saleh, 10 to 11 Nov 2026" })).toBeInTheDocument()
    expect(screen.getByText("Outside their dates")).toBeInTheDocument()
    expect(screen.getByText(/left the days marked Outside their dates/)).toBeInTheDocument()
  })

  it("moves by month in the address, keeping the nurse", async () => {
    const { router, user, calls } = start("/leave?month=2026-11&nurse=n1", pageOf())

    await user.click(await screen.findByRole("link", { name: "Next month" }))

    await waitFor(() => expect(router.state.location.search).toEqual({ month: "2026-12", nurse: "n1" }))
    expect(calls.some((call) => call.url.includes("/api/units/er/leave?month=2026-12"))).toBe(true)
  })

  it("keeps focus on the link while the next month loads", async () => {
    const answer = ({ url }: { url: string }) => ({ body: { ...MONTH, month: new URL(url, "http://here").searchParams.get("month") } })
    const { user } = start("/leave?month=2026-11", pageOf({ "GET /api/units/er/leave": answer }))

    const next = await screen.findByRole("link", { name: "Next month" })
    await user.click(next)

    await waitFor(() => expect(next).toHaveAttribute("href", "/leave?month=2027-01"))
    expect(next).toHaveFocus()
  })

  it("says so when the nurse chosen is not in the unit that month, and keeps them for the next", async () => {
    start("/leave?month=2026-11&nurse=gone", pageOf())

    expect(await screen.findByText("The nurse you chose is not in ER in November 2026, so this shows everyone.")).toBeInTheDocument()
    expect(screen.getByRole("link", { name: "Next month" })).toHaveAttribute("href", "/leave?month=2026-12&nurse=gone")
    expect(screen.getByRole("link", { name: "Amal Saleh" })).toBeInTheDocument()
  })

  it("shows one nurse's month, with the count", async () => {
    const { router, user } = start("/leave?month=2026-11", pageOf())

    await user.selectOptions(await screen.findByLabelText("Show"), "n1")

    expect(await screen.findByText("Amal Saleh has 2 days of leave in November 2026.")).toBeInTheDocument()
    expect(screen.queryByText("Badr Omar", { selector: "a" })).not.toBeInTheDocument()
    expect(screen.queryByRole("columnheader", { name: "Nurse" })).not.toBeInTheDocument()
    expect(router.state.location.search).toEqual({ month: "2026-11", nurse: "n1" })
  })

  it("says when a month has none", async () => {
    start("/leave", pageOf({ "GET /api/units/er/leave": { body: { ...MONTH, runs: [] } } }))
    expect(await screen.findByText("No leave is recorded in November 2026.")).toBeInTheDocument()
  })

  it("says when the unit has nobody that month", async () => {
    start("/leave", pageOf({ "GET /api/units/er/leave": { body: { month: "2026-11", nurses: [], runs: [] } } }))
    expect(await screen.findByText("ER has no nurses in November 2026.")).toBeInTheDocument()
  })

  it("records leave, offering only active types, then returns focus", async () => {
    const { user, calls } = start("/leave", pageOf({ "POST /api/units/er/leave": { status: 201, body: RUN } }))

    await user.click(await screen.findByRole("button", { name: "Record leave" }))
    const types = within(await screen.findByLabelText("Leave type")).getAllByRole("option").map((option) => option.textContent)
    expect(types).toEqual(["Choose a type", "Annual", "Sick"])
    expect(screen.getByLabelText("Nurse")).toHaveFocus()

    await user.selectOptions(screen.getByLabelText("Nurse"), "n1")
    await user.selectOptions(screen.getByLabelText("Leave type"), "sick")
    await user.type(screen.getByLabelText("First day"), "2026-11-10")
    await user.click(screen.getByRole("button", { name: "Save" }))

    expect(await screen.findByText("The leave of Amal Saleh is saved: 10 Nov 2026.")).toBeInTheDocument()
    expect(calls.find((call) => call.method === "POST")!.body).toEqual({ nurse_id: "n1", leave_type_id: "sick", first: "2026-11-10", last: "2026-11-10" })
    expect(screen.getByRole("button", { name: "Record leave" })).toHaveFocus()
  })

  it("goes to the month just saved when it is another", async () => {
    const { user, router } = start("/leave?month=2026-11", pageOf({ "POST /api/units/er/leave": { status: 201, body: RUN } }))

    await user.click(await screen.findByRole("button", { name: "Record leave" }))
    await user.selectOptions(await screen.findByLabelText("Nurse"), "n1")
    await user.selectOptions(screen.getByLabelText("Leave type"), "sick")
    await user.type(screen.getByLabelText("First day"), "2027-01-10")
    await user.click(screen.getByRole("button", { name: "Save" }))

    await waitFor(() => expect(router.state.location.search).toMatchObject({ month: "2027-01" }))
  })

  it("asks for what is missing on the client", async () => {
    const { user, calls } = start("/leave", pageOf())

    await user.click(await screen.findByRole("button", { name: "Record leave" }))
    await user.click(await screen.findByRole("button", { name: "Save" }))

    expect(await screen.findByText("Choose a nurse.")).toBeInTheDocument()
    expect(screen.getByText("Enter the first day.")).toBeInTheDocument()
    expect(calls.some((call) => call.method === "POST")).toBe(false)
  })

  it("shows a refusal beside its field with focus on it", async () => {
    const { user } = start("/leave", pageOf({ "POST /api/units/er/leave": refused("first", "Amal Saleh is already on leave on 10 November 2026. Change that leave instead.") }))

    await user.click(await screen.findByRole("button", { name: "Record leave" }))
    await user.selectOptions(await screen.findByLabelText("Nurse"), "n1")
    await user.selectOptions(screen.getByLabelText("Leave type"), "sick")
    await user.type(screen.getByLabelText("First day"), "2026-11-10")
    await user.click(screen.getByRole("button", { name: "Save" }))

    expect(await screen.findByText(/already on leave on 10 November 2026/)).toBeInTheDocument()
    expect(screen.getByLabelText("First day")).toHaveFocus()
    expect(screen.getByLabelText("First day")).toHaveAttribute("aria-invalid", "true")
  })

  it("changes leave, naming the ids it replaces, with focus on the button that stays", async () => {
    const { user, calls } = start("/leave", pageOf({ "POST /api/units/er/leave/change": { body: RUN } }))

    await user.click(await screen.findByRole("button", { name: "Change leave of Amal Saleh, 10 to 11 Nov 2026" }))
    expect(await screen.findByRole("heading", { name: "Change leave of Amal Saleh" })).toBeInTheDocument()
    expect(screen.queryByLabelText("Nurse")).not.toBeInTheDocument()
    expect(screen.getByLabelText("First day")).toHaveValue("2026-11-10")
    expect(screen.getByLabelText("Last day")).toHaveValue("2026-11-11")
    await waitFor(() => expect(screen.getByLabelText("Leave type")).toHaveValue("sick"))

    await user.selectOptions(screen.getByLabelText("Leave type"), "annual")
    await user.click(screen.getByRole("button", { name: "Save" }))

    await screen.findByText("The leave of Amal Saleh is saved: 10 to 11 Nov 2026.")
    expect(calls.find((call) => call.url.endsWith("/change"))!.body).toEqual({ leave_ids: ["l1", "l2"], leave_type_id: "annual", first: "2026-11-10", last: "2026-11-11" })
    expect(screen.getByRole("button", { name: "Record leave" })).toHaveFocus()
  })

  it("lets leave of a retired type keep it and offers no other retired type", async () => {
    const { user } = start("/leave", pageOf())

    await user.click(await screen.findByRole("button", { name: "Change leave of Badr Omar, 20 Nov 2026" }))

    await waitFor(() => expect(screen.getByLabelText("Leave type")).toHaveValue("old"))
    expect(within(screen.getByLabelText("Leave type")).getByRole("option", { name: "Study (retired)" })).toBeInTheDocument()
  })

  it("says so when the leave has changed since the page opened", async () => {
    const stale = "This leave has changed since the page was opened. Reload the page to see it as it is."
    const { user } = start("/leave", pageOf({ "POST /api/units/er/leave/change": { status: 409, body: { detail: stale } } }))

    await user.click(await screen.findByRole("button", { name: "Change leave of Amal Saleh, 10 to 11 Nov 2026" }))
    await user.click(await screen.findByRole("button", { name: "Save" }))

    expect((await screen.findByRole("alert")).textContent).toBe(stale)
  })

  it("asks before removing, then keeps focus on the page", async () => {
    const { user, calls } = start("/leave", pageOf({ "POST /api/units/er/leave/remove": { status: 204 } }))

    await user.click(await screen.findByRole("button", { name: "Remove leave of Amal Saleh, 10 to 11 Nov 2026" }))
    expect(await screen.findByText("Remove this leave of Amal Saleh?")).toBeInTheDocument()
    expect(calls.some((call) => call.url.endsWith("/remove"))).toBe(false)

    await user.click(screen.getByRole("button", { name: "Remove leave" }))

    expect(await screen.findByText("The leave of Amal Saleh is removed: 10 to 11 Nov 2026.")).toBeInTheDocument()
    expect(calls.find((call) => call.url.endsWith("/remove"))!.body).toEqual({ leave_ids: ["l1", "l2"] })
    await waitFor(() => expect(screen.getByRole("button", { name: "Record leave" })).toHaveFocus())
  })

  it("tells a manager with no unit where their own leave is", async () => {
    start("/leave", { ...session(ME_MANAGER), "GET /api/units": { body: [] } })

    expect(await screen.findByRole("link", { name: "My leave" })).toHaveAttribute("href", "/my-leave")
    expect(screen.getByText(/No unit is assigned to you yet/)).toBeInTheDocument()
  })

  describe.each([["the CNO", ME_CNO], ["the Deputy CNO", ME_DEPUTY]])("%s", (_name, me) => {
    const ICU_UNIT = { ...ER_UNIT, id: "icu", name: "ICU" }
    const readerPage = (extra = {}) => pageOf({
      ...session(me),
      "GET /api/units": { body: [ER_UNIT, ICU_UNIT] },
      "GET /api/units/icu/leave": { body: { month: "2026-11", nurses: [BADR], runs: [{ ...BADR_RUN, outside_dates: false, leave_type: ANNUAL }] } },
      ...extra,
    })

    it("reads a unit's month with its types and no way to change anything", async () => {
      const { calls } = start("/leave", readerPage())

      const row = within((await screen.findByRole("link", { name: "Amal Saleh" })).closest("tr")!)
      expect(row.getAllByRole("cell").map((cell) => cell.textContent)).toEqual(["Amal Saleh", "10 to 11 Nov 2026", "2", "Sick"])
      expect(screen.getByRole("heading", { level: 1, name: "Leave" })).toBeInTheDocument()
      expect(screen.getByLabelText("Unit")).toHaveValue("er")
      expect(screen.getByText(/Only the unit's manager can change it/)).toBeInTheDocument()
      expect(within(screen.getByRole("main")).queryAllByRole("button")).toEqual([])
      expect(document.querySelector("form")).toBeNull()
      expect(screen.queryByText(/Actions/)).not.toBeInTheDocument()
      expect(screen.getByRole("region", { name: "Leave in ER, November 2026" })).toHaveAttribute("tabindex", "0")
      expect(screen.getByText(/The unit's manager removes them/)).toBeInTheDocument()
      expect(calls.some((call) => call.url.includes("leave-types"))).toBe(false)
      expect(calls.every((call) => call.method === "GET")).toBe(true)
    })

    it("chooses a unit, keeping the month and letting go of the nurse", async () => {
      const { router, user, calls } = start("/leave?month=2026-11&nurse=n1", readerPage())

      expect(await screen.findByText("Amal Saleh has 2 days of leave in November 2026.")).toBeInTheDocument()
      await user.selectOptions(screen.getByLabelText("Unit"), "icu")

      expect(await screen.findByRole("link", { name: "Badr Omar" })).toBeInTheDocument()
      expect(screen.getByLabelText("Unit")).toHaveFocus()
      expect(screen.getByRole("heading", { name: "November 2026" })).toBeInTheDocument()
      expect(router.state.location.search).toEqual({ unit: "icu", month: "2026-11" })
      expect(calls.some((call) => call.url.includes("/api/units/icu/leave?month=2026-11"))).toBe(true)
    })

    it("keeps the unit through a month and a nurse's month", async () => {
      const { router, user, calls } = start("/leave?unit=icu&month=2026-11", readerPage({ "GET /api/units/icu/leave": { body: { month: "2026-11", nurses: [BADR], runs: [BADR_RUN] } } }))

      await user.click(await screen.findByRole("link", { name: "Badr Omar" }))
      expect(await screen.findByText("Badr Omar has 1 day of leave in November 2026.")).toBeInTheDocument()
      expect(router.state.location.search).toEqual({ unit: "icu", month: "2026-11", nurse: "n2" })
      expect(within(screen.getByRole("main")).queryAllByRole("button")).toEqual([])

      await user.click(screen.getByRole("link", { name: "Next month" }))
      await waitFor(() => expect(router.state.location.search).toEqual({ unit: "icu", month: "2026-12", nurse: "n2" }))
      expect(calls.some((call) => call.url.includes("/api/units/icu/leave?month=2026-12"))).toBe(true)
      expect(calls.some((call) => call.url.includes("/api/units/er/leave"))).toBe(false)
    })

    it("says so when there are no units, and offers them no leave of their own", async () => {
      start("/leave", readerPage({ "GET /api/units": { body: [] } }))

      expect(await screen.findByText("There are no units yet.")).toBeInTheDocument()
      expect(screen.queryByRole("link", { name: "My leave" })).not.toBeInTheDocument()
    })

    it("says so when the units cannot be read", async () => {
      start("/leave", readerPage({ "GET /api/units": { status: 500 } }))

      expect(await screen.findByRole("alert")).toHaveTextContent("The units could not be read.")
    })
  })

  it("tells a manager who else can see a type, and offers them no unit to choose", async () => {
    start("/leave", pageOf())

    expect(await screen.findByText(/Only you, the nurse, the CNO and the Deputy CNO can see a leave's type/)).toBeInTheDocument()
    expect(screen.queryByLabelText("Unit")).not.toBeInTheDocument()
  })

  it("the System Admin has no way in", async () => {
    const { router } = start("/leave", admin())

    await screen.findByRole("heading", { name: "Health" })
    expect(router.state.location.pathname).not.toBe("/leave")
  })

  it.each(["/leave"])("%s has no way in for a staff nurse", async (path) => {
    const { router } = start(path, { ...session(NURSE), "GET /api/nurses/my-unit": { body: { id: "er", name: "ER" } } })

    await screen.findByText("No roster yet.")
    expect(router.state.location.pathname).toBe("/")
  })

  it("a staff nurse's home and header lead to their own leave", async () => {
    start("/", { ...session(NURSE), "GET /api/nurses/my-unit": { body: { id: "er", name: "ER" } } })

    await screen.findByText("No roster yet.")
    expect(within(screen.getByRole("navigation", { name: "Main" })).getByRole("link", { name: "My leave" })).toHaveAttribute("href", "/my-leave")
    expect(within(screen.getByRole("main")).getByRole("link", { name: "My leave" })).toHaveAttribute("href", "/my-leave")
  })

  it("a nurse reads their own leave with its type", async () => {
    const { user, router } = start("/my-leave", {
      ...session(NURSE),
      "GET /api/nurses/my-leave": { body: { month: "2026-11", runs: [{ first: "2026-11-10", last: "2026-11-12", days: 3, leave_type: "Annual" }] } },
    })

    const row = within((await screen.findByRole("cell", { name: "Annual" })).closest("tr")!)
    expect(document.title).toBe("My leave · Nurse roster")
    expect(row.getAllByRole("cell").map((cell) => cell.textContent)).toEqual(["10 to 12 Nov 2026", "3", "Annual"])
    expect(screen.getByText(/Only you, your manager, the CNO and the Deputy CNO can see its type: colleagues see a day off/)).toBeInTheDocument()

    await user.click(screen.getByRole("link", { name: "Previous month" }))
    await waitFor(() => expect(router.state.location.search).toEqual({ month: "2026-10" }))
  })

  it("the audit log names what was done to leave", async () => {
    const entry = (id: number, action: string) => ({ id, action, actor: "mona", target: "h1", at: "2026-11-05T07:00:00+03:00", ip: null, before: null, after: null })
    start("/audit-log", admin({
      "GET /api/audit/entries": { body: { entries: [entry(1, "leave.recorded"), entry(2, "leave.changed"), entry(3, "leave.removed")], next_before: null } },
      "GET /api/audit/filter-options": { body: { users: [], actions: [] } },
    }))

    expect(await screen.findByText("Recorded a nurse's leave")).toBeInTheDocument()
    expect(screen.getByText("Changed a nurse's leave")).toBeInTheDocument()
    expect(screen.getByText("Removed a nurse's leave")).toBeInTheDocument()
  })

  it("a nurse with none in a month is told so", async () => {
    start("/my-leave", { ...session(NURSE), "GET /api/nurses/my-leave": { body: { month: "2026-11", runs: [] } } })

    expect(await screen.findByText("You have no leave recorded in November 2026.")).toBeInTheDocument()
  })

  it("a failed read says so", async () => {
    start("/my-leave", { ...session(NURSE), "GET /api/nurses/my-leave": { status: 500 } })

    expect((await screen.findByRole("alert")).textContent).toMatch(/could not be read/)
  })
})
