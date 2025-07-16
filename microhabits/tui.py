import csv
import curses
import datetime
import os
import subprocess
from bisect import bisect
from typing import Dict, List, Optional, TextIO, Union

import yaml
from dateutil.parser import parse as dateparse

STATUS_COMPLETED = ["y"]
STATUS_SKIPPED = ["s"]
STATUS_FAILED = [None]
STATUS_ALL = STATUS_FAILED + STATUS_COMPLETED + STATUS_SKIPPED

NAME_CUTOFF = 25
NAME_CUTOFF_CHAR = "…"
DATE_PADDING = 14
DAYS_BACK = 1
DAYS_FORWARD = 1
HEADER_HEIGHT = 2

LOG_DATE_FORMAT = "%Y-%m-%d"
PRETTY_DATE_FORMAT = "%d/%m (%a)"


class Habit:
    def __init__(
        self,
        name: str,
        frequency: Union[List[str], int],
        associated_file: Union[str, None] = None,
    ):
        self.name = name
        self.frequency = frequency
        self.statuses = {}
        self.associated_file = associated_file
        self.hide_from_tui = False

    def set_status(self, date: datetime.date, status: Optional[str]):
        self.statuses[date] = status

    def get_status(self, date: datetime.date):
        return self.statuses.get(date)

    def get_name(self) -> str:
        return self.name

    def get_file(self) -> Union[str, None]:
        return self.associated_file

    def toggle_status(self, date: datetime.date):
        status = self.get_status(date)
        i = STATUS_ALL.index(status)
        i = (i + 1) % len(STATUS_ALL)
        status = STATUS_ALL[i]
        self.set_status(date, status)

    def is_due(self, date: datetime.date):
        due = True
        if self.get_status(date) in STATUS_COMPLETED + STATUS_SKIPPED:
            due = False
        elif self.frequency == 0:
            due = False
        elif isinstance(self.frequency, int):
            completed_days = [
                d for d, s in self.statuses.items() if s in STATUS_COMPLETED
            ]
            last_done = (
                bisect(completed_days, date) - 1
            )  # index of last completed date before date
            if last_done >= 0:  # If any date was found
                last_done = completed_days[last_done]
                day_gap = (date - last_done).days
                if day_gap < self.frequency:
                    due = False
        elif isinstance(self.frequency, list):
            cond_month_day = []
            cond_week_day = []
            for cond in self.frequency:
                if any(c.isdigit() for c in cond):  # if has any digits
                    cond_month_day.append(dateparse(cond).day)
                else:
                    cond_week_day.append(dateparse(cond).weekday())
            if (date.day not in cond_month_day) and (
                date.weekday() not in cond_week_day
            ):
                due = False
        return due


def load_habits_from_file(habits_file: TextIO) -> Dict[str, Habit]:
    habits = {}
    for h in yaml.safe_load(habits_file):
        name = h["name"]
        frequency = h.get("frequency", 1)  # Default frequency
        file = h.get("file")
        habits[name] = Habit(name, frequency, file)
    return habits


def load_log_from_file(habits: Dict[str, Habit], log_file: TextIO) -> Dict[str, Habit]:
    for entry in csv.DictReader(log_file):
        name = entry["name"]
        date = datetime.datetime.strptime(entry["date"], LOG_DATE_FORMAT).date()
        status = entry["status"]
        if h := habits.get(name):
            h.set_status(date, status)
        else:
            h = Habit(name, 0)
            h.set_status(date, status)
            h.hide_from_tui = True
            habits[name] = h
    return habits


def save_log_to_file(habits: Dict[str, Habit], log_file: TextIO):
    writer = csv.DictWriter(log_file, fieldnames=["date", "name", "status"])
    writer.writeheader()
    for name, habit in habits.items():
        for date, status in habit.statuses.items():
            if status in STATUS_COMPLETED + STATUS_SKIPPED:
                writer.writerow(
                    {
                        "date": date.strftime(LOG_DATE_FORMAT),
                        "name": name,
                        "status": status,
                    }
                )


def open_in_editor(file_path: str, editor=None):
    if file_path:

        if not editor:
            editor = os.getenv("EDITOR", "vi")
        file_path = os.path.expanduser(file_path)
        subprocess.run([editor, file_path], check=False)


