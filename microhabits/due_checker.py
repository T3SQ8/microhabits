import datetime
from datetime import timedelta

from .log import Log


def check_due(log: Log, due_on: dict, selected_day: datetime.date) -> bool:
    # pylint: disable=too-many-return-statements

    if log.get_status(selected_day):
        return False

    if "days_of_week" in due_on:
        if selected_day.strftime("%A").lower() in due_on["days_of_week"]:
            return True

    if "days_of_month" in due_on:
        if selected_day.day in due_on["days_of_month"]:
            return True

    if "frequency" in due_on:
        freq: int = due_on["frequency"]
        match freq:
            case 0:
                return False
            case 1:
                return True
            case _:
                # go back and check as many days as specified
                # and check if any of them are completed
                for n in range(freq):
                    n_days_before = selected_day - timedelta(n)
                    if log.get_status(n_days_before) == "COMPLETED":
                        return False
                return True

    return False
