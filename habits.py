#!/usr/bin/env python

# TODO subtasks
# TODO option to assume skip
# TODO option change mark character
# TODO mesurable habits
# TODO Highlight todays date
# TODO curses.A_DIM completed and surficed habits
# TODO don't crash when screensize is changed
# TODO Show full name of overflowing habits name on the bottom
# TODO read from ~/.config/{name}/habits.yml and ~/.config/{name}/log.csv

from os.path import exists
from datetime import datetime, timedelta
import csv
import curses
import re
import yaml

class Habits:
    def __init__(self, habits_file, log_file):
        self.fieldnames = ['date', 'name', 'status']
        self.habits_file = habits_file
        self.log_file = log_file
        if not exists(self.habits_file):
            print(f"No such file or directory: '{self.habits_file}'")
            exit(1)
        if not exists(self.log_file):
            with open(self.log_file, 'w', encoding='utf-8') as file:
                csv.writer(file).writerow(self.fieldnames)

    def load_habits_from_file(self):
        with open(self.habits_file, 'r', encoding='utf-8') as file:
            habits = yaml.safe_load(file)
            #self.config = habits['config'] if 'config' in habits else None # FIXME
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
        for habit in self.log:
            for date in self.log[habit]:
                for status in self.log[habit][date]:
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
        def check_due(frequency, date, habit):
            date = datetime.strptime(date, "%Y-%m-%d")
            match frequency:
                case int():
                    last_done = None
                    try: # If never done before
                        for c_date, status in self.log[habit].items():
                            if status == 'y':
                                last_done = c_date
                    except KeyError:
                        pass
                    if last_done == None:
                        return False
                    else:
                        last_done = datetime.strptime(last_done, "%Y-%m-%d")
                        delta = date - last_done
                        if 0 < delta.days < frequency:
                            return True
                case list():
                        try:
                            frequency = [
                                    re.search('(\d{1,2})[a-zA-Z]{2}', item).group(1) for item in frequency
                                    ]
                            date = date.strftime('%-d') # non-padded day of month
                            if not date in frequency:
                                return True
                        except:
                            frequency = [ item.capitalize() for item in frequency ]
                            date = date.strftime('%A') # Day of week
                            if not date.capitalize() in frequency:
                                return True

        before_days = -before_days if before_days > 0 else before_days # Make negative if positive

        header = []
        header.append(' '.ljust(66) + '-----------')

        day_header = ' '.ljust(21)
        c = before_days
        while before_days <= c <= forward_days:
            d = start_day + timedelta(days=c)
            day_header += d.strftime('%d/%m (%a)').rjust(14)
            c += 1
        header.append(day_header)

        habits_list = []
        for habit in self.habits:
            row = ''
            name = habit['name'][:22]+'>' if len(habit['name']) > 22 else habit['name']
            row += name.ljust(24)
            c = before_days
            while before_days <= c <= forward_days:
                d = start_day + timedelta(days=c)
                d = d.strftime('%Y-%m-%d')
                try:
                    t = f'[{self.log[habit["name"]][d]}]'
                except KeyError:
                    if check_due(habit['frequency'], d, habit['name']) == True:
                        t = '[.]'
                    else:
                        t = '[ ]'
                row += t.ljust(14)
                c += 1
            habits_list.append(row)

        return header, habits_list

    def curses_loop(self, stdscr):
        def message(msg):
            stdscr.addstr(y_max-1, 0,
                    msg.ljust(x_max-1) # Pad the message so that it covers any previous message
                    )

        def save():
            self.dump_log_to_file()
            message(f'Saved to {self.log_file}')

        y_max, x_max = stdscr.getmaxyx()
        now = datetime.today()
        x = 0
        y = 0
        current_row = 0
        curses.curs_set(0)
        curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE)
        while True:
            stdscr.erase()
            message('keys: kjaks djasjd adkjsa djlsa jdjsalkdj sajlkdj')
            header, habits = self.gen_content(now, 3, 1)
            for y, row in enumerate(header):
                stdscr.addstr(y, 0, row)
                y += 1
            header_space = y
            if y < header_space:
                y = header_space
            for idy, text in enumerate(habits):
                if idy == current_row:
                    highlighted = idy
                    stdscr.attron(curses.color_pair(1))
                    stdscr.addstr(y, x, text)
                    stdscr.attroff(curses.color_pair(1))
                else:
                    stdscr.addstr(y, x, text)
                y += 1

            match stdscr.getch():
                case curses.KEY_UP:
                    if current_row > 0:
                        current_row -= 1
                case curses.KEY_DOWN:
                    if current_row < len(habits) - 1:
                        current_row += 1
                case curses.KEY_LEFT:
                    now = now - timedelta(days=1)
                case curses.KEY_RIGHT:
                    now = now + timedelta(days=1)
                case curses.KEY_ENTER | 10 | 13: # ord('\n') and ord('\r')
                    highlighted = self.habits[highlighted]['name']
                    d = now.strftime('%Y-%m-%d')
                    try:
                        self.log[highlighted]
                    except KeyError:
                        self.log[highlighted] = {}
                    try:
                        self.log[highlighted][d]
                    except KeyError:
                        self.log[highlighted][d] = {}
                    if self.log[highlighted][d] == 'y':
                        self.log[highlighted][d] = 's'
                    elif self.log[highlighted][d] == 's':
                        del self.log[highlighted][d]
                    else:
                        self.log[highlighted][d] = 'y'
                # TODO replace intigers with value of `ord('x')`
                case 116: # t
                    now = datetime.today()
                case 115: # s
                    save()
                    stdscr.getch()
                case 113: # q
                    save()
                    break
                case 81: # Q
                    message('Do you want to quit without saving? (N/y)')
                    key = stdscr.getch()
                    if key == ord('y') or key == ord('Y'):
                        break

def main(habits_file):
    log_file = habits_file[:habits_file.rfind(".")] + '.csv'
    h = Habits(habits_file, log_file)
    h.load_habits_from_file()
    h.load_log_from_file()
    h.curses_tui()

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Visually plot ledger files.')
    parser.add_argument('habits_file', metavar='FILE', help='Habits file in YAML format')
    args = parser.parse_args()
    main(args.habits_file)
