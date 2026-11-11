"""A nurse's skills (ticket 33): the CNO records, renews and takes them off; her unit manager (and the manager of a unit she is
due to join) and the Deputy CNO read them; she reads her own; the System Admin never does, and the audit log says only whose
changed and by whom. Today is held still, in November 2026."""

import pytest
from django.db import IntegrityError, transaction
from django.test import Client

from accounts.models import Role, User
from audit.models import AuditEntry
from conftest import PASSWORD, post
from hospital.models import Skill
from nurses.models import NurseProfile, NurseSkill
from nurses.tests.conftest import NURSES, added, make_unit

pytestmark = pytest.mark.django_db

SKILLS = "/api/hospital/skills"


@pytest.fixture(autouse=True)
def today(on_day):
    on_day(2026, 11, 5)


@pytest.fixture
def catalogue(cno):
    """BLS expires and is required to work, ICU does not expire, ACLS expires."""
    for name, expires, required in [("BLS", True, True), ("ICU", False, False), ("ACLS", True, False)]:
        response = post(cno, SKILLS, {"name": name, "expires": expires, "required_to_work": required,
                                     "lets_a_nurse_precept": False, "active": True})
        assert response.status_code == 201, response.content
    return {skill.name: str(skill.pk) for skill in Skill.objects.all()}


@pytest.fixture
def mona(client_of):
    return client_of("mona", Role.UNIT_MANAGER)


@pytest.fixture
def omar(client_of):
    return client_of("omar", Role.UNIT_MANAGER)


@pytest.fixture
def deputy(client_of):
    return client_of("hala", Role.DEPUTY_CNO)


@pytest.fixture
def admin(client_of):
    return client_of("it", Role.SYSTEM_ADMIN)


@pytest.fixture
def er(mona):
    return make_unit("ER", User.objects.get(username="mona"))


@pytest.fixture
def icu(omar):
    return make_unit("ICU", User.objects.get(username="omar"))


@pytest.fixture
def amal(cno, er, catalogue) -> str:
    return added(cno, er)["nurse"]["id"]


def record(client, nurse_id, skill_id, expiry=None):
    return post(client, f"{NURSES}/{nurse_id}/skills", {"skill_id": skill_id, "expiry": expiry})


def recorded(client, nurse_id, skill_id, expiry=None) -> list[dict]:
    response = record(client, nurse_id, skill_id, expiry)
    assert response.status_code == 201, response.content
    return response.json()


def renew(client, nurse_id, skill_id, expiry):
    return client.put(f"{NURSES}/{nurse_id}/skills/{skill_id}", {"expiry": expiry}, content_type="application/json")


def remove(client, nurse_id, skill_id):
    return post(client, f"{NURSES}/{nurse_id}/skills/{skill_id}/remove", {})


def held(rows: list[dict]) -> dict[str, str | None]:
    return {row["name"]: row["expiry"] for row in rows}


def on_nurses_page(client, hospital_id="h123") -> dict:
    response = client.get(NURSES)
    assert response.status_code == 200, response.content
    return held(next(row for row in response.json() if row["hospital_id"] == hospital_id)["skills"])


def on_attributes_page(client, unit, hospital_id="h123") -> dict:
    response = client.get(f"/api/units/{unit.pk}/nurses")
    assert response.status_code == 200, response.content
    return held(next(row for row in response.json() if row["hospital_id"] == hospital_id)["skills"])


def my_skills(client) -> list[dict]:
    response = client.get(f"{NURSES}/my-skills")
    assert response.status_code == 200, response.content
    return response.json()


def signed_in_as(username="h123") -> Client:
    user = User.objects.get(username=username)
    user.set_password(PASSWORD)
    user.must_change_password = False
    user.save()
    client = Client()
    assert post(client, "/api/auth/login", {"username": username, "password": PASSWORD}).status_code == 200
    return client


def refusal(response) -> tuple[str, str]:
    assert response.status_code == 422, response.content
    error = response.json()["detail"][0]
    return error["loc"][2], error["msg"]


def change_skill(client, name, **changes):
    row = next(row for row in client.get(SKILLS).json() if row["name"] == name)
    body = {key: row[key] for key in ("name", "expires", "required_to_work", "lets_a_nurse_precept", "active")} | changes
    return client.put(f"{SKILLS}/{row['id']}", body, content_type="application/json")


