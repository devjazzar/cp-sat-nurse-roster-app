"""Judging every row of a skills import file, against the rules recording or renewing one skill holds (`nurses.skills_api`).
The file is read as every import's is (`nurses.importing.read_file`); nothing here saves anything: `nurses.files_api` does,
after judging the file again under the locks a skill write takes.

A row for a skill the nurse does not hold records it; one for a skill she holds sets its expiry, a renewal; one that says
what is already recorded changes nothing. Confirming is quick (no passwords), so it is one short request."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
from dataclasses import dataclass, field
from enum import StrEnum

from uuid import UUID

from django.db.models.functions import Lower
from pydantic import TypeAdapter

from hospital.catalogue_api import FIRST_YEAR, LAST_YEAR, IsoDate
from hospital.models import Skill
from nurses.importing import HOSPITAL_ID, Layout, Line, Problem, parsed, wrong_cell_count
from nurses.models import NurseProfile, NurseSkill
from nurses.skills import counted_expiry, problems_with

COLUMNS = ("Hospital ID", "Skill", "Expiry")
SKILLS_FILE = Layout(COLUMNS, "skill", "skills", "", "a skill name that has a comma in it")

_EXPIRY = TypeAdapter(IsoDate)


class SkillImportChange(StrEnum):
    """What confirming does with a row that has no problem."""
    RECORD = "record"
    RENEW = "renew"
    NONE = "none"


@dataclass(frozen=True)
class RowMeaning:
    """What a row means when there is no problem with it."""
    nurse: NurseProfile
    skill: Skill
    expiry: dt.date | None
    held: NurseSkill | None  # Her current record of the skill, which a renewal ends.

    @property
    def change(self) -> SkillImportChange:
        if self.held is None:
            return SkillImportChange.RECORD
        return SkillImportChange.NONE if counted_expiry(self.held) == self.expiry else SkillImportChange.RENEW


@dataclass
class Row:
    """What the file says, for the page to show, and what it means when there is no problem with it."""
    line: int
    hospital_id: str = ""
    skill: str = ""
    expiry: str = ""
    full_name: str = ""
    problems: list[Problem] = field(default_factory=list)
    meaning: RowMeaning | None = None

    @property
    def change(self) -> SkillImportChange | None:
        return self.meaning.change if self.meaning else None

    @property
    def held_expiry(self) -> dt.date | None:
        return counted_expiry(self.meaning.held) if self.meaning and self.meaning.held else None


@dataclass(frozen=True)
class Preview:
    rows: list[Row]
    token: str | None  # None when any row has a problem, so there is nothing to confirm.


@dataclass(frozen=True)
class _Standing:
    """What a row is judged against: the file's other lines and the database as it is now."""
    lines_by_key: dict[tuple[str, str], list[int]]
    nurses: dict[str, NurseProfile]  # By hospital ID in lower case.
    skills: dict[str, Skill]  # By name in lower case: unique in any case of letters.
    held: dict[tuple[UUID, UUID], NurseSkill]  # By (nurse, skill).


def _key(line: Line) -> tuple[str, str] | None:
    """The nurse and skill a line names, in lower case, when it can name one."""
    if wrong_cell_count(line, SKILLS_FILE):
        return None
    hospital_id, skill = parsed(HOSPITAL_ID, line.cells[0].strip()), line.cells[1].strip()
    return (hospital_id.lower(), skill.lower()) if hospital_id and skill else None


