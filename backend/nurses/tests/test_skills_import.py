"""The skills import (ticket 36): the CNO records and renews nurses' skills from a CSV of hospital ID, skill and expiry, read
as the nurse import's file is (its encodings and limits are tested in `test_files.py`, and here only that they are shared),
previewed row by row and confirmed by sending the file again."""
import codecs

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client

from accounts.models import Role, User
from audit.models import AuditEntry
from conftest import post
from hospital.models import HospitalSettings, Skill, SkillRename
from nurses import importing
from nurses.models import NurseSkill
from nurses.tests.conftest import NURSES, added
from nurses.tests.test_skills import change_skill, held, on_nurses_page, recorded

pytestmark = pytest.mark.django_db

SKILLS = "/api/hospital/skills"
TEMPLATE = f"{NURSES}/skills-import/template"
PREVIEW = f"{NURSES}/skills-import/preview"
CONFIRM = f"{NURSES}/skills-import/confirm"
HEADER = "Hospital ID,Skill,Expiry"


@pytest.fixture(autouse=True)
def today(on_day):
    on_day(2026, 11, 5)


@pytest.fixture
def catalogue(cno):
    """BLS expires and is required to work, ICU does not expire, ACLS expires."""
    for name, expires, required in [("BLS", True, True), ("ICU", False, False), ("ACLS", True, False)]:
        response = post(cno, SKILLS, {"name": name, "expires": expires, "required_to_work": required, "active": True})
        assert response.status_code == 201, response.content
    return {skill.name: str(skill.pk) for skill in Skill.objects.all()}


@pytest.fixture
def amal(cno, er, catalogue) -> str:
    return added(cno, er, "h1", full_name="Amal Saleh")["nurse"]["id"]


@pytest.fixture
def badr(cno, er, catalogue) -> str:
    return added(cno, er, "H2", full_name="Badr Omar", gender="M")["nurse"]["id"]


def rename(client, name, new_name):
    row = next(row for row in client.get(SKILLS).json() if row["name"] == name)
    body = {key: row[key] for key in ("expires", "required_to_work", "active")} | {"name": new_name}
    return client.put(f"{SKILLS}/{row['id']}", body, content_type="application/json")


def upload(content, name="skills.csv"):
    return SimpleUploadedFile(name, content.encode() if isinstance(content, str) else content, content_type="text/csv")


def csv_of(*rows) -> str:
    return "\n".join([HEADER, *rows]) + "\n"


def preview(client, content):
    return client.post(PREVIEW, {"file": upload(content)})


def previewed(client, content) -> dict:
    response = preview(client, content)
    assert response.status_code == 200, response.content
    return response.json()


def confirm(client, content, token):
    return client.post(CONFIRM, {"file": upload(content), "token": token})


def confirmed(client, content) -> dict:
    response = confirm(client, content, previewed(client, content)["token"])
    assert response.status_code == 200, response.content
    return response.json()


def problems_of(client, *rows) -> list:
    body = previewed(client, csv_of(*rows))
    assert body["token"] is None
    return [[(problem["column"], problem["message"]) for problem in row["problems"]] for row in body["rows"]]


def file_refusal(response) -> str:
    assert response.status_code == 422, response.content
    detail = response.json()["detail"]
    assert detail[0]["loc"][2:] == ["file"]
    return detail[0]["msg"]


# ---- the template ---------------------------------------------------------------------------------------------------
def test_the_template_has_the_exact_columns_and_a_byte_order_mark_for_excel(cno):
    response = cno.get(TEMPLATE)

    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/csv")
    assert 'filename="skills-import-template.csv"' in response["Content-Disposition"]
    assert response["Cache-Control"] == "no-store"
    assert response.content == codecs.BOM_UTF8 + b'"Hospital ID","Skill","Expiry"\r\n'


def test_the_template_is_read_as_a_file_with_no_skills_and_writes_no_audit_entry(cno):
    before = AuditEntry.objects.count()

    template = cno.get(TEMPLATE).content

    assert AuditEntry.objects.count() == before
    assert file_refusal(preview(cno, template)) == "This file has no skills below its first line. Add one skill per line."


