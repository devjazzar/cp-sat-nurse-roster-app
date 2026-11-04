import { useQueryClient, type QueryClient } from "@tanstack/react-query"
import { useNavigate } from "@tanstack/react-router"

import { getGetSessionQueryKey, getGetSessionQueryOptions, useLogout } from "@/api/generated/endpoints"
import type { Me, SessionState } from "@/api/generated/model"

/** Who is signed in. The answer is cached until login, logout, a password change or a 401 changes
 *  it, so a route guard costs no request. Nothing here polls: see SESSION_SAVE_EVERY_REQUEST. */
export async function currentUser(queryClient: QueryClient): Promise<Me | null> {
  const session = await queryClient.ensureQueryData(getGetSessionQueryOptions<SessionState>())
  return session.user ?? null
}

export function setCurrentUser(queryClient: QueryClient, user: Me | null) {
  queryClient.setQueryData<SessionState>(getGetSessionQueryKey(), { user })
}

export function cachedUser(queryClient: QueryClient): Me | null {
  return queryClient.getQueryData<SessionState>(getGetSessionQueryKey())?.user ?? null
}

export function useSignOut() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const logout = useLogout()
  return {
    pending: logout.isPending,
    run: () =>
      logout.mutate(undefined, {
        onSuccess: () => {
          queryClient.clear() // what the last user saw must not outlive their session
          setCurrentUser(queryClient, null)
          void navigate({ to: "/login" })
        },
      }),
  }
}