def transfer(client, nurse_id, unit, month):
    response = post(client, f"{NURSES}/{nurse_id}/transfer", {"unit_id": str(unit.pk), "from_month": month})
    assert response.status_code == 200, response.content


# ---- the row --------------------------------------------------------------------------------------
def test_the_cno_records_a_skill_with_its_expiry_and_one_without(cno, amal, catalogue):
    recorded(cno, amal, catalogue["BLS"], "2027-06-30")
    rows = recorded(cno, amal, catalogue["ICU"])

    assert rows == [
        {"skill_id": catalogue["BLS"], "name": "BLS", "expires": True, "required_to_work": True, "active": True,
         "expiry": "2027-06-30"},
        {"skill_id": catalogue["ICU"], "name": "ICU", "expires": False, "required_to_work": False, "active": True,
         "expiry": None},
    ]
    row = NurseSkill.objects.get(skill__name="BLS")
    assert row.recorded_by.username == "chief" and row.recorded_at is not None
    assert row.removed_by is None and row.removed_at is None


def test_an_expiry_already_past_is_recorded_as_it_is(cno, amal, catalogue):
    # An expired certificate is a fact the solver needs (ADR 0010), not a mistake.
    assert held(recorded(cno, amal, catalogue["BLS"], "2026-10-31")) == {"BLS": "2026-10-31"}


def test_renewing_ends_the_row_and_begins_another(cno, amal, catalogue):
    recorded(cno, amal, catalogue["BLS"], "2026-12-31")

    response = renew(cno, amal, catalogue["BLS"], "2028-12-31")

    assert response.status_code == 200, response.content
    assert held(response.json()) == {"BLS": "2028-12-31"}
    rows = NurseSkill.objects.filter(skill__name="BLS").order_by("recorded_at", "id")
    assert [(row.expiry.isoformat(), row.removed_at is not None) for row in rows] == [
        ("2026-12-31", True), ("2028-12-31", False)]
    assert rows[0].removed_by.username == "chief"


def test_renewing_to_the_same_date_changes_nothing_and_logs_nothing(cno, amal, catalogue):
    recorded(cno, amal, catalogue["BLS"], "2026-12-31")

    assert renew(cno, amal, catalogue["BLS"], "2026-12-31").status_code == 200

    assert NurseSkill.objects.count() == 1
    assert AuditEntry.objects.filter(action="nurse.skills_changed").count() == 1


def test_taking_a_skill_off_ends_the_row_and_keeps_it(cno, amal, catalogue):
    recorded(cno, amal, catalogue["BLS"], "2026-12-31")
    recorded(cno, amal, catalogue["ICU"])

    response = remove(cno, amal, catalogue["BLS"])

    assert response.status_code == 200, response.content
    assert held(response.json()) == {"ICU": None}
    row = NurseSkill.objects.get(skill__name="BLS")
    assert row.removed_at is not None and row.removed_by.username == "chief"


def test_a_skill_taken_off_can_be_recorded_again(cno, amal, catalogue):
    recorded(cno, amal, catalogue["ICU"])
    remove(cno, amal, catalogue["ICU"])

    assert held(recorded(cno, amal, catalogue["ICU"])) == {"ICU": None}
    assert NurseSkill.objects.count() == 2


def test_at_most_one_current_row_a_nurse_and_skill(cno, amal, catalogue):
    recorded(cno, amal, catalogue["ICU"])
    row = NurseSkill.objects.get()

    with pytest.raises(IntegrityError), transaction.atomic():
        NurseSkill.objects.create(nurse=row.nurse, skill=row.skill, recorded_by=row.recorded_by)


# ---- refusals -------------------------------------------------------------------------------------
def test_a_skill_she_already_holds_is_refused_naming_what_to_do(cno, amal, catalogue):
    recorded(cno, amal, catalogue["ICU"])

    assert refusal(record(cno, amal, catalogue["ICU"])) == (
        "skill_id", "Amal Saleh already holds ICU. Change or take off the one recorded.")


def test_an_expiring_kind_without_an_expiry_is_refused(cno, amal, catalogue):
    assert refusal(record(cno, amal, catalogue["BLS"])) == ("expiry", "BLS expires. Enter the last day it counts.")
    assert not NurseSkill.objects.exists()


