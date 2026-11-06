import { defineConfig, devices } from "@playwright/test"

import { stack } from "./support"

/** The browser checks, against a stack e2e/stack.sh started and seeded: `E2E_STACK=<project> npx playwright test`.
 *
 *  Ticket 23 checks phones only. Each project is a phone (a touch screen, a mobile Chrome's user agent) at one width; 320 px is
 *  the narrowest the app holds to, which is also a 640 px window at 200% zoom. The checks share one seeded stack and change it,
 *  so they run one at a time, and each puts back what it changed. `deploy` restarts `web`, so it runs last, after the rest.
 *  Ticket 24 adds its journeys and a desktop project here. */
const phone = (width: number, height: number) => ({ ...devices["Pixel 7"], viewport: { width, height } })

export default defineConfig({
  testDir: "tests",
  fullyParallel: false,
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: 0,
  reporter: [["list"]],
  use: {
    baseURL: stack.baseURL,
    trace: "retain-on-failure",
  },
  projects: [
    { name: "phone-360", use: phone(360, 780), testIgnore: /deploy\.spec/ },
    { name: "phone-320", use: phone(320, 640), testMatch: /layout\.spec/ },
    { name: "deploy", use: phone(360, 780), testMatch: /deploy\.spec/, dependencies: ["phone-360", "phone-320"] },
  ],
})