def test_the_nurse_import_template_is_unchanged(cno):
    assert cno.get(f"{NURSES}/import/template").content == (
        codecs.BOM_UTF8 + b'"Hospital ID","Full name","Gender","Unit","Start date"\r\n')


@pytest.mark.parametrize("role", [role for role in Role if role != Role.CNO])
def test_only_the_cno_imports_skills(client_of, role, amal):
    other = client_of("other", role)
    content = csv_of("h1,ICU,")

    assert other.get(TEMPLATE).status_code == 403
    assert preview(other, content).status_code == 403
    assert confirm(other, content, "x").status_code == 403
    assert Client().post(PREVIEW, {"file": upload(content)}).status_code == 401
    assert not NurseSkill.objects.exists()


# ---- what a preview reports -----------------------------------------------------------------------------------------
def test_a_good_file_previews_what_each_row_does_with_a_token_and_saves_nothing(cno, amal, badr, catalogue):
    recorded(cno, amal, catalogue["BLS"], "2026-12-31")
    recorded(cno, amal, catalogue["ICU"])
    entries = AuditEntry.objects.count()

    response = preview(cno, csv_of("h1,bls,2027-12-31", "h1,ICU,", "h2,Acls,2027-03-01"))

    assert response.status_code == 200
    assert response["Cache-Control"] == "no-store"
    body = response.json()
    assert body["token"]
    assert [(r["line"], r["hospital_id"], r["full_name"], r["skill"], r["expiry"], r["change"], r["held_expiry"], r["problems"])
            for r in body["rows"]] == [
        (2, "h1", "Amal Saleh", "BLS", "2027-12-31", "renew", "2026-12-31", []),
        (3, "h1", "Amal Saleh", "ICU", "", "none", None, []),
        (4, "H2", "Badr Omar", "ACLS", "2027-03-01", "record", None, []),
    ]
    assert NurseSkill.objects.count() == 2
    assert AuditEntry.objects.count() == entries


def test_every_problem_on_every_row_is_reported_beside_its_column(cno, amal, badr, catalogue, make_user):
    change_skill(cno, "ACLS", active=False)
    make_user("chief2", Role.UNIT_MANAGER)

    assert problems_of(cno,
                       "h1,ICU,",
                       "has space,Nothing,2026-13-40",
                       "nobody,ACLS,2027-01-01",
                       "chief2,BLS,",
                       "h2,ICU,2027-01-01",
                       "h2,BLS,31/12/2027") == [
        [],
        [("hospital_id", "Use 1 to 150 letters, digits, dots, dashes and underscores."),
         ("skill", "There is no such skill. Use its name on the Skills page."),
         ("expiry", "Use a date as YYYY-MM-DD, between 1925 and 2076.")],
        [("hospital_id", "No nurse has this hospital ID. Use the one on the Nurses page."),
         ("skill", "ACLS is retired, so it can no longer be recorded or renewed.")],
        [("hospital_id", "No nurse has this hospital ID. Use the one on the Nurses page."),
         ("expiry", "BLS expires. Enter the last day it counts, as YYYY-MM-DD.")],
        [("expiry", "ICU does not expire, so leave its expiry empty.")],
        [("expiry", "Use a date as YYYY-MM-DD, between 1925 and 2076.")],
    ]


def test_a_deactivated_nurse_is_a_problem(cno, amal):
    response = cno.put(f"{NURSES}/{amal}/end-date", {"end_date": "2026-11-04"}, content_type="application/json")
    assert response.json()["is_active"] is False

    assert problems_of(cno, "h1,ICU,") == [
        [("hospital_id", "Amal Saleh is deactivated. Record their skills on the Nurses page, or remove the line.")]]


def test_a_skill_held_but_retired_cannot_be_renewed_by_file(cno, amal, catalogue):
    recorded(cno, amal, catalogue["BLS"], "2026-12-31")
    change_skill(cno, "BLS", active=False)

    assert problems_of(cno, "h1,BLS,2027-12-31") == [[("skill", "BLS is retired, so it can no longer be recorded or renewed.")]]


def test_a_former_name_is_not_a_skill(cno, amal, catalogue):
    assert rename(cno, "ICU", "Intensive care").status_code == 200
    assert SkillRename.objects.filter(old_name="ICU").exists()

    assert problems_of(cno, "h1,ICU,") == [[("skill", "There is no such skill. Use its name on the Skills page.")]]
    assert previewed(cno, csv_of("h1,intensive CARE,"))["rows"][0]["skill"] == "Intensive care"