def test_renewing_an_expiring_kind_to_no_expiry_is_refused(cno, amal, catalogue):
    recorded(cno, amal, catalogue["BLS"], "2026-12-31")

    assert refusal(renew(cno, amal, catalogue["BLS"], None)) == ("expiry", "BLS expires. Enter the last day it counts.")


def test_a_non_expiring_kind_with_an_expiry_is_refused(cno, amal, catalogue):
    assert refusal(record(cno, amal, catalogue["ICU"], "2027-01-01")) == ("expiry", "ICU does not expire, so it takes no expiry.")
    recorded(cno, amal, catalogue["ICU"])
    assert refusal(renew(cno, amal, catalogue["ICU"], "2027-01-01")) == ("expiry", "ICU does not expire, so it takes no expiry.")


def test_a_retired_skill_can_be_neither_recorded_nor_renewed_but_its_record_stays(cno, amal, catalogue):
    recorded(cno, amal, catalogue["BLS"], "2026-12-31")
    assert change_skill(cno, "BLS", active=False).status_code == 200
    assert change_skill(cno, "ACLS", active=False).status_code == 200

    assert refusal(record(cno, amal, catalogue["ACLS"], "2027-01-01")) == (
        "skill_id", "ACLS is retired, so it can no longer be recorded.")
    assert refusal(renew(cno, amal, catalogue["BLS"], "2027-12-31")) == (
        "expiry", "BLS is retired, so it can no longer be renewed.")
    rows = on_nurses_page(cno)
    assert rows == {"BLS": "2026-12-31"}
    assert remove(cno, amal, catalogue["BLS"]).status_code == 200, "A record made in error still comes off."


def test_an_unknown_skill_is_refused(cno, amal):
    assert refusal(record(cno, amal, "0190d6b6-0000-7000-8000-000000000000")) == ("skill_id", "Choose a skill from the list.")


def test_an_unknown_nurse_is_404(cno, catalogue):
    assert record(cno, "0190d6b6-0000-7000-8000-000000000000", catalogue["ICU"]).status_code == 404


def test_renewing_or_removing_a_skill_she_does_not_hold_is_a_409(cno, amal, catalogue):
    """Her page is out of date: someone took it off since it opened."""
    assert renew(cno, amal, catalogue["BLS"], "2027-01-01").status_code == 409
    assert remove(cno, amal, catalogue["ICU"]).status_code == 409


def test_what_is_not_a_date_is_refused_beside_its_field(cno, amal, catalogue):
    assert refusal(record(cno, amal, catalogue["BLS"], "2027-02-30"))[0] == "expiry"


# ---- who writes -----------------------------------------------------------------------------------
def test_only_the_cno_writes(cno, mona, deputy, admin, amal, catalogue):
    recorded(cno, amal, catalogue["ICU"])
    nurse = signed_in_as()

    for client in (mona, deputy, admin, nurse):
        assert record(client, amal, catalogue["BLS"], "2027-01-01").status_code == 403
        assert renew(client, amal, catalogue["ICU"], None).status_code == 403
        assert remove(client, amal, catalogue["ICU"]).status_code == 403
    assert on_nurses_page(cno) == {"ICU": None}


def test_a_manager_with_a_nurse_profile_has_skills_the_cno_sets(cno, mona, er, catalogue):
    response = post(cno, f"{NURSES}/managers", {"user_id": str(User.objects.get(username="mona").pk), "gender": "F",
                                                "unit_id": str(er.pk), "start_date": "2026-01-10"})
    assert response.status_code == 201, response.content
    profile = response.json()["id"]

    assert record(mona, profile, catalogue["ICU"]).status_code == 403, "Not even their own."
    recorded(cno, profile, catalogue["ICU"])

    assert held(my_skills(mona)) == {"ICU": None}
    assert on_nurses_page(mona, "mona") == {"ICU": None}


# ---- who reads ------------------------------------------------------------------------------------
def test_the_cno_reads_every_nurses_skills_on_the_nurses_page(cno, er, icu, amal, catalogue):
    other = added(cno, icu, "h456", full_name="Badr Ali")["nurse"]["id"]
    recorded(cno, amal, catalogue["BLS"], "2027-06-30")
    recorded(cno, other, catalogue["ICU"])

    assert on_nurses_page(cno, "h123") == {"BLS": "2027-06-30"}
    assert on_nurses_page(cno, "h456") == {"ICU": None}


