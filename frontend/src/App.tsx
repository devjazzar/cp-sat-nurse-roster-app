import { useGetHealth } from "@/api/generated/endpoints"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

function Reachability({ name, reachable }: { name: string; reachable: boolean }) {
  return (
    <div className="flex items-center justify-between">
      <span>{name}</span>
      <Badge variant={reachable ? "secondary" : "destructive"}>{reachable ? "Reachable" : "Unreachable"}</Badge>
    </div>
  )
}

export function App() {
  const health = useGetHealth()

  return (
    <main className="flex min-h-svh items-center justify-center p-4">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle>Nurse roster</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          {health.isPending && <p>Checking the installation…</p>}
          {health.isError && <p role="alert">The application cannot be reached.</p>}
          {health.data && (
            <>
              <Reachability name="Database" reachable={health.data.data.database} />
              <Reachability name="Solver" reachable={health.data.data.solver.reachable} />
            </>
          )}
        </CardContent>
      </Card>
    </main>
  )
}