def test_a_nurse_and_skill_twice_in_the_file_in_any_case_is_reported_on_both_lines(cno, amal, badr):
    assert problems_of(cno, "h1,BLS,2027-01-01", "h2,BLS,2027-01-01", "H1,bls,2028-01-01") == [
        [("skill", "BLS of h1 is also on line 4. Keep one line for each nurse's skill.")],
        [],
        [("skill", "BLS of h1 is also on line 2. Keep one line for each nurse's skill.")]]


def test_an_expiry_already_past_is_accepted_as_a_fact(cno, amal):
    assert previewed(cno, csv_of("h1,BLS,2025-01-31"))["token"]


def test_a_line_with_too_many_or_too_few_cells_is_reported_once_for_the_whole_line(cno, amal):
    assert problems_of(cno, "h1,BLS,2027-01-01,extra", "h1") == [
        [(None, "This line has 4 cells, not 3. Put double quotes around a skill name that has a comma in it.")],
        [(None, "This line has 1 cells, not 3. Put double quotes around a skill name that has a comma in it.")],
    ]


def test_a_nul_in_a_cell_is_a_problem_and_not_a_server_error(cno, amal):
    assert problems_of(cno, "h1,IC\x00U,") == [[("skill", "There is no such skill. Use its name on the Skills page.")]]
    assert problems_of(cno, "h\x001,ICU,")[0][0][0] == "hospital_id"


# ---- what a file may be: the nurse import's rules, shared -----------------------------------------------------------
def test_utf16_with_a_mark_is_read(cno, amal):
    assert previewed(cno, csv_of("h1,ICU,").replace("\n", "\r\n").encode("utf-16"))["token"]


def test_an_encoding_that_could_only_be_guessed_is_refused(cno, amal):
    assert "CSV UTF-8" in file_refusal(preview(cno, csv_of("h1,Réa,").encode("cp1252")))


@pytest.mark.parametrize("content, words", [
    ("", "This file is empty."),
    ("Hospital ID,Full name,Gender,Unit,Start date\nh1,Amal,F,ER,2026-01-10", "Hospital ID, Skill, Expiry"),
    ("h1,ICU,", "exactly these columns"),
], ids=["empty", "a nurse import file", "no header"])
def test_a_file_that_cannot_be_read_is_refused_as_a_whole(cno, content, words):
    assert words in file_refusal(preview(cno, content))


def test_the_row_and_size_limits_are_the_nurse_import_s(cno, amal):
    rows = ["h1,ICU,"] * importing.MAX_ROWS

    assert len(previewed(cno, csv_of(*rows))["rows"]) == importing.MAX_ROWS
    assert file_refusal(preview(cno, csv_of(*rows, "h1,ICU,"))) == (
        "This file has more than 500 skills. Split it and import each part.")
    assert file_refusal(preview(cno, f"{HEADER}\n" + " " * importing.MAX_BYTES)) == (
        "This file is larger than 1 MB, which is more than 500 skills need.")


def test_a_file_too_large_to_keep_in_memory_never_reaches_the_disk(cno, settings, monkeypatch):
    settings.FILE_UPLOAD_MAX_MEMORY_SIZE = 1000
    monkeypatch.setattr("django.core.files.uploadedfile.TemporaryUploadedFile.__init__",
                        lambda *_, **__: pytest.fail("the upload went to a temporary file"))

    assert preview(cno, f"{HEADER}\n" + "h1,ICU,\n" * 200).status_code == 422


