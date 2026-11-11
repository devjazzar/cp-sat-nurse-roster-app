"""The skill catalogue (ticket 32): the CNO's list of skills, which every role reads. The refusals that depend on nurses'
records and unit rules are tickets 33's and 34's; the third mark, "Lets a nurse precept", ticket 53's."""
import pytest
from django.core.management import call_command

from accounts.models import Role
from audit.models import AuditEntry
from hospital.models import Skill
from conftest import post
from nurses.models import NurseSkill
from nurses.tests.conftest import added, make_unit

pytestmark = pytest.mark.django_db

SKILLS = "/api/hospital/skills"
NEW = {"name": "BLS", "expires": True, "required_to_work": True, "lets_a_nurse_precept": False, "active": True}


def create(client, **fields):
    return client.post(SKILLS, NEW | fields, content_type="application/json")


def editable(row: dict) -> dict:
    return {key: value for key, value in row.items() if key not in ("id", "renames")}


def update(client, current_name: str, /, **changes):
    row = next(row for row in client.get(SKILLS).json() if row["name"] == current_name)
    return client.put(f"{SKILLS}/{row['id']}", editable(row) | changes, content_type="application/json")


def refused_fields(response) -> set[tuple]:
    assert response.status_code == 422, response.content
    return {tuple(error["loc"][2:]) for error in response.json()["detail"]}


def messages(response) -> list[str]:
    return [error["msg"] for error in response.json()["detail"]]


def names(client) -> list[str]:
    return [row["name"] for row in client.get(SKILLS).json()]


def marked(client) -> list[str]:
    return [row["name"] for row in client.get(SKILLS).json() if row["lets_a_nurse_precept"]]


@pytest.fixture
def cno(signed_in):
    client = signed_in(Role.CNO, username="the-cno")
    for name, expires, required in [("ICU", False, False), ("ACLS", True, False), ("BLS", True, True)]:
        create(client, name=name, expires=expires, required_to_work=required)
    return client


# ---- the list and the form ------------------------------------------------------------------------
def test_the_catalogue_starts_empty(make_user, signed_in):
    # The spec names no skill: a hospital's are its own.
    make_user("admin", Role.SYSTEM_ADMIN)

    call_command("bootstrap")

    assert signed_in(Role.CNO).get(SKILLS).json() == []


def test_the_cno_adds_a_skill_with_both_flags(signed_in):
    client = signed_in(Role.CNO)

    response = create(client, name="  Preceptor ", expires=False, required_to_work=False)

    assert response.status_code == 201
    assert editable(response.json()) == {"name": "Preceptor", "expires": False, "required_to_work": False,
                                         "lets_a_nurse_precept": False, "active": True}
    assert response.json()["renames"] == []
    assert client.get(SKILLS).json() == [response.json()]


def test_the_list_is_in_alphabetical_order_whatever_the_case_with_retired_skills_on_it(cno):
    create(cno, name="aaa", expires=False, active=False)

    assert names(cno) == ["aaa", "ACLS", "BLS", "ICU"]


def test_the_cno_changes_both_flags(cno):
    response = update(cno, "ICU", expires=True, required_to_work=True)

    assert response.status_code == 200
    assert editable(response.json()) == {"name": "ICU", "expires": True, "required_to_work": True,
                                         "lets_a_nurse_precept": False, "active": True}
    assert update(cno, "ICU", expires=False, required_to_work=False).json()["expires"] is False


def test_a_retired_skill_stays_on_the_list_and_comes_back(cno):
    retired = update(cno, "ACLS", active=False)
    assert retired.status_code == 200 and retired.json()["active"] is False
    assert "ACLS" in names(cno)

    assert update(cno, "ACLS", active=True).json()["active"] is True


def test_there_is_no_way_to_delete_a_skill(cno):
    row = cno.get(SKILLS).json()[0]

    assert cno.delete(f"{SKILLS}/{row['id']}").status_code == 405


