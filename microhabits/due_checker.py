import datetime
from typing import Literal, Optional, TypeAlias, TypedDict

from .log import Log

DayName: TypeAlias = Literal[
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"
]


class DueFrequency(TypedDict):
    frequency: int


class DueDayOfWeek(TypedDict):
    days_of_week: list[DayName]


class DueDayOfMonth(TypedDict):
    days_of_month: list[int]


DueOn: TypeAlias = Optional[DueFrequency | DueDayOfWeek | DueDayOfMonth]


def check_due(log: Log, due_on: DueOn, selected_day: datetime.date) -> bool:
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