def test_the_list_names_skills_in_alphabetical_order(cno, amal, catalogue):
    for name in ("ICU", "ACLS", "BLS"):
        recorded(cno, amal, catalogue[name], None if name == "ICU" else "2027-01-01")

    response = cno.get(NURSES)

    assert [row["name"] for row in response.json()[0]["skills"]] == ["ACLS", "BLS", "ICU"]


def test_her_unit_manager_reads_them_and_another_unit_manager_does_not(cno, mona, omar, er, icu, amal, catalogue):
    recorded(cno, amal, catalogue["BLS"], "2027-06-30")

    assert on_nurses_page(mona) == {"BLS": "2027-06-30"}
    assert on_attributes_page(mona, er) == {"BLS": "2027-06-30"}
    assert all(row["hospital_id"] != "h123" for row in omar.get(NURSES).json())
    assert omar.get(f"/api/units/{er.pk}/nurses").status_code == 403


def test_the_deputy_cno_reads_any_units_and_never_on_the_nurses_page(cno, deputy, er, icu, amal, catalogue):
    other = added(cno, icu, "h456", full_name="Badr Ali")["nurse"]["id"]
    recorded(cno, amal, catalogue["BLS"], "2027-06-30")
    recorded(cno, other, catalogue["ICU"])

    assert on_attributes_page(deputy, er) == {"BLS": "2027-06-30"}
    assert on_attributes_page(deputy, icu, "h456") == {"ICU": None}
    assert deputy.get(NURSES).status_code == 403


def test_a_nurse_reads_her_own_and_nothing_of_a_colleagues(cno, er, amal, catalogue):
    colleague = added(cno, er, "h456", full_name="Badr Ali")["nurse"]["id"]
    recorded(cno, amal, catalogue["BLS"], "2027-06-30")
    recorded(cno, colleague, catalogue["ICU"])
    nurse = signed_in_as()

    assert my_skills(nurse) == [{"skill_id": catalogue["BLS"], "name": "BLS", "expires": True, "required_to_work": True,
                                 "active": True, "expiry": "2027-06-30"}]
    assert held(nurse.get(f"{NURSES}/my-skills", {"nurse_id": colleague}).json()) == {"BLS": "2027-06-30"}, "Takes no nurse."
    for path in (NURSES, f"/api/units/{NurseProfile.objects.get(pk=amal).placements.get().unit_id}/nurses"):
        assert nurse.get(path).status_code == 403


def test_a_manager_with_no_profile_simply_has_no_skills_of_their_own(mona, er):
    assert my_skills(mona) == []


def test_the_system_admin_reads_them_nowhere(cno, admin, er, amal, catalogue):
    recorded(cno, amal, catalogue["BLS"], "2027-06-30")

    assert admin.get(f"{NURSES}/my-skills").status_code == 403
    assert admin.get(NURSES).status_code == 403
    assert admin.get(f"/api/units/{er.pk}/nurses").status_code == 403


def test_a_stranger_is_401(amal, catalogue):
    assert Client().get(f"{NURSES}/my-skills").status_code == 401
    assert record(Client(), amal, catalogue["ICU"]).status_code == 401


# ---- a transfer, a deactivation ---------------------------------------------------------------------
def test_they_follow_her_across_a_transfer(cno, mona, omar, er, icu, amal, catalogue, on_day):
    recorded(cno, amal, catalogue["BLS"], "2027-06-30")
    transfer(cno, amal, icu, "2027-01")

    assert on_nurses_page(omar) == {"BLS": "2027-06-30"}, "The manager of a unit she is due to join reads them."
    assert on_attributes_page(omar, icu) == {"BLS": "2027-06-30"}
    assert on_nurses_page(mona) == {"BLS": "2027-06-30"}, "Hers until she leaves."

    on_day(2027, 1, 2)

    assert on_nurses_page(omar) == {"BLS": "2027-06-30"}
    assert all(row["hospital_id"] != "h123" for row in mona.get(NURSES).json())
    assert held(my_skills(signed_in_as())) == {"BLS": "2027-06-30"}
    assert NurseSkill.objects.count() == 1, "Recorded once, about the person."


