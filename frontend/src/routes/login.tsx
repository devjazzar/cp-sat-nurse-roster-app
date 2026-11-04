import { zodResolver } from "@hookform/resolvers/zod"
import { useQueryClient } from "@tanstack/react-query"
import { createFileRoute, redirect, useNavigate } from "@tanstack/react-router"
import { useForm } from "react-hook-form"
import { z } from "zod"

import { ApiError } from "@/api/fetcher"
import { useLogin } from "@/api/generated/endpoints"
import type { LoginRefusal } from "@/api/generated/model"
import { FormField } from "@/components/form-field"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { FieldGroup } from "@/components/ui/field"
import { currentUser, setCurrentUser } from "@/session"

export const Route = createFileRoute("/login")({
  beforeLoad: async ({ context }) => {
    if (await currentUser(context.queryClient)) throw redirect({ to: "/" })
  },
  staticData: { title: "Log in" },
  component: LoginPage,
})

const schema = z.object({
  username: z.string().min(1, "Enter your username."),
  password: z.string().min(1, "Enter your password."),
})

function refusalMessage(error: unknown): string {
  if (error instanceof ApiError && error.status === 423) {
    const until = (error.body as LoginRefusal).locked_until
    const time = until ? new Date(until).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : null
    return time
      ? `Too many failed logins. This account is locked until ${time}. Try again then.`
      : "Too many failed logins. This account is locked. Try again later."
  }
  if (error instanceof ApiError && error.status === 401) return "Wrong username or password."
  return "The login could not be completed. Try again."
}

function LoginPage() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const login = useLogin()
  const form = useForm({ resolver: zodResolver(schema), defaultValues: { username: "", password: "" } })

  const submit = form.handleSubmit((data) =>
    login.mutate(
      { data },
      {
        onSuccess: (me) => {
          setCurrentUser(queryClient, me)
          // The signed-in layout sends a forced password change where it belongs.
          void navigate({ to: "/" })
        },
      },
    ),
  )

  return (
    <main className="flex min-h-svh items-center justify-center p-4">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle><h1>Nurse roster</h1></CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={submit} noValidate>
            <FieldGroup>
              <FormField label="Username" autoComplete="username" autoFocus
                registration={form.register("username")} error={form.formState.errors.username} />
              <FormField label="Password" type="password" autoComplete="current-password"
                registration={form.register("password")} error={form.formState.errors.password} />
              {login.isError && <p role="alert" className="text-sm text-destructive">{refusalMessage(login.error)}</p>}
              <Button type="submit" disabled={login.isPending}>Log in</Button>
            </FieldGroup>
          </form>
        </CardContent>
      </Card>
    </main>
  )
}
