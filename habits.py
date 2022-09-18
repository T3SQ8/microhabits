#!/usr/bin/env python

import sys
from os.path import exists
from datetime import datetime, timedelta
import csv
import curses
import re
import yaml

DAYS_BACK = 3
DAYS_FORWARD = 1

class Habits:
    def __init__(self, habits_file, log_file):
        self.fieldnames = ['date', 'name', 'status']
        self.habits_file = habits_file
        self.log_file = log_file
        self.log = {}
        self.habits = {}
        if not exists(self.habits_file):
            print(f"No such file or directory: '{self.habits_file}'")
            sys.exit(1)
        if not exists(self.log_file):
            with open(self.log_file, 'w', encoding='utf-8') as file:
                csv.writer(file).writerow(self.fieldnames)

    def load_habits_from_file(self):
        with open(self.habits_file, 'r', encoding='utf-8') as file:
            habits = yaml.safe_load(file)
            self.habits = habits['habits']

        for habit in self.habits: # Default frequency daily
            if not 'frequency' in habit:
                habit['frequency'] = 1

    def load_log_from_file(self):
        log = []
        self.log = {}
        with open(self.log_file, 'r', encoding='utf-8') as file:
            for row in csv.DictReader(file):
                log.append(row)
        # Creates a 'log' dictionary, inside of each entry is another dictionary with a date and a
        # corresponding status. This process removes duplicate CSV entries by overwriting the date
        # with the newest value.
        for _dict in log:
            try:
                self.log[_dict['name']]
            except KeyError:
                self.log[_dict['name']] = {}
            self.log[_dict['name']][_dict['date']] = _dict['status']

    def dump_log_to_file(self):
        log = []
        # As a result of the way the log is processed, the entries are grouped together by the
        # habit.
        for habit, dates in self.log.items():
            for date, status in dates.items():
                log.append({
                        'date': date,
                        'name': habit,
                        'status': status
                })
        with open(self.log_file, 'w', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=self.fieldnames)
            writer.writeheader()
            for _dict in log:
                writer.writerow(_dict)

    def curses_tui(self):
        curses.wrapper(self.curses_loop)

    def gen_content(self, start_day, before_days, forward_days):

        before_days = -before_days if before_days > 0 else before_days # Make negative if positive

        header = []
        header.append(' '.ljust(66) + '-----------')

        day_header = ' '.ljust(21)
        i = before_days
        while before_days <= i <= forward_days:
            screen_date = start_day + timedelta(days=i)
            day_header += screen_date.strftime('%d/%m (%a)').rjust(14)
            i += 1
        header.append(day_header)

        habits_list = []
        for habit in self.habits:
            row = ''
            name = habit['name'][:22]+'>' if len(habit['name']) > 22 else habit['name']
            row += name.ljust(24)
            i = before_days
            while before_days <= i <= forward_days:
                screen_date = start_day + timedelta(days=i)
                screen_date = screen_date.strftime('%Y-%m-%d')
                try:
                    textbox = f'[{self.log[habit["name"]][screen_date]}]'
                except KeyError:
                    if self.check_due(habit, screen_date):
                        textbox = '[ ]'
                    else:
                        textbox = '[o]'
                row += textbox.ljust(14)
                i += 1
            habits_list.append(row)

        return header, habits_list

    def toggle_status(self, habit_name, date):
        if not habit_name in self.log:
            self.log[habit_name] = {}
        if not date in self.log[habit_name]:
            self.log[habit_name][date] = {}

        match self.log[habit_name][date]:
            case 'y':
                self.log[habit_name][date] = 's'
            case 's':
                del self.log[habit_name][date]
            case _:
                self.log[habit_name][date] = 'y'

    def check_due(self, habit, selected_date):
        due = True
        frequency = habit['frequency']
        name = habit['name']
        selected_date = datetime.strptime(selected_date, "%Y-%m-%d")

        match frequency:
            case int():
                if frequency == 0:
                    due = False
                try:
                    for status_date in sorted(self.log[name]):
                        status = self.log[name][status_date]
                        if status == 'y':
                            tmp_last_done = datetime.strptime(status_date, "%Y-%m-%d")
                            if not tmp_last_done.date() > selected_date.date():
                                last_done = tmp_last_done
                except KeyError:
                    pass
                if 'last_done' in locals():
                    delta = selected_date - last_done
                    if 0 <= delta.days < frequency:
                        due = False
            case list():
                try:
                    frequency = [
                            re.search(r'(\d{1,2})[a-zA-Z]{2}',
                                item).group(1) for item in frequency
                            ]
                    selected_date = selected_date.strftime('%-d') # non-padded day of month
                    if not selected_date in frequency:
                        due = False
                except Exception:
                    frequency = [ item.capitalize() for item in frequency ]
                    selected_date = selected_date.strftime('%A') # Day of week
                    if not selected_date.capitalize() in frequency:
                        due = False
        return due

    def curses_loop(self, stdscr):
        y_max, x_max = stdscr.getmaxyx()
        now = datetime.today()
        col = 0
        row = 0
        current_row = 0
        curses.curs_set(0)
        curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE)

        def message(msg):
            msg = msg.ljust(x_max-1) # Pad the message so that it covers any previous message
            stdscr.addstr(y_max-1, 0, msg)

        def save():
            self.dump_log_to_file()
            message(f'Saved to {self.log_file}')

        while True:
            stdscr.erase()
            message(
                    'keys: k/UP,j/DOWN:Select habit   h/LEFT,l/RIGHT:Select day   SPACE/RETURN:Toggle status   t:Jump to today   q:Save and exit   Q:Exit'
                    )
            header, habits = self.gen_content(now, DAYS_BACK, DAYS_FORWARD)
            for row, line in enumerate(header):
                stdscr.addstr(row, 0, line)
                row += 1
            for idy, text in enumerate(habits):
                if idy == current_row:
                    stdscr.attron(curses.color_pair(1))
                    stdscr.addstr(row, col, text)
                    stdscr.attroff(curses.color_pair(1))
                else:
                    stdscr.addstr(row, col, text)
                row += 1
            key = stdscr.getch()
            if (key == curses.KEY_UP or key == ord('k')) and current_row > 0:
                current_row -= 1
            if (key == curses.KEY_DOWN  or key == ord('j')) and current_row < len(habits) - 1:
                current_row += 1
            if key == curses.KEY_LEFT or key == ord('h'):
                now = now - timedelta(days=1)
            if key == curses.KEY_RIGHT or key == ord('l'):
                now = now + timedelta(days=1)
            if key == curses.KEY_ENTER or key in [ord('\n'), ord('\r'), ord(' ')]:
                self.toggle_status(
                    self.habits[current_row]['name'],
                    now.strftime('%Y-%m-%d')
                    )
            if key == ord('t'):
                now = datetime.today()
            if key == ord('s'):
                save()
                stdscr.getch()
            if key == ord('q'):
                save()
                sys.exit(1)
            if key == ord('Q'):
                message('Do you want to quit without saving? (N/y)')
                key = stdscr.getch()
                if key == ord('y') or key == ord('Y'):
                    sys.exit(1)

def main(habits_file):
    log_file = habits_file[:habits_file.rfind(".")] + '.csv'
    habits = Habits(habits_file, log_file)
    habits.load_habits_from_file()
    habits.load_log_from_file()
    habits.curses_tui()

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Visually plot ledger files.')
    parser.add_argument('habits_file', metavar='FILE', help='Habits file in YAML format')
    args = parser.parse_args()
    main(args.habits_file)
