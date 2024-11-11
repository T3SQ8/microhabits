#!/usr/bin/env python3


import yaml
import csv
import datetime
from bisect import bisect
from dateutil.parser import parse as dateparse
from typing import TextIO, Dict, Optional, Union, List
import curses

STATUS_COMPLETED = ['y']
STATUS_SKIPPED = ['s']
STATUS_FAILED = [None]
STATUS_ALL = STATUS_FAILED + STATUS_COMPLETED + STATUS_SKIPPED

NAME_CUTOFF = 25
NAME_CUTOFF_CHAR = '…'
DATE_PADDING = 14

LOG_DATE_FORMAT = '%Y-%m-%d'
PRETTY_DATE_FORMAT = '%d/%m (%a)'


class Habit:
    def __init__(self, name: str, frequency: Union[List[str], int]):
        self.name = name
        self.frequency = frequency
        self.statuses = {}

    def set_status(self, date: datetime.date, status: Optional[str]):
        self.statuses[date] = status

    def get_status(self, date: datetime.date):
        return self.statuses.get(date)

    def is_due(self, date: datetime.date):
        due = True

        if self.get_status(date) in STATUS_COMPLETED + STATUS_SKIPPED:
            due = False
        elif self.frequency == 0:
            due = False
        elif isinstance(self.frequency, int):
            completed_days = [d for d, s in self.statuses.items() if s in STATUS_COMPLETED]
            last_done = bisect(completed_days, date)-1 # index of last completed date before date
            if last_done >= 0: # If any date was found
                last_done = completed_days[last_done]
                day_gap = (date - last_done).days
                if day_gap < self.frequency:
                    due = False
        elif isinstance(self.frequency, list):
            cond_month_day = []
            cond_week_day = []
            for cond in self.frequency:
                if any(c.isdigit() for c in cond): # if has any digits
                    cond_month_day.append(dateparse(cond).day)
                else:
                    cond_week_day.append(dateparse(cond).weekday())
            if (date.day not in cond_month_day) and (date.weekday() not in cond_week_day):
                due = False

        return due

    def toggle_status(self, date: datetime.date):
        status = self.get_status(date)
        i = STATUS_ALL.index(status)
        i = (i + 1) % len(STATUS_ALL)
        status = STATUS_ALL[i]
        self.set_status(date, status)

def load_habits_from_file(habits_file: TextIO) -> Dict[str, Habit]:
    habits = {}
    for h in yaml.safe_load(habits_file):
        name = h['name']
        frequency = h.get('frequency', 1) # Default frequency
        habits[name] = Habit(name, frequency)
    return habits


def load_log_from_file(habits: Dict[str, Habit], log_file: TextIO) -> Dict[str, Habit]:
    for entry in csv.DictReader(log_file):
        name = entry['name']
        date = datetime.datetime.strptime(entry['date'], LOG_DATE_FORMAT).date()
        status = entry['status']
        if h := habits.get(name):
            h.set_status(date, status)
    return habits


def save_log_to_file(habits: Dict[str, Habit], log_file: TextIO):
        writer = csv.DictWriter(log_file, fieldnames=['date', 'name', 'status'])
        writer.writeheader()
        for name, habit in habits.items():
            for date, status in habit.statuses.items():
                if status in STATUS_COMPLETED + STATUS_SKIPPED:
                    writer.writerow({
                        'date': date.strftime(LOG_DATE_FORMAT),
                        'name': name,
                        'status': status
                    })