def test_they_stay_when_she_is_deactivated_or_ends(cno, mona, er, amal, catalogue):
    recorded(cno, amal, catalogue["BLS"], "2027-06-30")
    response = cno.put(f"{NURSES}/{amal}/end-date", {"end_date": "2026-11-04"}, content_type="application/json")
    assert response.status_code == 200 and response.json()["is_active"] is False

    assert on_nurses_page(cno) == {"BLS": "2027-06-30"}
    assert NurseSkill.objects.current().count() == 1
    # A returning nurse has her record, and the CNO may keep it up to date meanwhile.
    assert renew(cno, amal, catalogue["BLS"], "2028-06-30").status_code == 200
    assert cno.put(f"{NURSES}/{amal}/end-date", {"end_date": None}, content_type="application/json").status_code == 200
    assert held(my_skills(signed_in_as())) == {"BLS": "2028-06-30"}


# ---- the catalogue's "expires" ---------------------------------------------------------------------
def test_turning_expires_on_is_refused_while_a_record_has_no_expiry_naming_the_nurses(cno, er, amal, catalogue):
    badr = added(cno, er, "h456", full_name="Badr Ali")["nurse"]["id"]
    recorded(cno, amal, catalogue["ICU"])
    recorded(cno, badr, catalogue["ICU"])

    response = change_skill(cno, "ICU", expires=True)

    assert refusal(response) == ("expires", "Amal Saleh and Badr Ali hold ICU with no expiry. "
                                            "Take it off them first, then record it again with its expiry.")
    assert Skill.objects.get(name="ICU").expires is False
    assert not AuditEntry.objects.filter(action="skill.changed").exists()


def test_the_refusal_names_a_few_and_counts_the_rest(cno, er, catalogue):
    for number in range(5):
        nurse = added(cno, er, f"h{number}", full_name=f"Nurse {number}")["nurse"]["id"]
        recorded(cno, nurse, catalogue["ICU"])

    assert refusal(change_skill(cno, "ICU", expires=True))[1].startswith("Nurse 0, Nurse 1, Nurse 2 and 2 more hold ICU")


def test_a_record_taken_off_does_not_stand_in_the_way(cno, amal, catalogue):
    recorded(cno, amal, catalogue["ICU"])
    remove(cno, amal, catalogue["ICU"])

    assert change_skill(cno, "ICU", expires=True).status_code == 200


def test_off_again_is_allowed_and_the_dates_kept(cno, amal, catalogue):
    recorded(cno, amal, catalogue["BLS"], "2027-06-30")

    assert change_skill(cno, "BLS", expires=False).status_code == 200
    assert on_nurses_page(cno) == {"BLS": None}, "A date kept counts for nothing while the kind does not expire."
    assert renew(cno, amal, catalogue["BLS"], None).status_code == 200
    assert NurseSkill.objects.count() == 1, "Saving it as it reads changes nothing."

    assert change_skill(cno, "BLS", expires=True).status_code == 200, "Every record still has its date."
    assert on_nurses_page(cno) == {"BLS": "2027-06-30"}


def test_the_catalogues_update_is_logged_as_skill_changed(cno, catalogue):
    change_skill(cno, "ICU", required_to_work=True)

    assert AuditEntry.objects.filter(action="skill.changed", target="ICU").count() == 1
    assert not AuditEntry.objects.filter(action="skill.updated").exists()


# ---- the audit log --------------------------------------------------------------------------------
def test_the_log_says_whose_and_by_whom_and_nothing_more(cno, admin, amal, catalogue):
    recorded(cno, amal, catalogue["BLS"], "2027-06-30")
    renew(cno, amal, catalogue["BLS"], "2028-06-30")
    remove(cno, amal, catalogue["BLS"])

    entries = AuditEntry.objects.filter(action="nurse.skills_changed").order_by("id")

    assert [(entry.actor.username, entry.target) for entry in entries] == [("chief", "h123")] * 3
    assert all(entry.before is None and entry.after is None for entry in entries)
    response = admin.get("/api/audit/entries", {"action": "nurse.skills_changed"})
    assert response.status_code == 200, response.content
    text = response.content.decode()
    assert text.count('"nurse.skills_changed"') == 3
    for leaked in ("BLS", "2027-06-30", "2028-06-30", '"expiry"', '"skill'):
        assert leaked not in text, leaked


def test_a_refused_write_logs_nothing(cno, amal, catalogue):
    record(cno, amal, catalogue["BLS"])
    record(cno, amal, catalogue["ICU"], "2027-01-01")

    assert not AuditEntry.objects.filter(action="nurse.skills_changed").exists()
