#!/usr/bin/env python3


# TODO Lock file
# TODO "S" to mark all tasks as skipped
# TODO Press "?" to show all key binds

import os
from datetime import datetime, timedelta
import csv
from bisect import bisect
import curses
import yaml
import dateutil.parser


YAML_EXAMPLE_DATA = """
- name: Exercise
  frequency: ['Monday', 'Wednesday', 'Saturday'] # Specific days of the week

- name: Clean House
  frequency: 3 # Every 3 days

- name: Backup
  frequency: ['1st', '15th'] # Every 1st and 15th of every month

- name: Take a long walk on the beach # Example of long name
  # Default frequency daily

- name: Play videogames # Habits that don't need to be done but are tracked
  frequency: 0
"""

class Habits:
    def __init__(self, habits_file, log_file):
        self.habits_file = habits_file
        self.log_file = log_file
        self.status_comp = ['y']
        self.status_skip = ['s']
        self.status_fail = [None]
        self.status_all = self.status_comp + self.status_skip + self.status_fail

        self.habits = None
        self.log = {}

    def load_habits_from_file(self):
        if not os.path.isfile(self.habits_file):
            with open(self.habits_file, 'w', encoding='utf-8') as f:
                f.write(YAML_EXAMPLE_DATA)
        with open(self.habits_file, 'r', encoding='utf-8') as f:
            habits = yaml.safe_load(f)
        self.habits = {}
        for habit in habits:
            name = habit['name']
            frequency = habit.get('frequency', 1)
            self.habits.setdefault(name, {})
            self.habits[name]['frequency'] = frequency

    def load_log_file(self):
        if not os.path.isfile(self.log_file):
            self.save_log_file()
        with open(self.log_file, 'r+', encoding='utf-8') as f:
            for entry in csv.DictReader(f):
                # Creates a dictionary where each item contains another dictionary with dates
                # and a corresponding status. This process removes duplicate CSV entries by
                # overwriting the date's status with the latest value.
                # {'habit1': {2024-01-01: 'y', 2024-01-02: 's', ...},
                #  'habit2': {2024-01-01: 'y', 2024-01-02: 'y', ...}}
                name = entry['name']
                date = self.iso_to_dt(entry['date'])
                status = entry['status']
                self.log.setdefault(name, {})
                self.log[name][date] = status

    def save_log_file(self):
        with open(self.log_file, 'w+', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['date', 'name', 'status'])
            writer.writeheader()
            for habit, dates in self.log.items():
                for date, status in dates.items():
                    if status:
                        writer.writerow({
                            'date': self.dt_to_iso(date),
                            'name': habit,
                            'status': status
                        })

    def pretty_print_log(self):
        print(yaml.dump(self.log)) # using yaml despite original data being csv

    def is_due(self, name, date):
        due = True
        frequency = self.habits[name]['frequency']
        log_entries = self.log.get(name, {})
        status_chosen_date = log_entries.get(date)

        if frequency == 0:
            due = False
        elif status_chosen_date in self.status_comp:
            due = False
        elif isinstance(frequency, int):
            completed_dates = [date for date, status in log_entries.items() if status == "y"]
            last_done = bisect(completed_dates, date) - 1
            if last_done >= 0:
                last_done = abs((date - completed_dates[last_done]).days)
                if last_done < frequency:
                    due = False
        elif isinstance(frequency, list):
            cond_month_day = []
            cond_week_day = []
            for cond in frequency:
                if any(c.isdigit() for c in cond):
                    day = dateutil.parser.parse(cond).day
                    cond_month_day.append(day)
                else:
                    day = dateutil.parser.parse(cond).weekday()
                    cond_week_day.append(day)
            if date.day in cond_month_day:
                due = True
            elif not date.weekday() in cond_week_day:
                due = False
        return due

    def toggle_status(self, name, date):
        log = self.log.setdefault(name, {})
        status = log.get(date)
        i = self.status_all.index(status)
        i = (i + 1) % len(self.status_all)
        status = self.status_all[i]
        self.log[name][date] = status

    def dt_to_iso(self, dt):
        return dt.strftime('%Y-%m-%d')

    def iso_to_dt(self, date):
        return datetime.strptime(date, "%Y-%m-%d")