@pytest.mark.parametrize("fields, field", [
    ({"name": "   "}, "name"),
    ({"name": "x" * 101}, "name"),
    ({"name": "a\x00b"}, "name"),
    ({"name": "=ICU"}, "name"),  # The solver refuses a name a spreadsheet reads as a formula (ticket 35).
    ({"name": "+ICU"}, "name"),
    ({"name": "-ICU"}, "name"),
    ({"name": "@ICU"}, "name"),
    ({"name": "'ICU"}, "name"),
    ({"name": "IC\nU"}, "name"),
    ({"expires": "yes"}, "expires"),
    ({"required_to_work": 1}, "required_to_work"),
    ({"lets_a_nurse_precept": "no"}, "lets_a_nurse_precept"),
    ({"active": None}, "active"),
    ({"colour": "#000000"}, "colour"),
])
def test_a_refusal_names_the_field(signed_in, fields, field):
    assert refused_fields(create(signed_in(Role.CNO), **fields)) == {(field,)}


@pytest.mark.parametrize("field", ["expires", "required_to_work", "lets_a_nurse_precept", "active"])
def test_every_flag_must_be_given(signed_in, field):
    body = {key: value for key, value in NEW.items() if key != field}

    response = signed_in(Role.CNO).post(SKILLS, body, content_type="application/json")

    assert refused_fields(response) == {(field,)}


def test_an_unknown_skill_is_404(signed_in):
    response = signed_in(Role.CNO).put(f"{SKILLS}/019a0000-0000-7000-8000-000000000000", NEW,
                                       content_type="application/json")

    assert response.status_code == 404


# ---- "Lets a nurse precept" (ticket 53) -------------------------------------------------------------
def test_a_skill_made_without_the_mark_has_it_off():
    # As every skill there was before the mark: the migration leaves them all off.
    skill = Skill.objects.create(name="ICU", expires=False, required_to_work=False)

    skill.refresh_from_db()
    assert skill.lets_a_nurse_precept is False


def test_the_cno_adds_a_skill_that_lets_a_nurse_precept(signed_in):
    client = signed_in(Role.CNO)

    response = create(client, name="Preceptor course", expires=True, required_to_work=False, lets_a_nurse_precept=True)

    assert response.status_code == 201 and response.json()["lets_a_nurse_precept"] is True
    assert client.get(SKILLS).json()[0]["lets_a_nurse_precept"] is True


def test_the_cno_sets_and_clears_the_mark_on_more_than_one_skill(cno):
    assert update(cno, "BLS", lets_a_nurse_precept=True).json()["lets_a_nurse_precept"] is True
    assert update(cno, "ICU", lets_a_nurse_precept=True).json()["lets_a_nurse_precept"] is True
    assert marked(cno) == ["BLS", "ICU"]

    cleared = update(cno, "BLS", lets_a_nurse_precept=False)

    assert cleared.status_code == 200 and cleared.json()["lets_a_nurse_precept"] is False
    assert marked(cno) == ["ICU"]


def test_the_mark_is_cleared_while_a_nurse_holds_the_skill(cno):
    # Unlike turning `expires` on, nothing refuses it: the skill is checked only when a preceptor is assigned.
    update(cno, "ICU", lets_a_nurse_precept=True)
    nurse_id = added(cno, make_unit("ER"))["nurse"]["id"]
    icu = Skill.objects.get(name="ICU")
    assert post(cno, f"/api/nurses/{nurse_id}/skills", {"skill_id": str(icu.pk), "expiry": None}).status_code == 201
    assert NurseSkill.objects.current().filter(skill=icu).exists()

    response = update(cno, "ICU", lets_a_nurse_precept=False)

    assert response.status_code == 200 and marked(cno) == []
    assert NurseSkill.objects.current().filter(skill=icu).exists()