def run(stdscr, habits):
    today = datetime.date.today()
    selected_date = today
    selected_habit_nr = 0

    tui_habits = []
    for name, habit in habits.items():
        if not habit.hide_from_tui:
            tui_habits.append(habit)

    curses_loop = True
    hide_completed = False
    header_pad = curses.newpad(HEADER_HEIGHT, 1000)
    habits_pad = curses.newpad(len(tui_habits), 1000)

    stdscr.refresh()  # needed so everything displays at program start without a keypress

    while curses_loop:
        # The marker for the selected date
        header_pad.addstr(0, NAME_CUTOFF + DATE_PADDING * DAYS_BACK, "-" * DATE_PADDING)

        # Show selected date and the chosed number of days before/after
        date_range = [
            selected_date + datetime.timedelta(days=delta)
            for delta in range(-DAYS_BACK, DAYS_FORWARD + 1)
        ]
        for i, date in enumerate(date_range):
            attrb = curses.A_BOLD if date == today else curses.A_NORMAL
            formatted_date = date.strftime(PRETTY_DATE_FORMAT)
            header_pad.addstr(1, NAME_CUTOFF + DATE_PADDING * i, formatted_date, attrb)

        # Add habits to pad
        for row, habit in enumerate(tui_habits):
            name = habit.get_name()
            if habit.get_file():
                name = "[f] " + name
            if len(name) > (l := NAME_CUTOFF - 2):
                name = name[:l] + NAME_CUTOFF_CHAR
            attrb = curses.A_BOLD
            for i, date in enumerate(date_range):
                due = habit.is_due(date)
                status = habit.get_status(date)
                habits_pad.addstr(row, 0, name)
                if status:
                    text = f"[{status}]"
                elif due:
                    text = "[ ]"
                else:
                    text = "[o]"
                if hide_completed and not due and date == selected_date:
                    attrb = curses.A_DIM
                habits_pad.addstr(row, NAME_CUTOFF + DATE_PADDING * i, text)
            habits_pad.chgat(row, 0, attrb)

        attrb = curses.A_STANDOUT
        if bool(habits_pad.inch(selected_habit_nr, 0) & curses.A_BOLD):
            attrb = attrb | curses.A_BOLD
        habits_pad.chgat(selected_habit_nr, 0, attrb)

        # Refresh all pads at once.
        curses.update_lines_cols()
        y_max, x_max = [p - 1 for p in stdscr.getmaxyx()]
        header_pad.refresh(0, 0, 0, 0, HEADER_HEIGHT, x_max)
        scroll = max(0, selected_habit_nr - y_max + HEADER_HEIGHT)
        habits_pad.refresh(scroll, 0, HEADER_HEIGHT, 0, y_max, x_max)

        match key := stdscr.getkey():
            case "KEY_UP" | "k":
                selected_habit_nr = max(0, selected_habit_nr - 1)
            case "KEY_DOWN" | "j":
                selected_habit_nr = min(selected_habit_nr + 1, len(tui_habits) - 1)
            case "KEY_LEFT" | "h":
                selected_date -= datetime.timedelta(days=1)
            case "KEY_RIGHT" | "l":
                selected_date += datetime.timedelta(days=1)
            case " ":
                tui_habits[selected_habit_nr].toggle_status(selected_date)
            case "t":
                selected_date = today
            case "q":
                curses_loop = False
            case "H":
                hide_completed = not hide_completed
            case "g":
                selected_habit_nr = 0
            case "G":
                selected_habit_nr = len(tui_habits) - 1
            case "E":
                try:
                    open_in_editor(tui_habits[selected_habit_nr].get_file())
                finally:
                    stdscr.clear()
                    stdscr.refresh()
            case _:
                print(key)


def main(habits_file, log_file):
    with open(habits_file, "r", encoding="utf-8") as f:
        habits = load_habits_from_file(f)

    try:
        with open(log_file, "r", encoding="utf-8") as f:
            habits = load_log_from_file(habits, f)
    except FileNotFoundError:
        pass

    curses.wrapper(lambda stdscr: run(stdscr, habits))

    with open(log_file, "w", encoding="utf-8") as f:
        save_log_to_file(habits, f)
