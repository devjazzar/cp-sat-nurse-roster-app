import { createFileRoute, Link, Outlet, redirect, useRouteContext } from "@tanstack/react-router"

import { Role } from "@/api/generated/model"
import { Button } from "@/components/ui/button"
import { currentUser, useSignOut } from "@/session"

/** Everything past the login. Ticket 03 scopes the navigation for the other roles. */
export const Route = createFileRoute("/_signed-in")({
  beforeLoad: async ({ context }) => {
    const user = await currentUser(context.queryClient)
    if (!user) throw redirect({ to: "/login" })
    if (user.must_change_password) throw redirect({ to: "/change-password" })
    return { user }
  },
  component: SignedInLayout,
})

const linkClass = "text-sm text-muted-foreground hover:text-foreground [&.active]:font-medium [&.active]:text-foreground"

function SignedInLayout() {
  const { user } = useRouteContext({ from: "/_signed-in" })
  const signOut = useSignOut()

  return (
    <div className="min-h-svh">
      <header className="flex flex-wrap items-center gap-x-4 gap-y-2 border-b px-4 py-3">
        <span className="font-medium">Nurse roster</span>
        <nav className="flex flex-wrap items-center gap-4">
          {user.role === Role.system_admin && (
            <>
              <Link to="/health" className={linkClass}>Health</Link>
              <Link to="/settings" className={linkClass}>Technical settings</Link>
            </>
          )}
          <Link to="/change-password" className={linkClass}>Change password</Link>
        </nav>
        <div className="ms-auto flex items-center gap-3">
          <span className="text-sm text-muted-foreground">{user.username}</span>
          <Button variant="outline" size="sm" onClick={signOut.run} disabled={signOut.pending}>Log out</Button>
        </div>
      </header>
      <main tabIndex={-1} className="mx-auto max-w-3xl p-4 outline-none">
        <Outlet />
      </main>
    </div>
  )
}