class CursesTui:
    def __init__(self, habits):
        self.habits = habits
        self.today = datetime.today()
        self.today = self.today.replace(hour=0, minute=0, second=0, microsecond=0)
        self.selected_date = self.today
        self.selected_habit_nr = 0
        self.curses_loop = True
        self.hide_completed = False
        self.scroll = 0

        self.y_max = 0
        self.x_max = 0
        self.window = None
        self.days_back = 3
        self.days_forward = 1
        self.name_cutoff = 25
        self.cutoff_char = '…'
        self.date_padding = 14
        self.header_height = 2
        self.message_height = 1

        self.header_pad = None
        self.message_pad = None
        self.habits_pad = None

        self.keys_main = {
                curses.KEY_UP:    (self.move, ['up']),
                curses.KEY_DOWN:  (self.move, ['down']),
                curses.KEY_LEFT:  (self.move, ['left']),
                curses.KEY_RIGHT: (self.move, ['right']),
                curses.KEY_ENTER: (self.toggle_status, []),
                ord('q'):         (self.save_quit, []),
                }

        self.keys_misc = {
                ord('k'):  (self.move, ['up']),
                ord('j'):  (self.move, ['down']),
                ord('h'):  (self.move, ['left']),
                ord('l'):  (self.move, ['right']),
                ord('s'):  (self.save, []),
                ord('Q'):  (self.force_exit, []),
                ord('t'):  (self.move, ['today']),
                ord('g'):  (self.move, ['top']),
                ord('G'):  (self.move, ['bottom']),
                ord('H'):  (self.toggle_hide, []),
                ord('\n'): (self.toggle_status, []),
                ord('\r'): (self.toggle_status, []),
                ord(' '):  (self.toggle_status, []),
                }

        self.keys_internal = {
                curses.KEY_RESIZE: (self.resize, []),
                }

        self.keys_all = self.keys_main | self.keys_misc | self.keys_internal

    def move(self, direction, dist=1):
        match direction:
            case 'up':
                if (line := self.selected_habit_nr - dist) >= 0:
                    self.selected_habit_nr = line
            case 'down':
                if (line := self.selected_habit_nr + dist) < len(self.habits.habits):
                    self.selected_habit_nr = line
            case 'right':
                self.selected_date += timedelta(days=dist)
            case 'left':
                self.selected_date -= timedelta(days=dist)
            case 'top':
                self.selected_habit_nr = 0
            case 'bottom':
                self.selected_habit_nr = len(self.habits.habits)-1
            case 'today':
                self.selected_date = self.today
        # TODO find a better way to scroll
        s = self.selected_habit_nr - self.y_max + self.header_height + self.message_height
        self.scroll = max(0, s)

    def screen_date_format(self, dt):
        return dt.strftime('%d/%m (%a)')

    def toggle_status(self):
        name = list(self.habits.habits.keys())[self.selected_habit_nr]
        date = self.selected_date
        self.habits.toggle_status(name, date)

    def force_exit(self):
        self.notify('Do you want to quit without saving? [y/N]')
        self.refresh()
        key = self.window.getch()
        if key == ord('y') or key == ord('Y'):
            self.curses_loop = False

    def save(self):
        self.habits.save_log_file()
        self.notify(f'Saved to {self.habits.log_file}')

    def save_quit(self):
        self.save()
        self.curses_loop = False

    def notify(self, msg=''):
        msg = msg.ljust(self.x_max)[:self.x_max-1] # Pad and crop to cover older messages
        self.message_pad.addstr(0, 0, msg)

    def toggle_hide(self):
        self.hide_completed = not self.hide_completed

    def resize(self):
        self.y_max, self.x_max = self.window.getmaxyx()
        self.y_max -= 1
        self.x_max -= 1

    def refresh(self):
        self.header_pad.refresh(0,0,  0,0,  self.header_height,self.x_max)
        self.habits_pad.refresh(self.scroll,0,  self.header_height,0,
                                self.y_max-self.message_height,self.x_max)
        self.message_pad.refresh(0,0,  self.y_max,0,  self.y_max,self.x_max)

    def run(self, window):
        self.window = window
        self.resize()
        self.header_pad = curses.newpad(self.header_height, 1000)
        self.message_pad = curses.newpad(self.message_height, 1000)
        self.habits_pad = curses.newpad(len(self.habits.habits), 1000)
        curses.curs_set(0)
        window.refresh()

        while self.curses_loop:
            self.header_pad.addstr(0, self.name_cutoff + self.date_padding *
                                   abs(self.days_back), '-' * self.date_padding)

            date_range = []
            for delta in range(-abs(self.days_back), self.days_forward + 1):
                date_range.append(self.selected_date + timedelta(days=delta))


            for i,date in enumerate(date_range):
                attrb = curses.A_BOLD if date == self.today else curses.A_NORMAL
                date = self.screen_date_format(date)
                self.header_pad.addstr(1, self.name_cutoff + self.date_padding*i, date, attrb)

            for row, habit in enumerate(self.habits.habits):
                attrb = curses.A_BOLD
                for i,date in enumerate(date_range):
                    name = habit
                    due = self.habits.is_due(name, date)
                    status = self.habits.log.get(name)
                    if status:
                        status = status.get(date)
                    if len(name) > self.name_cutoff - 2:
                        name = name[:self.name_cutoff - 2] + self.cutoff_char
                    self.habits_pad.addstr(row, 0, name)
                    if status:
                        text = f'[{status}]'
                    elif due:
                        text = '[ ]'
                    else:
                        text = '[o]'
                    if self.hide_completed and not due and date == self.selected_date:
                        attrb = curses.A_DIM
                    self.habits_pad.addstr(row, self.name_cutoff + self.date_padding*i, text)
                self.habits_pad.chgat(row, 0, attrb)

            self.habits_pad.move(self.selected_habit_nr, 0)
            attrb = curses.A_STANDOUT
            if bool(self.habits_pad.inch(self.selected_habit_nr, 0) & curses.A_BOLD):
                attrb = attrb | curses.A_BOLD
            self.habits_pad.chgat(self.selected_habit_nr, 0, attrb)

            self.refresh()
            self.notify()

            p = self.keys_all.get(window.getch())
            if p:
                func, parms = p
                func(*parms)



