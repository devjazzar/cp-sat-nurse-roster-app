"""What a closed month holds fixed (ticket 21), what its close ends, and what each reader sees of it: opening values after a nurse's
first close, start and end dates across a month fixed for good, a shift's hours, requests still pending, a nurse's own month and
roster, and the CNO's overview."""
from __future__ import annotations

import datetime as dt

import pytest
from django.test import Client

from closing import closing
from closing.tests.test_close import JUNE, approved, at, close_view, june, june_and_july, on  # noqa: F401
from conftest import PASSWORD, post
from hospital.models import Shift
from notifications.models import Event, Notification
from notifications.reading import Names, text_of
from nurses.models import NurseProfile
from requesting.models import Request, RequestState, RequestWindow, WindowState
from rosters.tests.test_pins import change_shift
from rosters.tests.test_review import carla, ok, url  # noqa: F401

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _scene(before_june, solver):
    pass


def close_june(on):  # noqa: F811
    on(dt.date(2026, 7, 2))
    return closing.catch_up(at(dt.date(2026, 7, 2), 9))


def close_june_and_july(on):  # noqa: F811
    on(dt.date(2026, 8, 3))
    return closing.catch_up(at(dt.date(2026, 8, 3), 9))


def nurse(hospital_id) -> NurseProfile:
    return NurseProfile.objects.get(user__username=hospital_id)


def field_errors(response) -> dict:
    assert response.status_code == 422, response.content
    return {tuple(error["loc"])[-1]: error["msg"] for error in response.json()["detail"]}


class TestOpeningValues:
    def attributes(self, client, unit, hospital_id, **changes):
        row = next(row for row in ok(client.get(url(unit, "/nurses"))) if row["hospital_id"] == hospital_id)
        body = {key: row[key] for key in ("team_leader", "score", "ramadan_reduced", "breastfeeding", "ytd_overtime",
                                          "hours_balance", "night_balance", "friday_balance", "allowed_shifts")}
        return client.put(url(unit, f"/nurses/{row['id']}/attributes"), body | changes, content_type="application/json")

    def test_they_lock_after_her_first_close_on_their_fields_only(self, june, mona, er, on):  # noqa: F811
        assert self.attributes(mona, er, "Amal", hours_balance=3).status_code == 200
        close_june(on)

        errors = field_errors(self.attributes(mona, er, "Amal", hours_balance=5, ytd_overtime=9))

        assert set(errors) == {"hours_balance", "ytd_overtime"}
        assert errors["hours_balance"] == ("Amal's first month has closed, so their opening values can no longer change: each "
                                           "month now starts from the carry-over of the one before.")
        saved = ok(self.attributes(mona, er, "Amal", score=0.5))
        assert saved["score"] == 0.5 and saved["hours_balance"] == 3 and saved["opening_values_locked"] is True


class TestDates:
    def correct(self, client, hospital_id, start):
        profile = nurse(hospital_id)
        return client.put(f"/api/nurses/{profile.pk}/details", {"full_name": profile.user.full_name, "gender": profile.gender,
                                                                "start_date": start}, content_type="application/json")

    def test_a_start_date_across_a_month_fixed_for_good_is_refused(self, june_and_july, er, carla, on):  # noqa: F811
        close_june_and_july(on)

        errors = field_errors(self.correct(carla, "Dana", "2026-06-10"))

        assert errors["start_date"] == ("June 2026 has closed, and so has the month after it, so a date that changes which of "
                                        "its days Dana was present cannot be saved.")
        # July can still close again, since August has not closed, but a start date in it moves June's days too.
        assert "June 2026" in field_errors(self.correct(carla, "Dana", "2026-07-10"))["start_date"]

    def test_while_it_can_close_again_the_change_is_taken_and_the_close_says_its_facts_changed(self, june, mona, er, carla,  # noqa: F811
                                                                                                 on):
        close_june(on)

        assert self.correct(carla, "Dana", "2026-06-10").status_code == 200

        assert close_view(mona, er)["closed"]["changed_since"] is True

    def test_an_end_date_into_a_month_fixed_for_good_is_refused(self, june_and_july, carla, on):  # noqa: F811
        close_june_and_july(on)
        response = carla.put(f"/api/nurses/{nurse('Dana').pk}/end-date", {"end_date": "2026-06-20"},
                             content_type="application/json")

        assert "June 2026 has closed" in field_errors(response)["end_date"]


class TestAShiftsHours:
    def test_a_closed_month_no_longer_holds_them(self, june, carla, on):  # noqa: F811
        on(dt.date(2026, 7, 1))
        refusal = field_errors(change_shift(carla, "N", hours=10))["hours"]
        assert "ER, June 2026" in refusal

        closing.catch_up(at(dt.date(2026, 7, 1), 1))

        assert change_shift(carla, "N", hours=10).status_code == 200
        assert Shift.objects.get(code="N").hours == 10

    def test_closing_again_reads_the_hours_the_first_close_read(self, june, mona, er, carla, on):  # noqa: F811
        on(dt.date(2026, 7, 1))
        [first] = closing.catch_up(at(dt.date(2026, 7, 1), 1))
        assert change_shift(carla, "N", hours=10).status_code == 200

        again = ok(post(mona, url(er, "/close"), {"month": "2026-06"}))

        assert again["closed"]["closed_by"] == "Mona Ali"
        latest = closing.latest_close(er, JUNE)
        assert latest.input["general"]["shift_hours"]["N"] == 12
        assert latest.result["nurses"] == first.result["nurses"]


