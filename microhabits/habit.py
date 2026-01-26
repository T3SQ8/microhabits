import datetime

from .due_checker import check_due
from .log import Log


class Habit:
    def __init__(self, name: str, due_on: dict, associated_file: str | None):
        self.name: str = name
        self.due_on: dict = due_on
        self.associated_file: str | None = associated_file
        self.hide_from_tui: bool = False
        self.log: Log = Log()

    def get_name(self) -> str:
        return self.name

    def get_file(self) -> str | None:
        return self.associated_file

    def is_due(self, date: datetime.date) -> bool:
        return check_due(self.log, self.due_on, date)
