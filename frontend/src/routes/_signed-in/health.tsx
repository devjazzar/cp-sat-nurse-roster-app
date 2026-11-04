import { createFileRoute, redirect } from "@tanstack/react-router"
import type { ReactNode } from "react"

import { useGetInstallationHealth } from "@/api/generated/endpoints"
import { Role } from "@/api/generated/model"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

export const Route = createFileRoute("/_signed-in/health")({
  beforeLoad: ({ context }) => {
    if (context.user.role !== Role.system_admin) throw redirect({ to: "/" })
  },
  component: HealthPage,
})

export function formatBytes(bytes: number): string {
  const units = ["B", "KB", "MB", "GB", "TB"]
  const power = Math.min(Math.floor(Math.log(Math.max(bytes, 1)) / Math.log(1024)), units.length - 1)
  const value = bytes / 1024 ** power
  return `${power === 0 || value >= 100 ? value.toFixed(0) : value.toFixed(1)} ${units[power]}`
}

function Row({ name, children }: { name: string; children: ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-4">
      <dt>{name}</dt>
      <dd className="text-right text-muted-foreground">{children}</dd>
    </div>
  )
}

function Reachability({ reachable }: { reachable: boolean }) {
  return <Badge variant={reachable ? "secondary" : "destructive"}>{reachable ? "Reachable" : "Unreachable"}</Badge>
}

function HealthPage() {
  // A manual refresh and no timer: polling would keep an idle session alive for ever.
  const health = useGetInstallationHealth()

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-medium">Health</h1>
        <Button variant="outline" size="sm" onClick={() => health.refetch()} disabled={health.isFetching}>Refresh</Button>
      </div>
      {health.isPending && <p>Checking the installation…</p>}
      {health.isError && <p role="alert">The health of the installation could not be read.</p>}
      {health.data && (
        <div className="grid gap-4 sm:grid-cols-2">
          <Card>
            <CardHeader><CardTitle>Services</CardTitle></CardHeader>
            <CardContent>
              <dl className="flex flex-col gap-2">
                <Row name="Solver"><Reachability reachable={health.data.solver.reachable} /></Row>
                {health.data.solver.version && <Row name="Solver version">{health.data.solver.version}</Row>}
                {health.data.solver.workers != null && <Row name="Solver threads">{health.data.solver.workers}</Row>}
                <Row name="Database"><Reachability reachable={health.data.database} /></Row>
              </dl>
            </CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle>Queue</CardTitle></CardHeader>
            <CardContent>
              <dl className="flex flex-col gap-2">
                <Row name="Workers alive">{health.data.queue.workers}</Row>
                <Row name="Jobs waiting">{health.data.queue.waiting}</Row>
                <Row name="Jobs running">{health.data.queue.running}</Row>
                <Row name="Jobs failed">{health.data.queue.failed}</Row>
              </dl>
            </CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle>Storage</CardTitle></CardHeader>
            <CardContent>
              <dl className="flex flex-col gap-2">
                <Row name="Database size">{formatBytes(health.data.database_size_bytes)}</Row>
                {health.data.disk ? (
                  <>
                    <Row name="Disk free">{formatBytes(health.data.disk.free_bytes)}</Row>
                    <Row name="Disk size">{formatBytes(health.data.disk.total_bytes)}</Row>
                  </>
                ) : (
                  <Row name="Disk">Unknown</Row>
                )}
              </dl>
            </CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle>Backups</CardTitle></CardHeader>
            <CardContent>
              <dl className="flex flex-col gap-2">
                <Row name="Last backup">
                  {health.data.last_backup ? new Date(health.data.last_backup).toLocaleString() : "None yet"}
                </Row>
              </dl>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}
