"""Provides functionality to determine whether a habit is due on a given date
based on various scheduling criteria (weekdays, days of month, frequency)."""

import datetime
from typing import Literal, NotRequired, Optional, TypeAlias, TypedDict

from .log import Log

DayName: TypeAlias = Literal[
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"
]


class DueCriteria(TypedDict):
    """Criteria for determining when a habit is due."""

    days_of_week: NotRequired[list[DayName]]
    days_of_month: NotRequired[list[int]]
    frequency: NotRequired[int]


type DueOn = Optional[DueCriteria]


def check_due(log: Log, due_on: DueOn, selected_day: datetime.date) -> bool:
    """Determine if a habit is due on the selected day."""
    # pylint: disable=too-many-return-statements

    # Not due if a status is set
    if log.get_status(selected_day):
        return False

    # Always due if due_on has not been specified.
    # This is equivalent to saying default frequency=1
    if due_on is None:
        return True

    # Due if the selected day of week is one of the specified days
    if due_days_of_week := due_on.get("days_of_week"):
        if selected_day.strftime("%A").lower() in due_days_of_week:
            return True

    # Due if the selected day of month is one of the specified days
    if due_days_of_month := due_on.get("days_of_month"):
        if selected_day.day in due_days_of_month:
            return True

    # Frequency specifies the space between each day until due
    if specified_frequency := due_on.get("frequency"):
        match specified_frequency:
            case 0:  # Never due if frequency=0
                return False
            case 1:
                return True
            case _:
                if "COMPLETED" in log.n_days_before(selected_day, specified_frequency):
                    return False
                return True

    return False  # If none of the cases above apply