def _judged(line: Line, standing: _Standing) -> Row:
    if problem := wrong_cell_count(line, SKILLS_FILE):
        row = Row(line.number, *(line.cells + [""] * len(COLUMNS))[:len(COLUMNS)])
        row.problems.append(problem)
        return row
    row = Row(line.number, *(cell.strip() for cell in line.cells))  # `Row`'s first fields are in the order of `COLUMNS`.

    nurse = None
    hospital_id = parsed(HOSPITAL_ID, row.hospital_id)
    if hospital_id is None:
        row.problems.append(Problem("hospital_id", "Use 1 to 150 letters, digits, dots, dashes and underscores."))
    else:
        nurse = standing.nurses.get(hospital_id.lower())
        if nurse is None:
            row.problems.append(Problem("hospital_id", "No nurse has this hospital ID. Use the one on the Nurses page."))
        else:
            row.hospital_id, row.full_name = nurse.user.username, nurse.user.full_name
            if not nurse.user.is_active:
                row.problems.append(Problem("hospital_id", f"{row.full_name} is deactivated. Record their skills on the Nurses "
                                                           "page, or remove the line."))

    skill = standing.skills.get(row.skill.lower()) if row.skill and "\x00" not in row.skill else None
    if skill is None:
        row.problems.append(Problem("skill", "There is no such skill. Use its name on the Skills page."))
    else:
        row.skill = skill.name
        if not skill.active:
            row.problems.append(Problem("skill", f"{skill.name} is retired, so it can no longer be recorded or renewed."))
    key = _key(line)
    others = [number for number in standing.lines_by_key.get(key, []) if number != row.line] if key else []
    if others:
        row.problems.append(Problem("skill", f"{row.skill} of {row.hospital_id} is also on line {others[0]}. "
                                             "Keep one line for each nurse's skill."))

    expiry = parsed(_EXPIRY, row.expiry) if row.expiry else None
    if skill is not None and not skill.expires and row.expiry:
        row.problems.append(Problem("expiry", f"{skill.name} does not expire, so leave its expiry empty."))
    elif row.expiry and expiry is None:
        row.problems.append(Problem("expiry", f"Use a date as YYYY-MM-DD, between {FIRST_YEAR} and {LAST_YEAR}."))
    elif skill is not None and skill.expires and not row.expiry:
        row.problems.append(Problem("expiry", f"{skill.name} expires. Enter the last day it counts, as YYYY-MM-DD."))

    if not row.problems:
        held = standing.held.get((nurse.pk, skill.pk))
        # The file has no identifier or issue date yet (ticket 60): a renewal carries the record's, as the API's does, and a
        # licence, which needs its identifier, is recorded on the Nurses page.
        found = problems_with(nurse, skill, expiry, held.identifier if held else None, held.issue_date if held else None)
        for field, words in found:
            if field == "identifier":
                row.problems.append(Problem("skill", f"{words} Record it on the Nurses page, or remove the line."))
            else:
                row.problems.append(Problem("expiry", f"{words} The one recorded is {held.issue_date.isoformat()}."))
        if not found:
            row.meaning = RowMeaning(nurse, skill, expiry, held)
    return row


def _token(rows: list[Row]) -> str:
    """Stands for what these rows mean right now: the nurse, the skill with its name and kind, the expiry, and the record a
    renewal would end, so that a renewal by hand since the preview, or a skill renamed, is a different preview."""
    meant = [(str(row.meaning.nurse.pk), row.meaning.nurse.user.username, str(row.meaning.skill.pk), row.meaning.skill.name,
              row.meaning.skill.expires, row.meaning.expiry.isoformat() if row.meaning.expiry else None,
              str(row.meaning.held.pk) if row.meaning.held else None) for row in rows]
    return hashlib.sha256(json.dumps(meant).encode()).hexdigest()


def nurse_ids(lines: list[Line]) -> set[str]:
    """Each possible hospital ID in the file, in lower case. Only possible ones, as the database is asked about these and
    cannot take a NUL."""
    return {hospital_id.lower() for line in lines if not wrong_cell_count(line, SKILLS_FILE)
            if (hospital_id := parsed(HOSPITAL_ID, line.cells[0].strip()))}


def nurses_named(lines: list[Line]):
    """The nurse profiles the file names, in any case of letters."""
    return (NurseProfile.objects.annotate(lowered=Lower("user__username"))
            .filter(lowered__in=nurse_ids(lines)))


def check(lines: list[Line]) -> Preview:
    """Every row's problems as things stand. It writes nothing and holds no lock."""
    by_key: dict[tuple[str, str], list[int]] = {}
    for line in lines:
        if key := _key(line):
            by_key.setdefault(key, []).append(line.number)
    nurses = {nurse.user.username.lower(): nurse for nurse in nurses_named(lines).select_related("user")}
    skills = {skill.name.lower(): skill for skill in Skill.objects.all()}
    held = {(row.nurse_id, row.skill_id): row
            for row in NurseSkill.objects.current().filter(nurse__in=nurses.values()).select_related("skill")}
    standing = _Standing(by_key, nurses, skills, held)
    rows = [_judged(line, standing) for line in lines]
    return Preview(rows, None if any(row.problems for row in rows) else _token(rows))
