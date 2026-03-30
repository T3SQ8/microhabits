import datetime
from typing import Optional

from sortedcontainers import SortedDict

type Status = Optional[str]
STATUSES: tuple[Status, ...] = (None, "COMPLETED", "SKIPPED", "FAILED")


class Log:
    def __init__(self) -> None:
        self.statuses: SortedDict[datetime.date, str | None] = SortedDict()

    def set_status(self, date: datetime.date, status: str | None) -> None:
        self.statuses[date] = status

    def get_status(self, date: datetime.date) -> str | None:
        return self.statuses.get(date)

    def next_status(self, date: datetime.date) -> None:
        status = self.get_status(date)
        i = STATUSES.index(status)
        new_status = STATUSES[(i + 1) % len(STATUSES)]
        self.set_status(date, new_status)

    def n_days_before(self, date: datetime.date, n: int) -> list[Status]:
        return [self.get_status(date - datetime.timedelta(n)) for n in range(n)]
