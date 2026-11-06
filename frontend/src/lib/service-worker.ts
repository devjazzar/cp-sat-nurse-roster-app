/** Registers public/sw.js, which is there so the app installs to a phone's home screen and handles no request (ticket 23).
 *  `updateViaCache: "none"` has the browser ask the server for the worker on every check, so a deploy's new one is found at
 *  the next visit. A browser without service workers, or one that refuses (a certificate it does not trust), simply has none:
 *  the app works the same, only not installable. */
export function registerServiceWorker() {
  if (!("serviceWorker" in navigator)) return
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js", { scope: "/", updateViaCache: "none" }).catch(() => undefined)
  })
}
