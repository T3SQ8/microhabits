"""Habit data model and core operations."""

import datetime
from dataclasses import dataclass, field
from typing import Optional

from .due_checker import DueOn, check_due
from .log import Log, Status


@dataclass
class Habit:
    """Represents a trackable habit with scheduling and completion data."""

    name: str
    due_on: DueOn
    associated_file: Optional[str] = None
    alias: Optional[str] = None
    log: Log = field(default_factory=Log)
    hide_from_tui: bool = False

    def get_name(self) -> str:
        """Return name of the habit."""
        return self.name

    def get_alias_or_name(self) -> str:
        """Return alias if available, otherwise return name."""
        return self.alias or self.name

    def get_file(self) -> str | None:
        """Return the associated file path, if any."""
        return self.associated_file

    def is_due(self, date: datetime.date) -> bool:
        """Check if the habit is due on the given date."""
        return check_due(self.log, self.due_on, date)

    def set_status(self, date: datetime.date, status: Status) -> None:
        """Set the completion status for a given date."""
        self.log.set_status(date, status)
