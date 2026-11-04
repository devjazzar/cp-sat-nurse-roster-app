from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.db import models
from django.db.models.functions import UUID7


class Role(models.TextChoices):
    SYSTEM_ADMIN = "system_admin", "System Admin"
    CNO = "cno", "CNO"
    DEPUTY_CNO = "deputy_cno", "Deputy CNO"
    UNIT_MANAGER = "unit_manager", "Unit Manager"
    STAFF_NURSE = "staff_nurse", "Staff Nurse"


class UserManager(BaseUserManager):
    def create_user(self, username: str, password: str, role: str, **fields) -> "User":
        user = self.model(username=username, role=role, **fields)
        user.set_password(password)
        user.save(using=self._db)
        return user


class User(AbstractBaseUser):
    id = models.UUIDField(primary_key=True, db_default=UUID7(), editable=False)
    username = models.CharField(max_length=150, unique=True)
    full_name = models.CharField(max_length=200, blank=True)
    role = models.CharField(max_length=20, choices=Role)
    is_active = models.BooleanField(default=True)
    must_change_password = models.BooleanField(default=False)

    USERNAME_FIELD = "username"

    objects = UserManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["role"], condition=models.Q(role=Role.SYSTEM_ADMIN),
                                    name="accounts_one_system_admin"),
        ]


class LoginAttempts(models.Model):
    """Consecutive failed logins per username tried, known or not. Keyed by the name rather than
    held on the user, so an unknown username locks exactly like a real one and the answer to a
    login never says which usernames exist. The row goes away at the next successful login."""

    username = models.CharField(max_length=150, primary_key=True)
    failures = models.PositiveSmallIntegerField(default=0)
    locked_until = models.DateTimeField(null=True)