def launch_habit_tracker(a):
    for i in [a.file, a.log]:
        if (dir := os.path.dirname(i)) :
            os.makedirs(dir, exist_ok=True)
    habits = Habits(a.file, a.log)
    habits.load_habits_from_file()
    habits.load_log_file()
    tui = CursesTui(habits)
    tui.days_back = a.days_back
    tui.days_forward = a.days_forward
    curses.wrapper(tui.run)


def rename_in_logfile():
    pass # TODO function to rename in logfile

if __name__ == '__main__':
    import argparse

    default_habits_file = os.environ.get('XDG_CONFIG_HOME') or os.path.expanduser('~/.config')
    default_habits_file += '/microhabits/habits.yml'
    default_log_file = os.environ.get('XDG_DATA_HOME') or os.path.expanduser('~/.local/share')
    default_log_file += '/microhabits/log.csv'

    parser = argparse.ArgumentParser(description='minimalistic habit tracker')
    subparsers = parser.add_subparsers()

    habit_tracker = subparsers.add_parser('habits', help='Track habits')
    habit_tracker.set_defaults(func=launch_habit_tracker)
    habit_tracker.add_argument('-f', '--file', metavar='FILE',
                               default=default_habits_file,
                               help='habits file in YAML format (default: %(default)s)')
    habit_tracker.add_argument('-l', '--log', metavar='FILE', default=default_log_file,
            help='file to log activity to (default: %(default)s)')
    habit_tracker.add_argument('-b', '--days-back', default=3, type=int, metavar='DAYS',
            help='days before the selected date to display (default: %(default)s)')
    habit_tracker.add_argument('-w', '--days-forward', default=1, type=int, metavar='DAYS',
            help='days after the selected date to display (default: %(default)s)')

    habit_rename = subparsers.add_parser('rename', help='Rename habit in log file')
    habit_rename.set_defaults(func=rename_in_logfile)
    habit_rename.add_argument('habit_name', metavar='NAME',
                              help='old habit name to be replaced')
    habit_rename.add_argument('habit_name_new', metavar='STRING',
                              help='new habit name')
    habit_rename.add_argument('-l', '--log', metavar='FILE', default=default_log_file,
                              help='log file (default: %(default)s)')

    args = parser.parse_args()
    args.func(args)
