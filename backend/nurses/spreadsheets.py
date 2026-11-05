"""CSV files as a spreadsheet will open them: with a byte order mark, so Excel reads them as UTF-8 and saves them that
way again, and with nothing a spreadsheet would run."""
from __future__ import annotations

import codecs
import csv
from collections.abc import Iterable

from django.http import HttpResponse

# What makes a spreadsheet read a cell as a formula, the full-width forms included.
_FORMULA_STARTS = ("=", "+", "-", "@", "\t", "\r", "\n", "＝", "＋", "－", "＠")


def safe_cell(value: str) -> str:
    """A leading apostrophe makes a spreadsheet show the cell as text, so a name like `=HYPERLINK(...)` stays a name."""
    return f"'{value}" if value.lstrip(" ").startswith(_FORMULA_STARTS) else value


def csv_response(filename: str, rows: Iterable[Iterable[str]]) -> HttpResponse:
    """`filename` is ours, never a person's input. Not stored, because a staff list holds names and genders."""
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response["Cache-Control"] = "no-store"
    response.write(codecs.BOM_UTF8)
    # Every cell quoted: Excel splits on its locale's list separator, so an unquoted `a;=1+1` would start a new cell.
    csv.writer(response, quoting=csv.QUOTE_ALL).writerows([safe_cell(cell) for cell in row] for row in rows)
    return response
