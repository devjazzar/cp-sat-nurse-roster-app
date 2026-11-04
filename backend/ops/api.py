from django.db import OperationalError, connection
from ninja import Router, Schema

from ops.solver_client import SolverUnreachable, solver_health

router = Router()


class SolverHealth(Schema):
    reachable: bool
    version: str | None = None
    workers: int | None = None


class Health(Schema):
    status: str
    database: bool
    solver: SolverHealth


def _database_reachable() -> bool:
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return True
    except OperationalError:
        return False


def _solver() -> SolverHealth:
    try:
        health = solver_health()
    except SolverUnreachable:
        return SolverHealth(reachable=False)
    return SolverHealth(reachable=True, version=health.get("version"), workers=health.get("workers"))


@router.get("/health", response=Health, operation_id="getHealth")
def health(request) -> Health:
    """Always 200 while this process is alive; the body says what it can reach."""
    database, solver = _database_reachable(), _solver()
    return Health(status="ok" if database and solver.reachable else "degraded", database=database, solver=solver)