class TestRequestsStillPending:
    def test_they_expire_at_the_close_and_their_nurse_is_told(self, june, er, on):  # noqa: F811
        window = RequestWindow.objects.create(unit=er, month=JUNE, opens_on=dt.date(2026, 5, 1), closes_on=dt.date(2026, 5, 10),
                                              state=WindowState.CLOSED, created_by=er.manager)
        badr = nurse("Badr")
        waiting = Request.objects.create(window=window, nurse=badr, date=dt.date(2026, 6, 3), shift=None)
        close_june(on)

        waiting.refresh_from_db()
        assert waiting.state == RequestState.EXPIRED
        [step] = waiting.steps.filter(step="expired")
        assert (step.by, step.reason) == (None, "The month closed before a decision.")
        [note] = Notification.objects.filter(event=Event.REQUEST_DECIDED)
        assert note.user == badr.user and "by" not in note.payload
        assert text_of(note, Names([note])) == "Your request for a day off on 3 June 2026 has ended: the month closed before a decision."
        mine = ok(signed_in("Badr").get("/api/requests/mine", {"month": "2026-06"}))
        [row] = mine["requests"]
        assert row["state"] == "expired" and row["steps"][-1] == row["steps"][-1] | {"step": "expired", "by": None,
                                                                                    "reason": "The month closed before a decision."}


def signed_in(hospital_id) -> Client:
    client = Client()
    assert post(client, "/api/auth/login", {"username": hospital_id, "password": PASSWORD}).status_code == 200
    return client


class TestWhatPeopleSee:
    def test_a_nurses_own_month_shows_the_closed_figures(self, june, er, on):  # noqa: F811
        amal = signed_in("Amal")
        on(dt.date(2026, 7, 1))
        before = ok(amal.get("/api/rosters/mine/month", {"month": "2026-06"}))
        assert before["roster"] is None and before["first_month"] == "2026-07"

        [close] = closing.catch_up(at(dt.date(2026, 7, 1), 1))

        answer = ok(amal.get("/api/rosters/mine/month", {"month": "2026-06"}))
        row = close.result["nurses"]["Amal"]
        assert answer["first_month"] == "2026-06" and answer["roster"]["closed"] is True and answer["roster"]["version"] == 1
        hours = answer["roster"]["hours"]
        assert (hours["worked"], hours["leave_credit"], hours["owed"], hours["overtime"], hours["carried"]) == (
            row["hours_worked"], row["leave_credit"], row["required"], row["overtime"], row["carry_over"]["hours_balance"])
        assert {shift["code"]: shift["count"] for shift in hours["shifts"]} == {code: n for code, n in row["shifts"].items() if n}
        roster = ok(amal.get("/api/rosters/mine", {"month": "2026-06"}))
        assert roster["roster"]["version"] == 1 and roster["first_month"] == "2026-06"

    def test_the_overview_shows_closed(self, june, carla, on):  # noqa: F811
        on(dt.date(2026, 7, 1))
        assert ok(carla.get("/api/rosters/overview", {"month": "2026-06"}))["units"][0]["states"][0] == "approved"

        closing.catch_up(at(dt.date(2026, 7, 1), 1))

        assert ok(carla.get("/api/rosters/overview", {"month": "2026-06"}))["units"][0]["states"][0] == "closed"

    def test_the_manager_sees_each_nurses_carry_over_with_its_source(self, june, mona, er, on):  # noqa: F811
        view = close_view(mona, er)
        assert view["closed"] is None
        assert {row["into"]["source"] for row in view["carry_over"]} == {"opening"}
        assert {row["out"]["source"] for row in view["carry_over"]} == {"projected"}
        july = close_view(mona, er, "2026-07")
        assert {row["into"]["source"] for row in july["carry_over"]} == {"projected"}
        assert [row["into"]["hours_balance"] for row in july["carry_over"]] == [row["out"]["hours_balance"]
                                                                                for row in view["carry_over"]]

        close_june(on)

        view = close_view(mona, er)
        assert {row["out"]["source"] for row in view["carry_over"]} == {"closed"}
        assert {row["into"]["source"] for row in close_view(mona, er, "2026-07")["carry_over"]} == {"closed"}
        assert view["closed"]["version"] == 1 and view["closed"]["closed_by"] is None

    def test_what_the_facts_broke_is_listed_with_names(self, june, mona, er, on):  # noqa: F811
        on(dt.date(2026, 7, 1))
        from rosters.tests.test_review import record_leave
        for hospital_id in ("Emad",):  # Emad works the only Day on the 1st: leave leaves it uncovered.
            assert record_leave(mona, er, hospital_id, 1).status_code == 201
        closing.catch_up(at(dt.date(2026, 7, 1), 1))

        broke = close_view(mona, er)["closed"]["facts_broke"]

        assert any(row["rule"] == "headcount" and row["date"] == "2026-06-01" for row in broke)
        assert not [row for row in broke if "day " in row["text"]]

