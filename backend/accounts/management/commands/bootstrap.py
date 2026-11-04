import os

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.models import Role, User
from audit.log import record

USERNAME = "admin"


class Command(BaseCommand):
    help = "First start: creates the System Admin from INITIAL_ADMIN_PASSWORD. Does nothing afterwards."

    def handle(self, *args, **options):
        if User.objects.filter(role=Role.SYSTEM_ADMIN).exists():
            return
        password = os.environ.get("INITIAL_ADMIN_PASSWORD", "")
        if not password:
            raise CommandError("INITIAL_ADMIN_PASSWORD is not set and there is no System Admin yet.")
        with transaction.atomic():
            user = User.objects.create_user(USERNAME, password, Role.SYSTEM_ADMIN, full_name="System Admin",
                                            must_change_password=True)
            record("user.created", target=user.username,
                   after={"username": user.username, "role": user.role, "must_change_password": True})
        self.stdout.write(f"Created the System Admin '{USERNAME}'; the password must change at first login.")
