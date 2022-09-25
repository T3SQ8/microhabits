#!/usr/bin/env python

# TODO Overflowing habits
# TODO Press "H" hide done/skipped/sufficed tasks
# TODO Press "?" to all key binds
# TODO Subtasks
# TODO Don't crash when screen size is changed
# TODO Measurable habits
# TODO Highlight today's date
# TODO Option change mark character
# TODO Manpage
# TODO Visual plot/graph

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

HABIT_NAME_CUTOFF = 25
DATE_PADDING = 14

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
            # a corresponding statuses. This process removes duplicate CSV entries by overwriting
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

def is_due(habit, log, selected_date):
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

def curses_tui(window, habits, log, log_file, days_back, days_forward):
    def gen_content(start_day, before_days, forward_days):
        before_days = -abs(before_days)

        header = [' '.ljust(HABIT_NAME_CUTOFF)]
        header[0] += ' ' * DATE_PADDING * abs(days_back)
        header[0] += '-' * DATE_PADDING

        day_header = ' '.ljust(HABIT_NAME_CUTOFF)
        i = before_days
        while before_days <= i <= forward_days:
            screen_date = start_day + timedelta(days=i)
            day_header += screen_date.strftime('%d/%m (%a)').ljust(DATE_PADDING)
            i += 1
        header.append(day_header)

        habits_list = []
        for habit in habits:
            row = ''
            if len(habit['name']) > HABIT_NAME_CUTOFF - 2:
                name = habit['name'][:HABIT_NAME_CUTOFF - 2]+'>'
            else:
                name = habit['name']
            row += name.ljust(HABIT_NAME_CUTOFF)
            i = before_days
            while before_days <= i <= forward_days:
                screen_date = start_day + timedelta(days=i)
                screen_date = screen_date.strftime('%Y-%m-%d')
                try:
                    textbox = f'[{log[habit["name"]][screen_date]}]'
                except KeyError:
                    if is_due(habit, log, screen_date):
                        textbox = '[ ]'
                    else:
                        textbox = '[o]'
                row += textbox.ljust(DATE_PADDING)
                i += 1
            habits_list.append(row)

        return header, habits_list

    def move(direction, dist=1):
        nonlocal current_row
        nonlocal selected_date
        match direction:
            case 'up':
                if current_row > 0:
                    current_row -= dist
            case 'down':
                if current_row < len(menu_habits) - 1:
                    current_row += dist
            case 'left':
                selected_date -= timedelta(days=dist)
            case 'right':
                selected_date += timedelta(days=dist)
            case 'today':
                selected_date = datetime.today()
            case 'top':
                current_row = 0
            case 'bottom':
                current_row = len(habits)-1

    def toggle_status():
        nonlocal habits
        nonlocal selected_date
        habit_name = habits[current_row]['name']
        date = selected_date.strftime('%Y-%m-%d')
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

    def force_exit():
        notify('Do you want to quit without saving? [N/y]')
        key = window.getch()
        if key == ord('y') or key == ord('Y'):
            sys.exit(1)

    def save():
        dump_log_to_file(log, log_file)
        notify(f'Saved to {log_file}')

    def save_quit():
        save()
        sys.exit(1)

    def notify(msg):
        nonlocal help_hold
        msg = msg.ljust(x_max)[:x_max-1] # Pad and crop to cover older messages
        window.addstr(y_max, 0, msg)
        help_hold = True

    # Dictionary key is the key pressed on the keyboard. The tuple contains the function to be
    # executed in the loop later on when the key is pressed along with its arguments.
    keys_main = {
            curses.KEY_UP:    (move, ['up']),
            curses.KEY_DOWN:  (move, ['down']),
            curses.KEY_LEFT:  (move, ['left']),
            curses.KEY_RIGHT: (move, ['right']),
            curses.KEY_ENTER: (toggle_status, []),
            ord('q'):         (save_quit, []),
            }

    # Key binds not shown at the bottom at the bottom of the screen
    keys_misc = {
            ord('k'):  (move, ['up']),
            ord('j'):  (move, ['down']),
            ord('h'):  (move, ['left']),
            ord('l'):  (move, ['left']),
            ord('s'):  (save, []),
            ord('Q'):  (force_exit, []),
            ord('t'):  (move, ['today']),
            ord('g'):  (move, ['top']),
            ord('G'):  (move, ['bottom']),
            ord('\n'): (toggle_status, []),
            ord('\r'): (toggle_status, []),
            ord(' '):  (toggle_status, []),
            }

    help_message = 'keys: '
    for key, action in keys_main.items():
        func = action[0].__name__.replace('_', ' ')
        action = ' '.join(action[1])
        separator = ' '*3
        match key:
            case 259:
                key = 'UP'
            case 258:
                key = 'DOWN'
            case 260:
                key = 'LEFT'
            case 261:
                key = 'RIGHT'
            case 343:
                key = 'RETURN'
            case _:
                key = chr(key)
        help_message += f'{key}:{func} {action}' + separator

    col = 0
    row = 0
    selected_date = datetime.today()
    current_row = 0
    y_max, x_max = window.getmaxyx()
    y_max -= 1
    x_max -= 1
    curses.curs_set(0)
    help_hold = False
    notify(help_message)
    while True:
        window.refresh()

        if help_hold: # To prevent other messages from being overwritten by the help message
            help_hold = False
        else:
            notify(help_message)

        header, menu_habits = gen_content(selected_date, days_back, days_forward)
        for row, line in enumerate(header):
            window.addstr(row, 0, line)
            row += 1
        for idy, text in enumerate(menu_habits):
            if idy == current_row:
                window.addstr(row, col, text, curses.A_STANDOUT)
            else:
                window.addstr(row, col, text)
            row += 1

        try:
            func, parms = (keys_main | keys_misc)[window.getch()]
            func(*parms)
        except KeyError:
            pass

def main(habits_file, log_file, days_back, days_forward):
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
    curses.wrapper(curses_tui, habits, log, log_file, days_back, days_forward)

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Minimalistic habit tracker')
    parser.add_argument('-f', '--file', dest='habits_file', metavar='FILE',
            help='Habits file in YAML format')
    parser.add_argument('-l', '--log_file', metavar='FILE',
            help='File to log activity to')
    parser.add_argument('-b', '--days_back', default=3, type=int, metavar='DAYS',
            help='Days before the selected date to display (default: %(default)s)')
    parser.add_argument('-w', '--days_forward', default=1, type=int, metavar='DAYS',
            help='Days after the selected date to display (default: %(default)s)')
    args = parser.parse_args()
    main(args.habits_file, args.log_file, args.days_back, args.days_forward)
