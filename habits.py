#!/usr/bin/env python

import sys
import os
from datetime import datetime, timedelta
import csv
import curses
import re
import yaml

FIELDNAMES = ['date', 'name', 'status']

YAML_EXAMPLE_DATA = """
habits:
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
HELP_MESSAGE = 'keys: k/UP,j/DOWN:Select habit   h/LEFT,l/RIGHT:Select day   SPACE/RETURN:Toggle status   q:Save and exit   ?:Help'

DAYS_BACK = 3
DAYS_FORWARD = 1

def load_habits_from_file(habits_file):
    if not os.path.exists(habits_file):
        with open(habits_file, 'w', encoding='utf-8') as file:
            file.write(YAML_EXAMPLE_DATA)
    with open(habits_file, 'r', encoding='utf-8') as file:
        habits = yaml.safe_load(file)['habits']
    for habit in habits: # Default frequency daily
        if not 'frequency' in habit:
            habit['frequency'] = 1

    return habits

def load_log_from_file(log_file):
    if not os.path.exists(log_file):
        with open(log_file, 'w', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=FIELDNAMES)
            writer.writeheader()
    log = {}
    with open(log_file, 'r', encoding='utf-8') as file:
        for line in csv.DictReader(file):
            # Creates a 'log' dictionary, inside of each entry is another dictionary with dates and
            # a corresponding etatuses. This process removes duplicate CSV entries by overwriting
            # the date with the newest value.
            try:
                log[line['name']]
            except KeyError:
                log[line['name']] = {}
            name = line['name']
            date = line['date']
            status = line['status']
            log[name][date] = status
    return log

def dump_log_to_file(log, log_file):
    dump = []
    for habit, dates in log.items():
        for date, status in dates.items():
            dump.append({
                    'date': date,
                    'name': habit,
                    'status': status
            })
    with open(log_file, 'w', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=FIELDNAMES)
        writer.writeheader()
        for line in dump:
            writer.writerow(line)

def curses_tui(habits, log, log_file):
    def gen_content(start_day, before_days, forward_days):
        before_days = -abs(before_days)

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
        for habit in habits:
            row = ''
            name = habit['name'][:22]+'>' if len(habit['name']) > 22 else habit['name']
            row += name.ljust(24)
            i = before_days
            while before_days <= i <= forward_days:
                screen_date = start_day + timedelta(days=i)
                screen_date = screen_date.strftime('%Y-%m-%d')
                try:
                    textbox = f'[{log[habit["name"]][screen_date]}]'
                except KeyError:
                    if check_due(habit, screen_date):
                        textbox = '[ ]'
                    else:
                        textbox = '[o]'
                row += textbox.ljust(14)
                i += 1
            habits_list.append(row)

        return header, habits_list

    def toggle_status(habit_name, date):
        if not habit_name in log:
            log[habit_name] = {}
        if not date in log[habit_name]:
            log[habit_name][date] = {}

        match log[habit_name][date]:
            case 'y':
                log[habit_name][date] = 's'
            case 's':
                del log[habit_name][date]
            case _:
                log[habit_name][date] = 'y'

    def check_due(habit, selected_date):
        due = True
        frequency = habit['frequency']
        name = habit['name']
        selected_date = datetime.strptime(selected_date, "%Y-%m-%d")

        match frequency:
            case int():
                if frequency == 0:
                    due = False
                try:
                    for status_date in sorted(log[name]):
                        status = log[name][status_date]
                        if status == 'y':
                            tmp_last_done = datetime.strptime(status_date, "%Y-%m-%d")
                            if tmp_last_done.date() < selected_date.date():
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
                except AttributeError:
                    frequency = [ item.capitalize() for item in frequency ]
                    selected_date = selected_date.strftime('%A') # Day of week
                    if not selected_date.capitalize() in frequency:
                        due = False
        return due

    def curses_loop(stdscr):
        now = datetime.today()
        col = 0
        row = 0
        current_row = 0
        curses.curs_set(0)
        curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE)
        while True:
            stdscr.erase()
            y_max, x_max = stdscr.getmaxyx()
            stdscr.addstr(y_max-1, 0, HELP_MESSAGE)
            header, menu_habits = gen_content(now, DAYS_BACK, DAYS_FORWARD)
            for row, line in enumerate(header):
                stdscr.addstr(row, 0, line)
                row += 1
            for idy, text in enumerate(menu_habits):
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
            if (key == curses.KEY_DOWN  or key == ord('j')) and current_row < len(menu_habits) - 1:
                current_row += 1
            if key == curses.KEY_LEFT or key == ord('h'):
                now = now - timedelta(days=1)
            if key == curses.KEY_RIGHT or key == ord('l'):
                now = now + timedelta(days=1)
            if key == curses.KEY_ENTER or key in [ord('\n'), ord('\r'), ord(' ')]:
                toggle_status(
                    habits[current_row]['name'],
                    now.strftime('%Y-%m-%d')
                    )
            if key == ord('t'):
                now = datetime.today()
            if key == ord('s'):
                dump_log_to_file(log, log_file)
                stdscr.addstr(y_max-2, 0, f'Saved to {log_file}')
                stdscr.getch()
            if key == ord('q'):
                dump_log_to_file(log, log_file)
                sys.exit(1)
            if key == ord('Q'):
                stdscr.addstr(y_max-2, 0, 'Do you want to quit without saving? [N/y]')
                key = stdscr.getch()
                if key == ord('y') or key == ord('Y'):
                    sys.exit(1)

    curses.wrapper(curses_loop)

def main(habits_file, log_file):
    if not habits_file:
        try:
            habits_file = os.environ['XDG_CONFIG_HOME'] + '/microhabits/habits.yml'
        except KeyError:
            habits_file = os.environ['HOME'] + '/.config/microhabits/habits.yml'

    if not log_file:
        try:
            log_file = os.environ['XDG_DATA_HOME'] + '/microhabits/log.csv'
        except KeyError:
            log_file = os.environ['HOME'] + '/.config/microhabits/log.csv'

    for path in [habits_file, log_file]:
        parents = os.path.dirname(path)
        if parents:
            os.makedirs(parents, exist_ok=True)

    habits = load_habits_from_file(habits_file)
    log = load_log_from_file(log_file)
    curses_tui(habits, log, log_file)

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Minimalistic habit tracker')
    parser.add_argument('-f', '--file', dest='habits_file', metavar='FILE',
            help='Habits file in YAML format')
    parser.add_argument('-l', '--log_file',
            help='File to log activity to')
    args = parser.parse_args()
    main(args.habits_file, args.log_file)
