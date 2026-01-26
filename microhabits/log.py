import datetime

from sortedcontainers import SortedDict

STATUSES = (None, "COMPLETED", "SKIPPED", "FAILED")


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
