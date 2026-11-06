import source from "../public/sw.js?raw"

/** The service worker run against a stand-in for its global scope: what it listens for, and what it does when it does. */
function runWorker(cacheNames: string[] = []) {
  const listeners = new Map<string, (event: { waitUntil: (work: Promise<unknown>) => void }) => void>()
  const deleted: string[] = []
  const calls: string[] = []
  const scope = {
    addEventListener: (type: string, listener: (event: { waitUntil: (work: Promise<unknown>) => void }) => void) => listeners.set(type, listener),
    skipWaiting: async () => { calls.push("skipWaiting") },
    clients: { claim: async () => { calls.push("claim") } },
  }
  const caches = {
    keys: async () => cacheNames,
    delete: async (name: string) => { deleted.push(name); return true },
    open: async () => { throw new Error("the worker must not open a cache") },
    match: async () => { throw new Error("the worker must not read a cache") },
  }
  new Function("self", "caches", source)(scope, caches)
  const fire = async (type: string) => {
    const work: Promise<unknown>[] = []
    listeners.get(type)?.({ waitUntil: (promise) => work.push(promise) })
    await Promise.all(work)
  }
  return { listeners, deleted, calls, fire }
}

test("the service worker handles no request, so nothing under /api, no export, print sheet, backup or /metrics passes through it", () => {
  const { listeners } = runWorker()

  expect([...listeners.keys()].sort()).toEqual(["activate", "install"])
})

test("a new worker takes over at once, so a deploy is not held back behind the old one", async () => {
  const worker = runWorker()

  await worker.fire("install")
  await worker.fire("activate")

  expect(worker.calls).toEqual(["skipWaiting", "claim"])
})

test("on taking over it removes every cache an earlier worker may have left", async () => {
  const worker = runWorker(["spa-v1", "api"])

  await worker.fire("activate")

  expect(worker.deleted.sort()).toEqual(["api", "spa-v1"])
})
