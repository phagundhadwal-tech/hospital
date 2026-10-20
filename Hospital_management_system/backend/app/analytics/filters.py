"""
app/analytics/filters.py
========================
Validates query-string filters once and turns them into an immutable Filters
object that the repository layer converts into bound SQL parameters.

DATE SEMANTICS
  start_date  inclusive, 00:00:00 of that day
  end_date    inclusive of the WHOLE day (implemented as  < end_date + 1 day),
              so records on the last selected day are never dropped.
  Dates are wall-clock hospital time; the data carries no time-zone offset and
  no conversion is applied anywhere.

DEPARTMENT SCOPE
  Department-scoped roles are ALWAYS restricted to the department in their JWT;
  a department_id query parameter can never widen that.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from app.config import get_settings
from app.core.exceptions import BadRequestError, ForbiddenError


@dataclass(frozen=True)
class Filters:
    start: datetime | None = None            # inclusive
    end_exclusive: datetime | None = None    # exclusive (end_date + 1 day)
    department_id: int | None = None
    visit_type: str | None = None
    visit_status: str | None = None


def _hint(fmt: str) -> str:
    """Human-readable form of a strptime format, e.g. %Y-%m-%d -> YYYY-MM-DD."""
    return fmt.replace("%Y", "YYYY").replace("%m", "MM").replace("%d", "DD")


def _parse_date(value: str | None, name: str) -> date | None:
    if value is None or value == "":
        return None
    fmt = get_settings().DATE_FORMAT
    try:
        return datetime.strptime(value, fmt).date()
    except ValueError:
        raise BadRequestError(f"{name} must be a date in {_hint(fmt)} format.") from None


def _parse_dept(value: str | int | None, what: str) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        raise BadRequestError(f"{what} must be a numeric department id.") from None


def _clean_text(value: str | None, name: str) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if value == "":
        return None
    if len(value) > get_settings().FILTER_TEXT_MAX_LENGTH:
        raise BadRequestError(f"{name} is too long.")
    return value


def build_filters(
    start_date: str | None = None,
    end_date: str | None = None,
    department_id: str | None = None,
    visit_type: str | None = None,
    visit_status: str | None = None,
    dept_scope: str | None = None,
) -> Filters:
    start = _parse_date(start_date, "start_date")
    end = _parse_date(end_date, "end_date")
    if start and end and start > end:
        raise BadRequestError("start_date must not be after end_date.")

    if dept_scope:                                   # scoped role → server decides
        try:
            dept = int(dept_scope)
        except ValueError:
            raise ForbiddenError(
                "Your account is linked to an invalid department. "
                "Ask an administrator to re-create your user (backend/data/create_demo_users.py)."
            ) from None
    else:                                            # full-access role → optional filter
        dept = _parse_dept(department_id, "department_id")

    return Filters(
        start=datetime.combine(start, datetime.min.time()) if start else None,
        end_exclusive=datetime.combine(end + timedelta(days=1), datetime.min.time()) if end else None,
        department_id=dept,
        visit_type=_clean_text(visit_type, "visit_type"),
        visit_status=_clean_text(visit_status, "visit_status"),
    )