# ---- confirming -----------------------------------------------------------------------------------------------------
def test_confirming_records_new_skills_and_renews_held_ones(cno, amal, badr, catalogue):
    recorded(cno, amal, catalogue["BLS"], "2026-12-31")
    recorded(cno, amal, catalogue["ICU"])
    first = NurseSkill.objects.get(skill__name="BLS")
    content = csv_of("h1,BLS,2027-12-31", "h1,ICU,", "h2,ACLS,2027-03-01", "h2,ICU,")

    response = confirm(cno, content, previewed(cno, content)["token"])

    assert response.status_code == 200, response.content
    assert response["Cache-Control"] == "no-store"
    assert response.json() == {"recorded": 2, "renewed": 1, "unchanged": 1}
    assert on_nurses_page(cno, "h1") == {"BLS": "2027-12-31", "ICU": None}
    assert on_nurses_page(cno, "H2") == {"ACLS": "2027-03-01", "ICU": None}
    first.refresh_from_db()
    assert first.removed_at and first.removed_by.username == "chief", "A renewal ends the row, as by hand."
    renewed = NurseSkill.objects.current().get(skill__name="BLS")
    assert renewed.recorded_by.username == "chief"


def test_a_renewal_of_a_kind_that_no_longer_expires_reads_as_it_does_by_hand(cno, amal, catalogue):
    recorded(cno, amal, catalogue["ACLS"], "2026-12-31")
    assert change_skill(cno, "ACLS", expires=False).status_code == 200

    body = previewed(cno, csv_of("h1,ACLS,"))

    assert (body["rows"][0]["change"], body["rows"][0]["held_expiry"]) == ("none", None)
    assert confirm(cno, csv_of("h1,ACLS,"), body["token"]).json() == {"recorded": 0, "renewed": 0, "unchanged": 1}
    assert NurseSkill.objects.count() == 1


def test_a_file_with_any_problem_saves_nothing_whatever_token_is_sent(cno, amal):
    good_token = previewed(cno, csv_of("h1,ICU,"))["token"]
    bad = csv_of("h1,ICU,", "h1,BLS,")

    for token in ("", "null", good_token):
        response = confirm(cno, bad, token)
        assert response.status_code == 409
        assert response.json()["token"] is None and response.json()["rows"][1]["problems"]
    assert not NurseSkill.objects.exists()
    assert not AuditEntry.objects.filter(action="nurse.skills_imported").exists()


def test_a_file_that_is_not_the_one_previewed_saves_nothing(cno, amal):
    token = previewed(cno, csv_of("h1,BLS,2027-01-01"))["token"]
    other = csv_of("h1,BLS,2027-01-02")

    response = confirm(cno, other, token)

    assert response.status_code == 409
    assert response.json()["token"] == previewed(cno, other)["token"] != token
    assert not NurseSkill.objects.exists()


def test_a_renewal_by_hand_since_the_preview_is_not_what_was_previewed(cno, amal, catalogue):
    recorded(cno, amal, catalogue["BLS"], "2026-12-31")
    content = csv_of("h1,BLS,2027-12-31")
    token = previewed(cno, content)["token"]
    assert cno.put(f"{NURSES}/{amal}/skills/{catalogue['BLS']}", {"expiry": "2027-06-30"},
                   content_type="application/json").status_code == 200

    response = confirm(cno, content, token)

    assert response.status_code == 409
    assert response.json()["rows"][0]["held_expiry"] == "2027-06-30"
    assert response.json()["token"] != token
    assert on_nurses_page(cno, "h1") == {"BLS": "2027-06-30"}


def test_a_skill_renamed_since_the_preview_is_not_what_was_previewed(cno, amal):
    content = csv_of("h1,ICU,")
    token = previewed(cno, content)["token"]
    rename(cno, "ICU", "Intensive care")

    response = confirm(cno, content, token)

    assert response.status_code == 409
    assert response.json()["rows"][0]["problems"][0]["column"] == "skill"
    assert not NurseSkill.objects.exists()


def test_a_change_after_the_first_check_is_caught_under_the_locks(cno, amal, catalogue, monkeypatch):
    """Something done between the check outside the transaction and the locks, as nothing else could arrange. It is done
    inside the confirm's transaction, so the refusal's rollback undoes it too: what is left to see is that nothing was saved."""
    content = csv_of("h1,ICU,")
    token = previewed(cno, content)["token"]
    real = HospitalSettings.load

    def load_after_a_deactivation(*args, **kwargs):
        User.objects.filter(username="h1").update(is_active=False)
        return real(*args, **kwargs)
    monkeypatch.setattr("nurses.files_api.HospitalSettings.load", load_after_a_deactivation)

    response = confirm(cno, content, token)

    assert response.status_code == 409
    assert not NurseSkill.objects.exists()
    assert not AuditEntry.objects.filter(action="nurse.skills_imported").exists()


