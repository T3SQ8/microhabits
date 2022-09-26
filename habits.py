#!/usr/bin/env python

# TODO Overflowing habits
# TODO Press "?" to all key binds
# TODO Subtasks
# TODO Don't crash when screen size is changed
# TODO INI configs
# TODO Measurable habits
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

    try:
        if log[name][selected_date] in ['y', 's']:
            due = False
    except KeyError:
        pass

    selected_date = datetime.strptime(selected_date, "%Y-%m-%d")

    if due:
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

def screen_date_format(dt):
    return dt.strftime('%d/%m (%a)')

def iso_date_format(dt):
    return dt.strftime('%Y-%m-%d')

def curses_tui(window, habits, log, log_file, days_back, days_forward):
    def move(direction, dist=1):
        nonlocal current_row
        nonlocal selected_date
        match direction:
            case 'up':
                if current_row > 0:
                    current_row -= dist
            case 'down':
                if current_row < len(habits) - 1:
                    current_row += dist
            case 'left':
                selected_date -= timedelta(days=dist)
            case 'right':
                selected_date += timedelta(days=dist)
            case 'today':
                selected_date = today
            case 'top':
                current_row = 0
            case 'bottom':
                current_row = len(habits)-1

    def toggle_status():
        nonlocal habits
        nonlocal selected_date
        habit_name = habits[current_row]['name']
        date = iso_date_format(selected_date)
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

    def toggle_hide():
        nonlocal hide_completed
        hide_completed = not hide_completed

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
            ord('l'):  (move, ['right']),
            ord('s'):  (save, []),
            ord('Q'):  (force_exit, []),
            ord('t'):  (move, ['today']),
            ord('g'):  (move, ['top']),
            ord('G'):  (move, ['bottom']),
            ord('H'):  (toggle_hide, []),
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
    today = datetime.today()
    selected_date = today
    current_row = 0
    help_hold = False
    hide_completed = False

    y_max, x_max = window.getmaxyx()
    y_max -= 1
    x_max -= 1
    notify(help_message)
    curses.curs_set(0)

    while True:
        window.refresh()

        if help_hold: # To prevent other messages from being overwritten by the help message
            help_hold = False
        else:
            notify(help_message)

        window.addstr(0, HABIT_NAME_CUTOFF + DATE_PADDING * abs(days_back), '-' * DATE_PADDING)
        i = 0
        for delta in range(days_back, days_forward + 1):
            screen_date = selected_date + timedelta(days=delta)
            attrb = curses.A_BOLD if screen_date == today else curses.A_NORMAL
            screen_date = screen_date_format(screen_date)
            window.addstr(1, HABIT_NAME_CUTOFF + DATE_PADDING*i, screen_date, attrb)
            i += 1

        for idy, habit in enumerate(habits):
            attrb = curses.A_BOLD
            i = 0
            for delta in range(days_back, days_forward + 1):
                visual_y = idy + 2 # Margin for header
                if len(habit['name']) > HABIT_NAME_CUTOFF - 2:
                    name = habit['name'][:HABIT_NAME_CUTOFF - 2]+'>'
                else:
                    name = habit['name']
                window.addstr(visual_y, 0, name)
                screen_date = selected_date + timedelta(days=delta)
                screen_date = iso_date_format(screen_date)
                try:
                    text = f'[{log[habit["name"]][screen_date]}]'
                except KeyError:
                    if is_due(habit, log, screen_date):
                        text = '[ ]'
                    else:
                        text = '[o]'
                if hide_completed and not is_due(habit, log, iso_date_format(selected_date)):
                    attrb = curses.A_DIM
                window.addstr(visual_y, HABIT_NAME_CUTOFF + DATE_PADDING*i, text, attrb)
                i += 1
            if current_row == idy:
                attrb = attrb | curses.A_STANDOUT
            window.chgat(visual_y, 0, attrb) # Apply attribute to entire line

        try:
            func, parms = (keys_main | keys_misc)[window.getch()]
            func(*parms)
        except KeyError:
            pass

def main(habits_file, log_file, days_back, days_forward):
    days_back = -abs(days_back)
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
