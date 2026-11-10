"""The install guide names the push services' hosts for the hospital's firewall (ticket 42). They are the hosts the application
sends to, `notifications.subscriptions`, and this is what keeps the guide's list and the code's the same: change either alone
and it fails."""
import re
from pathlib import Path

from notifications.subscriptions import PUSH_SERVICE_DOMAINS, PUSH_SERVICE_HOSTS

GUIDE = Path(__file__).parents[3] / "deploy/INSTALL.md"
A_NAME = re.compile(r"`((?:\*\.)?[a-z0-9-]+(?:\.[a-z0-9-]+)+)`")


def named_for_the_firewall() -> set[str]:
    """The host names in the list of the guide's section on pushes."""
    section = GUIDE.read_text().split("\n## Pushes\n", 1)[1].split("\n## ", 1)[0]
    return {name for line in section.splitlines() if line.startswith("- `") for name in A_NAME.findall(line.split(":", 1)[0])}


def test_the_guide_names_every_host_the_worker_sends_to_and_no_other():
    assert named_for_the_firewall() == PUSH_SERVICE_HOSTS | {f"*.{domain}" for domain in PUSH_SERVICE_DOMAINS}


def test_they_are_the_five_names_ticket_41_settled():
    assert named_for_the_firewall() == {"fcm.googleapis.com", "push.services.mozilla.com", "*.push.services.mozilla.com",
                                        "*.push.apple.com", "*.notify.windows.com"}