def run(stdscr, habits):
    days_back = 1
    days_forward = 1
    header_height = 2
    today = datetime.date.today()
    selected_date = today
    selected_habit_nr = 0
    assert days_back >= 0 and days_forward >= 0

    curses_loop = True
    hide_completed = False
    header_pad = curses.newpad(header_height, 1000)
    habits_pad = curses.newpad(len(habits), 1000)

    stdscr.refresh()

    while curses_loop:
        # The marker for the selected date
        header_pad.addstr(0, NAME_CUTOFF + DATE_PADDING*days_back, '-'*DATE_PADDING)


        # Show selected date and the chosed number of days before/after
        date_range = [
            selected_date + datetime.timedelta(days=delta)
            for delta in range(-days_back, days_forward+1)
        ]
        for i,date in enumerate(date_range):
            attrb = curses.A_BOLD if date == today else curses.A_NORMAL
            formatted_date = date.strftime(PRETTY_DATE_FORMAT)
            header_pad.addstr(1, NAME_CUTOFF + DATE_PADDING*i, formatted_date, attrb)


        # Add habits to pad
        for row, (name, habit) in enumerate(habits.items()):
            attrb = curses.A_BOLD
            for i,date in enumerate(date_range):
                due = habit.is_due(date)
                status = habit.get_status(date)
                if len(name) > (l := NAME_CUTOFF-2):
                    name = name[:l] + NAME_CUTOFF_CHAR
                habits_pad.addstr(row, 0, name)
                if status: text = f'[{status}]'
                elif due:  text = '[ ]'
                else:      text = '[o]'
                if hide_completed and not due and date == selected_date:
                    attrb = curses.A_DIM
                habits_pad.addstr(row, NAME_CUTOFF + DATE_PADDING*i, text)
            habits_pad.chgat(row, 0, attrb)

        #habits_pad.move(self.selected_habit_nr, 0)
        attrb = curses.A_STANDOUT
        if bool(habits_pad.inch(selected_habit_nr, 0) & curses.A_BOLD):
            attrb = attrb | curses.A_BOLD
        habits_pad.chgat(selected_habit_nr, 0, attrb)


        # Refresh all pads at once.
        curses.update_lines_cols()
        y_max, x_max = stdscr.getmaxyx()
        y_max, x_max = y_max-1, x_max-1
        header_pad.refresh(0,0, 0,0, header_height,x_max)
        scroll = max(0, selected_habit_nr - y_max + header_height)
        habits_pad.refresh(scroll,0, header_height,0, y_max,x_max)


        match key := stdscr.getkey():
            case 'KEY_UP' | 'k':
                line = selected_habit_nr - 1
                line = max(0, line)
                selected_habit_nr = line
            case 'KEY_DOWN' | 'j':
                line = selected_habit_nr + 1
                line = min(line, len(habits)-1)
                selected_habit_nr = line
            case 'KEY_LEFT' | 'h':
                selected_date += datetime.timedelta(days=-1)
            case 'KEY_RIGHT' | 'l':
                selected_date += datetime.timedelta(days=1)
            case ' ':
                _, habit = list(habits.items())[selected_habit_nr]
                habit.toggle_status(selected_date)
            case 't':
                selected_date = today
            case 'q':
                curses_loop = False
            case 'H':
                hide_completed = not hide_completed
            case 'g':
                selected_habit_nr = 0
            case 'G':
                selected_habit_nr = len(habits)-1
            case _:
                print(key)


def main(habits_file, log_file):
    with open(habits_file, 'r') as f:
        habits = load_habits_from_file(f)

    try:
        with open(log_file, 'r') as f:
            habits = load_log_from_file(habits, f)
    except FileNotFoundError:
        pass

    curses.wrapper(lambda stdscr: run(stdscr, habits))

    with open(log_file, 'w') as f:
        save_log_to_file(habits, f)


if __name__ == '__main__':
    import os
    from pathlib import Path
    import argparse

    if (xdg_config_home := os.getenv('XDG_CONFIG_HOME')):
        xdg_config_home = Path(xdg_config_home)
    else:
        xdg_config_home = Path.home() / ".config"

    if (xdg_data_home := os.getenv('XDG_DATA_HOME')):
        xdg_data_home = Path(xdg_data_home)
    else:
        xdg_data_home = Path.home() / ".local/share"

    default_habits_file = xdg_config_home / "microhabits/habits.yml"
    default_log_file = xdg_data_home / "microhabits/log.csv"

    parser = argparse.ArgumentParser(description='minimalistic habit tracker')

    parser.add_argument('-f', '--file', metavar='FILE', dest='habits_file',
                               default=default_habits_file,
                               help='habits file in YAML format (default: %(default)s)')
    parser.add_argument('-l', '--log', metavar='FILE', dest='log_file',
                               default=default_log_file,
                               help='file to log activity to (default: %(default)s)')

    args = parser.parse_args()
    main(args.habits_file, args.log_file)
