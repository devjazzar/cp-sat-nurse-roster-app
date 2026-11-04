import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen } from "@testing-library/react"
import { afterEach, describe, expect, it, vi } from "vitest"

import { App } from "./App"

function renderWithHealth(fetchImpl: typeof fetch) {
  vi.stubGlobal("fetch", vi.fn(fetchImpl))
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <App />
    </QueryClientProvider>,
  )
}

function healthResponse(solverReachable: boolean) {
  return new Response(
    JSON.stringify({
      status: solverReachable ? "ok" : "degraded",
      database: true,
      solver: { reachable: solverReachable, version: solverReachable ? "0.1.0" : null, workers: solverReachable ? 8 : null },
    }),
    { status: 200, headers: { "Content-Type": "application/json" } },
  )
}

afterEach(() => vi.unstubAllGlobals())

describe("the first page", () => {
  it("reads the health endpoint through the generated client", async () => {
    renderWithHealth(async () => healthResponse(true))

    expect(await screen.findByText("Solver")).toBeInTheDocument()
    expect(screen.getAllByText("Reachable")).toHaveLength(2)
    expect(vi.mocked(fetch).mock.calls[0][0]).toBe("/api/health")
  })

  it("says so when the solver is down", async () => {
    renderWithHealth(async () => healthResponse(false))

    expect(await screen.findByText("Unreachable")).toBeInTheDocument()
  })

  it("says so when the application cannot be reached", async () => {
    renderWithHealth(async () => {
      throw new TypeError("network down")
    })

    expect(await screen.findByRole("alert")).toHaveTextContent("cannot be reached")
  })
})