def test_setting_and_clearing_the_mark_are_audited_with_its_value(cno):
    AuditEntry.objects.all().delete()

    update(cno, "ICU", lets_a_nurse_precept=True)
    update(cno, "ICU", lets_a_nurse_precept=False)

    first, second = AuditEntry.objects.order_by("pk")
    assert (first.action, first.target, first.actor.username) == ("skill.changed", "ICU", "the-cno")
    assert first.before == {"lets_a_nurse_precept": False} and first.after == {"lets_a_nurse_precept": True}
    assert (second.action, second.target) == ("skill.changed", "ICU")
    assert second.before == {"lets_a_nurse_precept": True} and second.after == {"lets_a_nurse_precept": False}


def test_adding_a_marked_skill_is_audited_with_the_mark(signed_in):
    client = signed_in(Role.CNO)
    AuditEntry.objects.all().delete()

    create(client, name="Preceptor course", expires=False, required_to_work=False, lets_a_nurse_precept=True)

    entry = AuditEntry.objects.get()
    assert entry.action == "skill.created"
    assert entry.after == {"name": "Preceptor course", "expires": False, "required_to_work": False,
                           "lets_a_nurse_precept": True, "active": True}


@pytest.mark.parametrize("role", list(Role))
def test_every_role_reads_the_mark(signed_in, cno, role):
    update(cno, "BLS", lets_a_nurse_precept=True)
    reader = cno if role == Role.CNO else signed_in(role, username=f"a-{role}")

    assert marked(reader) == ["BLS"]


@pytest.mark.parametrize("role", [role for role in Role if role != Role.CNO])
def test_only_the_cno_sets_or_clears_the_mark(signed_in, cno, role):
    update(cno, "BLS", lets_a_nurse_precept=True)
    client = signed_in(role, username=f"a-{role}")
    AuditEntry.objects.all().delete()

    assert update(client, "ICU", lets_a_nurse_precept=True).status_code == 403
    assert update(client, "BLS", lets_a_nurse_precept=False).status_code == 403
    assert create(client, name="Preceptor course", lets_a_nurse_precept=True).status_code == 403
    assert marked(cno) == ["BLS"] and names(cno) == ["ACLS", "BLS", "ICU"]
    assert not AuditEntry.objects.exists()


# ---- a taken name ---------------------------------------------------------------------------------
@pytest.mark.parametrize("name", ["icu", "ICU", "Icu "])
def test_a_name_cannot_be_used_twice_in_any_case(cno, name):
    created = create(cno, name=name)
    assert refused_fields(created) == {("name",)} and messages(created) == ["ICU is already a skill"]
    assert refused_fields(update(cno, "BLS", name=name)) == {("name",)}


def test_a_skill_may_change_only_the_case_of_its_own_name(cno):
    response = update(cno, "ICU", name="icu")

    assert response.status_code == 200 and response.json()["name"] == "icu"


def test_a_name_another_skill_used_to_hold_cannot_be_taken(cno):
    # A stored input that says "BLS" means the skill now called "Basic life support", so it cannot also mean another.
    update(cno, "BLS", name="Basic life support")

    created = create(cno, name="bls")
    assert refused_fields(created) == {("name",)} and messages(created) == ["BLS is the old name of another skill"]
    assert refused_fields(update(cno, "ICU", name="BLS")) == {("name",)}


def test_a_skill_may_go_back_to_a_name_of_its_own(cno):
    update(cno, "BLS", name="Basic life support")

    response = update(cno, "Basic life support", name="BLS")

    assert response.status_code == 200 and response.json()["name"] == "BLS"


# ---- a rename -------------------------------------------------------------------------------------
def test_a_rename_is_recorded_with_the_old_name_the_new_name_and_the_date(cno):
    response = update(cno, "BLS", name="Basic life support")

    assert response.status_code == 200 and response.json()["name"] == "Basic life support"
    (rename,) = response.json()["renames"]
    assert rename["old_name"] == "BLS" and rename["new_name"] == "Basic life support"
    assert rename["at"].endswith("+03:00")
    assert response.json() in cno.get(SKILLS).json()


