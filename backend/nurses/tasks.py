from accounts.models import Role, User
from accounts.provisioning import deactivate_many
from nurses import membership
from ops.queue import hourly


@hourly(at_minute=5)
def close_ended_nurses(timestamp: int) -> None:
    """Staff nurses whose last day is over. Hourly rather than at midnight, so a worker that was down catches up, and
    it costs one query when nobody has ended. A manager's account is the System Admin's: their profile ends alone."""
    deactivate_many(User.objects.filter(role=Role.STAFF_NURSE, is_active=True,
                                        nurse_profile__end_date__lt=membership.today()))
