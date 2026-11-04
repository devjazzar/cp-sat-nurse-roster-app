import { MutationCache, QueryCache, QueryClient } from "@tanstack/react-query"
import { createRouter, type RouterHistory } from "@tanstack/react-router"

import { ApiError } from "@/api/fetcher"
import { cachedUser, setCurrentUser } from "@/session"

import { routeTree } from "./routeTree.gen"

let onSessionEnded = () => {}

/** A 401 while we believed someone was signed in means the session ended behind our back: idle
 *  expiry, deactivation, or a password change elsewhere. A wrong password at login is also a 401,
 *  but nobody is signed in then, so it is left to the login form. */
function sessionCheck(queryClient: () => QueryClient) {
  return (error: unknown) => {
    if (error instanceof ApiError && error.status === 401 && cachedUser(queryClient())) {
      queryClient().clear()
      setCurrentUser(queryClient(), null)
      onSessionEnded()
    }
  }
}

export function createQueryClient(): QueryClient {
  const client: QueryClient = new QueryClient({
    queryCache: new QueryCache({ onError: sessionCheck(() => client) }),
    mutationCache: new MutationCache({ onError: sessionCheck(() => client) }),
    defaultOptions: {
      queries: {
        retry: (failures, error) => failures < 2 && !(error instanceof ApiError && error.status < 500),
      },
    },
  })
  return client
}

export function createAppRouter(queryClient: QueryClient, history?: RouterHistory) {
  const router = createRouter({
    routeTree,
    history,
    context: { queryClient },
    defaultErrorComponent: () => (
      <main className="flex min-h-svh items-center justify-center p-4">
        <p role="alert">The application cannot be reached. Reload the page to try again.</p>
      </main>
    ),
    defaultNotFoundComponent: () => (
      <main className="flex min-h-svh items-center justify-center p-4">
        <p>There is no such page.</p>
      </main>
    ),
  })
  onSessionEnded = () => void router.navigate({ to: "/login" })
  return router
}

declare module "@tanstack/react-router" {
  interface Register {
    router: ReturnType<typeof createAppRouter>
  }
}
