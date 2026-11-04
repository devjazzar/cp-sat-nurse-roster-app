from datetime import datetime, time
from typing import Annotated

from django.db import OperationalError, connection, transaction
from ninja import Router, Schema
from pydantic import Field

from accounts.authz import SignedIn
from accounts.models import Role
from audit.log import record
from ops.models import TechnicalSettings
from ops.solver_client import SolverUnreachable, solver_health
from ops.status import database_size_bytes, disk_usage, queue_state

router = Router()
system_admin = SignedIn(Role.SYSTEM_ADMIN)


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


class Disk(Schema):
    total_bytes: int
    free_bytes: int


class Queue(Schema):
    waiting: int
    running: int
    failed: int
    workers: int


class InstallationHealth(Schema):
    database: bool
    solver: SolverHealth
    database_size_bytes: int
    disk: Disk | None
    queue: Queue
    last_backup: datetime | None = Field(description="Always empty until backups exist.")


@router.get("/ops/health", response=InstallationHealth, auth=system_admin, operation_id="getInstallationHealth")
def installation_health(request) -> InstallationHealth:
    return InstallationHealth(database=_database_reachable(), solver=_solver(),
                              database_size_bytes=database_size_bytes(), disk=disk_usage(), queue=queue_state(),
                              last_backup=None)


ClockTime = Annotated[str, Field(pattern="^([01][0-9]|2[0-3]):[0-5][0-9]$", examples=["02:00"])]


class TechnicalSettingsSchema(Schema):
    time_limit_cap_seconds: int = Field(ge=1, le=86400)
    backup_time: ClockTime
    backup_retention_days: int = Field(ge=1, le=3650)
    close_time: ClockTime


def _as_dict(row: TechnicalSettings) -> dict:
    return {"time_limit_cap_seconds": row.time_limit_cap_seconds, "backup_time": row.backup_time.strftime("%H:%M"),
            "backup_retention_days": row.backup_retention_days, "close_time": row.close_time.strftime("%H:%M")}


@router.get("/ops/technical-settings", response=TechnicalSettingsSchema, auth=system_admin,
            operation_id="getTechnicalSettings")
def get_technical_settings(request) -> dict:
    return _as_dict(TechnicalSettings.load())


@router.put("/ops/technical-settings", response=TechnicalSettingsSchema, auth=system_admin,
            operation_id="updateTechnicalSettings")
def update_technical_settings(request, body: TechnicalSettingsSchema) -> dict:
    with transaction.atomic():
        row = TechnicalSettings.load(for_update=True)
        before = _as_dict(row)
        after = body.model_dump()
        if after != before:
            row.time_limit_cap_seconds = body.time_limit_cap_seconds
            row.backup_time = time.fromisoformat(body.backup_time)
            row.backup_retention_days = body.backup_retention_days
            row.close_time = time.fromisoformat(body.close_time)
            row.save()
            record("technical_settings.changed", actor=request.user, target="technical settings",
                   before=before, after=after, request=request)
    return after