def test_confirming_twice_changes_nothing_more(cno, amal):
    content = csv_of("h1,BLS,2027-01-01")
    token = previewed(cno, content)["token"]
    assert confirm(cno, content, token).status_code == 200

    response = confirm(cno, content, token)

    assert response.status_code == 409
    assert response.json()["rows"][0]["change"] == "none"
    assert NurseSkill.objects.count() == 1


def test_a_failure_on_the_last_row_undoes_the_first(cno, amal, badr, monkeypatch):
    content = csv_of("h1,ICU,", "h2,ICU,")
    token = previewed(cno, content)["token"]
    real = NurseSkill.objects.create

    def fail_on_second(**fields):
        if fields["nurse"].user.username == "H2":
            raise RuntimeError("the database went away")
        return real(**fields)
    monkeypatch.setattr(NurseSkill.objects, "create", fail_on_second)

    cno.raise_request_exception = False
    assert confirm(cno, content, token).status_code == 500
    assert not NurseSkill.objects.exists()
    assert not AuditEntry.objects.filter(action__startswith="nurse.skills").exists()


def test_a_cno_deactivated_since_the_preview_changes_nothing(cno, amal):
    content = csv_of("h1,ICU,")
    token = previewed(cno, content)["token"]
    User.objects.filter(username="chief").update(is_active=False)

    assert confirm(cno, content, token).status_code in (401, 403)
    assert not NurseSkill.objects.exists()


# ---- what stays behind ----------------------------------------------------------------------------------------------
def test_an_import_is_audited_as_who_and_how_many_rows_and_nothing_from_the_file(cno, amal, badr, catalogue):
    recorded(cno, amal, catalogue["ICU"])
    AuditEntry.objects.all().delete()

    confirmed(cno, csv_of("h1,ICU,", "h1,BLS,2027-12-31", "h2,ACLS,2027-03-01"))

    summary = AuditEntry.objects.get(action="nurse.skills_imported")
    assert summary.actor.username == "chief"
    assert (summary.target, summary.before, summary.after) == ("", None, {"count": 3})
    # Each nurse whose skills changed, as a change by hand says it: whose, by whom, never which skill or date.
    changed = AuditEntry.objects.filter(action="nurse.skills_changed")
    assert sorted(changed.values_list("target", flat=True)) == ["H2", "h1"]
    assert all((entry.before, entry.after) == (None, None) for entry in changed)
    everything = str(list(AuditEntry.objects.values_list("target", "before", "after")))
    for word in ("BLS", "ICU", "ACLS", "2027"):
        assert word not in everything


def test_a_preview_and_a_refused_confirm_write_no_audit_entry(cno, amal):
    before = AuditEntry.objects.count()

    previewed(cno, csv_of("h1,ICU,"))
    confirm(cno, csv_of("h1,ICU,"), "wrong")

    assert AuditEntry.objects.count() == before


def test_a_file_that_changes_nothing_is_still_audited_and_names_no_nurse(cno, amal, catalogue):
    recorded(cno, amal, catalogue["ICU"])
    AuditEntry.objects.all().delete()

    assert confirmed(cno, csv_of("h1,ICU,")) == {"recorded": 0, "renewed": 0, "unchanged": 1}

    assert list(AuditEntry.objects.values_list("action", flat=True)) == ["nurse.skills_imported"]


def test_the_staff_list_holds_no_skills(cno, amal):
    confirmed(cno, csv_of("h1,BLS,2027-01-01"))

    content = cno.get(f"{NURSES}/export").content.decode("utf-8-sig")

    assert content.splitlines()[0] == ('"Hospital ID","Full name","Gender","Unit","Start date","End date","Role","Status",'
                                       '"Transfers to come"')
    assert "BLS" not in content and "2027-01-01" not in content


def test_skills_imported_show_where_the_nurse_s_skills_are_read(cno, amal):
    confirmed(cno, csv_of("h1,BLS,2027-01-01", "h1,ICU,"))

    assert held(cno.get(NURSES).json()[0]["skills"]) == {"BLS": "2027-01-01", "ICU": None}