def test_each_rename_of_a_skill_is_kept_in_order(cno):
    update(cno, "BLS", name="Basic")
    update(cno, "Basic", name="Life support")

    renames = update(cno, "Life support", name="BLS").json()["renames"]

    assert [(rename["old_name"], rename["new_name"]) for rename in renames] == [
        ("BLS", "Basic"), ("Basic", "Life support"), ("Life support", "BLS")]


def test_a_change_of_case_is_a_rename_too(cno):
    # A stored input names a skill exactly as it was spelled then.
    (rename,) = update(cno, "ICU", name="Icu").json()["renames"]

    assert (rename["old_name"], rename["new_name"]) == ("ICU", "Icu")


def test_a_change_of_flags_records_no_rename(cno):
    assert update(cno, "ICU", expires=True, active=False).json()["renames"] == []


# ---- the audit log --------------------------------------------------------------------------------
def test_adding_is_audited_with_every_value(signed_in):
    client = signed_in(Role.CNO, username="the-cno")
    AuditEntry.objects.all().delete()

    create(client, name="ICU", expires=False, required_to_work=True)

    entry = AuditEntry.objects.get()
    assert entry.action == "skill.created" and entry.actor.username == "the-cno" and entry.target == "ICU"
    assert entry.before is None
    assert entry.after == {"name": "ICU", "expires": False, "required_to_work": True, "lets_a_nurse_precept": False,
                           "active": True}


def test_a_change_is_audited_with_only_what_changed(cno):
    AuditEntry.objects.all().delete()

    update(cno, "ICU", required_to_work=True)

    entry = AuditEntry.objects.get()
    assert entry.action == "skill.changed" and entry.actor.username == "the-cno" and entry.target == "ICU"
    assert entry.before == {"required_to_work": False} and entry.after == {"required_to_work": True}


def test_a_rename_is_audited_under_the_new_name(cno):
    AuditEntry.objects.all().delete()

    update(cno, "BLS", name="Basic life support")

    entry = AuditEntry.objects.get()
    assert entry.action == "skill.changed" and entry.target == "Basic life support"
    assert entry.before == {"name": "BLS"} and entry.after == {"name": "Basic life support"}


def test_a_retire_is_audited(cno):
    AuditEntry.objects.all().delete()

    update(cno, "ACLS", active=False)

    entry = AuditEntry.objects.get()
    assert entry.action == "skill.changed" and entry.target == "ACLS"
    assert entry.before == {"active": True} and entry.after == {"active": False}


def test_saving_with_no_change_writes_no_entry_and_no_rename(cno):
    AuditEntry.objects.all().delete()

    response = update(cno, "ICU")

    assert response.status_code == 200 and response.json()["renames"] == []
    assert not AuditEntry.objects.exists()


def test_a_refused_change_writes_nothing(cno):
    AuditEntry.objects.all().delete()

    update(cno, "BLS", name="icu")

    assert not AuditEntry.objects.exists()
    assert names(cno) == ["ACLS", "BLS", "ICU"]
    assert all(row["renames"] == [] for row in cno.get(SKILLS).json())


# ---- who may ---------------------------------------------------------------------------------------
@pytest.mark.parametrize("role", list(Role))
def test_every_role_reads_the_catalogue(signed_in, cno, role):
    reader = cno if role == Role.CNO else signed_in(role, username=f"a-{role}")  # The hospital has one CNO.

    assert names(reader) == ["ACLS", "BLS", "ICU"]


def test_a_stranger_reads_nothing(client, cno):
    assert client.get(SKILLS).status_code == 401


@pytest.mark.parametrize("role", [role for role in Role if role != Role.CNO])
def test_only_the_cno_changes_it(signed_in, cno, role):
    client = signed_in(role, username=f"a-{role}")
    AuditEntry.objects.all().delete()

    assert create(client, name="Preceptor").status_code == 403
    assert update(client, "ICU", name="Intensive care").status_code == 403
    assert names(cno) == ["ACLS", "BLS", "ICU"] and not AuditEntry.objects.exists()
