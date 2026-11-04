import { createFileRoute, redirect } from "@tanstack/react-router"

import { Role } from "@/api/generated/model"

export const Route = createFileRoute("/_signed-in/")({
  beforeLoad: ({ context }) => {
    if (context.user.role === Role.system_admin) throw redirect({ to: "/health" })
  },
  staticData: { title: "Home" },
  component: () => <p>There is nothing here for your role yet.</p>,
})
