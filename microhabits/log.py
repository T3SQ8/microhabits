"""Completion status log for tracking habit statuses across dates."""

import datetime
from typing import Optional

from sortedcontainers import SortedDict

type Status = Optional[str]
type StatusLog = SortedDict[datetime.date, Status]

STATUSES: tuple[Status, ...] = (None, "COMPLETED", "SKIPPED", "FAILED")


class Log:
    """Stores and manages completion status records for each date."""

    def __init__(self) -> None:
        """Initialize an empty status log."""
        self.statuses: StatusLog = SortedDict()

    def set_status(self, date: datetime.date, status: Status) -> None:
        """Set the completion status for a given date."""
        self.statuses[date] = status

    def get_status(self, date: datetime.date) -> str | None:
        """Return the completion status for a given date."""
        return self.statuses.get(date)

    def next_status(self, date: datetime.date) -> None:
        """Toggle status to the next defined value."""
        status = self.get_status(date)
        i = STATUSES.index(status)
        new_status = STATUSES[(i + 1) % len(STATUSES)]
        self.set_status(date, new_status)

    def n_days_before(self, date: datetime.date, n: int) -> list[Status]:
        """Return a list of statuses for the n days preceding the given date."""
        return [self.get_status(date - datetime.timedelta(n)) for n in range(n)]
