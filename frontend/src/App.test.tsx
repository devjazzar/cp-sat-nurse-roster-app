import { QueryClientProvider } from "@tanstack/react-query"
import { createMemoryHistory, RouterProvider } from "@tanstack/react-router"
import { render, screen, waitFor } from "@testing-library/react"
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
      const handler = handlers[`${method} ${url}`]
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
  it.each(["/", "/health", "/settings", "/change-password"])("%s sends a stranger to the login page", async (path) => {
    const { router } = start(path, session(null))

    expect(await screen.findByRole("button", { name: "Log in" })).toBeInTheDocument()
    expect(router.state.location.pathname).toBe("/login")
  })

  it.each(["/", "/health", "/settings"])("%s sends a forced change to the password page", async (path) => {
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

  it.each(["/health", "/settings"])("%s is not for another role", async (path) => {
    const { router, calls } = start(path, session(NURSE))

    expect(await screen.findByText(/nothing here for your role/)).toBeInTheDocument()
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
