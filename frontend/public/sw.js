// The service worker, there so the app installs to a phone's home screen (ticket 23) and so a device keeps its pushes when
// the browser renews its subscription (ticket 40). It keeps nothing offline. It has no `fetch` listener on purpose: every
// request, the page itself, the API, a roster export, a print sheet, a backup, goes to the network exactly as it would
// without a worker, under the server's own Cache-Control (`no-store` on the files, `no-cache` on the page). Never add one
// without reading ticket 23's comment: what must never be cached is listed there.
//
// Served at /sw.js with `no-cache` (backend/config/settings.py) and registered with updateViaCache "none" (src/main.tsx), so a
// deploy's new worker is found at the next visit. It takes over at once, and removes any cache an earlier one left.

self.addEventListener("install", (event) => {
  event.waitUntil(self.skipWaiting())
})

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((names) => Promise.all(names.map((name) => caches.delete(name))))
      .then(() => self.clients.claim()),
  )
})

// The browser renewed this device's subscription behind the scenes (ticket 40). If the server held the old address for the
// signed-in user, the device subscribes again with the server's current public key and tells it which address the new one
// replaces. One the server does not hold (turned off on every device from another) is left alone. A POST needs the CSRF
// token, which a worker can read only from `cookieStore`; without it the app's own check at its next start is what is left.
self.addEventListener("pushsubscriptionchange", (event) => {
  event.waitUntil(renewSubscription(event.oldSubscription))
})

// The app's own `renewAfterARotation` (src/lib/push.ts) does the same at its start, after a key rotation.
async function renewSubscription(old) {
  if (!old || !self.cookieStore) return
  const token = (await self.cookieStore.get("csrftoken"))?.value
  if (!token) return
  const post = async (path, body) => {
    const response = await fetch(`/api/notifications/push/${path}`, {
      method: "POST", credentials: "same-origin", body: JSON.stringify(body),
      headers: { "Content-Type": "application/json", "X-CSRFToken": token },
    })
    if (!response.ok) throw new Error(`The API answered ${response.status}`)
    return response.json()
  }
  const state = await post("state", { endpoint: old.endpoint })
  if (!state.this_device) return
  const pushManager = self.registration.pushManager
  const current = await pushManager.getSubscription()
  if (current) await current.unsubscribe()
  const renewed = await pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: bytesOf(state.public_key) })
  const { endpoint, keys } = renewed.toJSON()
  await post("on", { endpoint, keys: { p256dh: keys.p256dh, auth: keys.auth }, replaces: old.endpoint })
}

// As `bytesOf` in src/lib/push.ts: a worker cannot import the app's modules.
function bytesOf(base64url) {
  const base64 = base64url.replace(/-/g, "+").replace(/_/g, "/").padEnd(Math.ceil(base64url.length / 4) * 4, "=")
  return Uint8Array.from(atob(base64), (char) => char.charCodeAt(0))
}
