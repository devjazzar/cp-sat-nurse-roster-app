// The service worker, there only so the app installs to a phone's home screen (ticket 23). It keeps nothing offline and sends
// no push. It has no `fetch` listener on purpose: every request, the page itself, the API, a roster export, a print sheet, a
// backup, goes to the network exactly as it would without a worker, under the server's own Cache-Control (`no-store` on the
// files, `no-cache` on the page). Never add one without reading ticket 23's comment: what must never be cached is listed there.
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
