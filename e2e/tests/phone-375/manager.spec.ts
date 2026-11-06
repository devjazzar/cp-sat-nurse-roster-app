import { expect, test } from "@playwright/test"

import { expectNoSidewaysScroll, go, monthName, signIn, stack } from "../../support"
import { replanTheLargeUnit } from "../replan"

// Ticket 24, left by ticket 23: a unit manager's Requests and Swaps pages, and a re-plan's result, on a 375 px phone (an
// iPhone's width; the `phone-375` project). A manager's pages are not made for a phone, so what holds is that none makes the
// page itself scroll sideways: their tables scroll inside their own regions, which are in view.

test("the manager's Requests page, with its windows and requests, keeps within a phone's width", async ({ page }) => {
  await signIn(page, "mona")
  await go(page, "Requests")
  const windows = page.getByRole("region", { name: "Request windows, newest first" })
  await expect(windows.getByRole("row", { name: new RegExp(monthName(stack.window_month)) })).toBeVisible()
  await expect(page.getByRole("region", { name: `Requests for ${monthName(stack.window_month)}, by date` })
    .or(page.getByText("No requests were made in this window."))).toBeVisible()
  await expectNoSidewaysScroll(page)
  for (const region of await page.getByRole("region").all()) await expect(region).toBeInViewport({ ratio: 0 })
})

test("the manager's Swaps page keeps within a phone's width", async ({ page }) => {
  await signIn(page, "mona")
  await go(page, "Swaps")
  await page.goto(`/unit-swaps?month=${stack.approved_month}`)
  await expect(page.getByRole("heading", { level: 2, name: monthName(stack.approved_month) })).toBeVisible()
  // Ticket 23's swap check leaves withdrawn swaps on ER's approved month, so there is a list to read.
  await expect(page.getByRole("region", { name: "The unit's swaps, newest first" })).toBeVisible()
  await expectNoSidewaysScroll(page)
})

test("a re-plan's result keeps within a phone's width, its comparison tables scrolling in their own regions", async ({ page }) => {
  test.setTimeout(180_000)
  await signIn(page, "omar")
  const result = await replanTheLargeUnit(page)
  await expectNoSidewaysScroll(page)
  const rules = result.getByRole("table", { name: "Each rule, before and after" })
  await rules.scrollIntoViewIfNeeded()
  await expect(rules.getByRole("columnheader", { name: "Rule" })).toBeInViewport()
  await expectNoSidewaysScroll(page)
})
