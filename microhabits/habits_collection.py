"""Provides HabitsManager class for loading, managing, and logging habits and
their completion logs to and from YAML and CSV files."""

import csv
from dataclasses import dataclass, field
from datetime import datetime
from os import PathLike
from typing import Iterable, Self

import yaml

from .habit import Habit

LOG_DATE_FORMAT = "%Y-%m-%d"


@dataclass
class HabitsManager:
    """Manages a collection of habits with persistence to files."""

    habits_file: str | PathLike
    log_file: str | PathLike
    habits: dict[str, Habit] = field(default_factory=dict)

    def get_habits(self) -> Iterable[Habit]:
        """Returns all defined habits."""
        return self.habits.values()

    def get_unhidden(self) -> list[Habit]:
        """Returns non-hidden habtis. By default, habits that appear in the log but not in the
        habits.yml file are marked as hidden."""
        return [habit for habit in self.get_habits() if not habit.hide_from_tui]

    def load_files(self) -> Self:
        """Loads habits and log files, then returns self."""
        self.load_habits_from_file()
        self.load_log_from_file()
        return self

    def load_habits_from_file(self) -> None:
        """Load habit definitions from a YAML file."""
        with open(self.habits_file, "r", encoding="utf-8") as f:
            for habit in yaml.safe_load(f)["habits"]:
                name = habit["name"]
                if name in self.habits:
                    raise ValueError(
                        f'habit with name "{name}" exists multiple times in "{self.habits_file}"'
                    )
                due_on = habit.get("due_on")  # Default frequency daily
                file = habit.get("file")
                alias = habit.get("alias")
                self.habits[name] = Habit(name, due_on, file, alias)

    def load_log_from_file(self) -> None:
        """Load completion logs from a CSV file and apply to habits."""
        with open(self.log_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for entry in reader:
                name = entry["name"]
                status = entry["status"]
                date = datetime.strptime(
                    entry["date"], LOG_DATE_FORMAT
                ).date()  # str to datetime obj

                if habit := self.habits.get(name):
                    habit.log.set_status(date, status)
                else:
                    # create habit if it exists in log but not in habits.yml, will be hidden tui but
                    # removing this section will delete the habits past logs next time it is saved
                    # to file
                    habit = Habit(
                        name=name, due_on={"frequency": 0}, hide_from_tui=True
                    )
                    habit.set_status(date, status)

    def save_log_to_file(self) -> None:
        """Save all habit completion logs to a CSV file."""
        with open(self.log_file, "w", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["date", "name", "status"])
            writer.writeheader()
            for name, habit in self.habits.items():
                for date, status in habit.log.statuses.items():
                    if status is not None:
                        writer.writerow(
                            {
                                "date": date.strftime(LOG_DATE_FORMAT),
                                "name": name,
                                "status": status,
                            }
                        )
