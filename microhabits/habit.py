import datetime
from typing import Optional

from .due_checker import check_due
from .log import Log


class Habit:
    def __init__(
        self,
        name: str,
        due_on: dict,
        associated_file: Optional[str],
        alias: Optional[str],
    ):
        self.name: str = name
        self.due_on: dict = due_on
        self.associated_file: Optional[str] = associated_file
        self.hide_from_tui: bool = False
        self.log: Log = Log()
        self.alias: Optional[str] = alias

    def get_name(self) -> str:
        return self.name

    def get_alias_or_name(self) -> str:
        return self.alias or self.name

    def get_file(self) -> str | None:
        return self.associated_file

    def is_due(self, date: datetime.date) -> bool:
        return check_due(self.log, self.due_on, date)
