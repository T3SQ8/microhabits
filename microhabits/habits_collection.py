"""Provides HabitsManager class for loading, managing, and logging habits and
their completion logs to and from YAML and CSV files."""

import csv
from datetime import datetime
from os.path import isfile

import yaml

from .habit import Habit

LOG_DATE_FORMAT = "%Y-%m-%d"


class HabitsManager:
    """Manages a collection of habits with persistence to files."""

    def __init__(self, habits_file: str, log_file: str):
        """Initialize the HabitsManager and load habits and logs from files."""
        self.habits_file = habits_file
        self.log_file = log_file
        self.habits: dict[str, Habit]

        self.habits = self.load_habits_from_file(habits_file)

        if isfile(log_file):
            self.load_log_from_file(log_file)

    def load_habits_from_file(self, habits_file: str) -> dict[str, Habit]:
        """Load habit definitions from a YAML file."""
        with open(habits_file, "r", encoding="utf-8") as f:
            habits = {}
            for habit in yaml.safe_load(f)["habits"]:
                name = habit["name"]
                if name in habits:
                    raise ValueError(
                        f'habit with name "{name}" exists multiple times in "{habits_file}"'
                    )
                due_on = habit.get("due_on")  # Default frequency daily
                file = habit.get("file")
                alias = habit.get("alias")
                habits[name] = Habit(name, due_on, file, alias)
            return habits

    def load_log_from_file(self, log_file: str) -> None:
        """Load completion logs from a CSV file and apply to habits."""
        with open(log_file, "r", encoding="utf-8") as f:
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

    def save_log_to_file(self):
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
