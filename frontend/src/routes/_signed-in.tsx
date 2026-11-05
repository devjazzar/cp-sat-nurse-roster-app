import { createFileRoute, Link, Outlet, redirect, useRouteContext } from "@tanstack/react-router"

import { Button } from "@/components/ui/button"
import { useAwaitingPassword } from "@/lib/use-awaiting-password"
import { NAVIGATION, ROLE_NAMES } from "@/roles"
import { currentUser, useSignOut } from "@/session"

/** Everything past the login. */
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
  // Logging out clears the mutation cache and leaves the page, so a password on its way would reach nobody.
  const awaitingPassword = useAwaitingPassword()

  return (
    <div className="min-h-svh">
      <header className="flex flex-wrap items-center gap-x-4 gap-y-2 border-b px-4 py-3 print:hidden">
        <span className="font-medium">Nurse roster</span>
        <nav aria-label="Main" className="flex flex-wrap items-center gap-4">
          {NAVIGATION[user.role].map(({ label, ...link }) => (
            <Link key={link.to} {...link} className={linkClass}>{label}</Link>
          ))}
          <Link to="/change-password" className={linkClass}>Change password</Link>
        </nav>
        <div className="ms-auto flex items-center gap-3">
          <span className="text-sm text-muted-foreground">{user.username} · {ROLE_NAMES[user.role]}</span>
          <Button variant="outline" size="sm" onClick={signOut.run} disabled={signOut.pending || awaitingPassword}>Log out</Button>
        </div>
      </header>
      <main tabIndex={-1} className="p-4 outline-none">
        <Outlet />
      </main>
    </div>
  )
}
